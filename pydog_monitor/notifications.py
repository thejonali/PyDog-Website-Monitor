import base64
import logging
import os
import smtplib
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from requests import HTTPError
from twilio.rest import Client

from pydog_monitor.db import connect_database
from pydog_monitor.security import SecretConfigurationError, decrypt_secret

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class NotificationResult:
    status: str
    channel: str
    error: str = ""


class NotificationDeliveryError(RuntimeError):
    def __init__(self, message, channel="unknown"):
        super().__init__(message)
        self.channel = channel


def deliver_notification(contact, website_url, notification_type, database_path, error_code=None):
    try:
        channel = (contact.get("preferred_contact") or "").lower()
        subject, text_body, html_body = build_message(website_url, notification_type, error_code)
        if channel == "email":
            if not contact.get("email"):
                raise NotificationDeliveryError("Email contact is missing an email address.", channel="email")
            if os.path.exists("client_secret.json"):
                send_email(contact["email"], text_body, html_body, website_url, subject=subject)
                return NotificationResult(status="sent", channel="gmail")
            send_email_smtp(contact["email"], subject, html_body, database_path=database_path)
            return NotificationResult(status="sent", channel="smtp")
        if channel == "phone":
            if not contact.get("phone_number"):
                raise NotificationDeliveryError("Phone contact is missing a phone number.", channel="phone")
            send_sms(contact["phone_number"], text_body, database_path=database_path)
            return NotificationResult(status="sent", channel="twilio")
        raise NotificationDeliveryError(f"Unsupported contact method: {channel}", channel=channel or "unknown")
    except NotificationDeliveryError as exc:
        return NotificationResult(status="failed", channel=exc.channel, error=str(exc))


def build_message(website_url, notification_type, error_code=None):
    if notification_type == "recovery":
        subject = f"Website recovered - {website_url}"
        text_body = f"Recovery: The website {website_url} is responding again."
        html_body = f"<p>Recovery: The website <a href='{website_url}'>{website_url}</a> is responding again.</p>"
        return subject, text_body, html_body

    subject = "Website Down Alert"
    text_body = f"Alert: The website {website_url} is down. Error code: {error_code}"
    html_body = (
        f"<p>Alert: The website <a href='{website_url}'>{website_url}</a> is down.</p>"
        f"<p>Error code: {error_code}</p>"
    )
    return subject, text_body, html_body


def record_notification_attempt(
    website_id,
    contact_id,
    incident_id,
    notification_type,
    error_code,
    result,
    database_path,
):
    conn = connect_database(database_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO down_tracking (
                website_id,
                error_code,
                sent_contact,
                incident_id,
                notification_type,
                notification_status,
                notification_channel,
                notification_error
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                website_id,
                error_code,
                contact_id,
                incident_id,
                notification_type,
                result.status,
                result.channel,
                result.error,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def send_email(email, msgText, msgHTML, website_url, subject=None):
    scopes = ["https://www.googleapis.com/auth/gmail.send"]
    try:
        flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", scopes)
        creds = flow.run_local_server(port=0)
        service = build("gmail", "v1", credentials=creds)
        message = MIMEMultipart("alternative")
        message.attach(MIMEText(msgText, "plain"))
        message.attach(MIMEText(msgHTML, "html"))
        message["to"] = email
        message["subject"] = subject or f"Website - {website_url} is down"
        create_message = {"raw": base64.urlsafe_b64encode(message.as_bytes()).decode()}
        sent_message = service.users().messages().send(userId="me", body=create_message).execute()
    except HTTPError as exc:
        raise NotificationDeliveryError(f"Gmail API send failed: {exc}", channel="gmail") from exc
    except Exception as exc:
        raise NotificationDeliveryError(f"Gmail API configuration failed: {exc}", channel="gmail") from exc

    logger.info("Gmail notification sent", extra={"event": "notification_provider_sent", "provider": "gmail"})
    return sent_message


def send_sms(phone_number, message, database_path=None):
    settings = _load_settings("Twilio", database_path)
    try:
        account_sid = _required_setting(settings, "account_sid", "Twilio")
        auth_token = decrypt_secret(_required_setting(settings, "auth_token", "Twilio"))
        from_phone = _required_setting(settings, "from_phone", "Twilio")
    except SecretConfigurationError as exc:
        raise NotificationDeliveryError(f"Twilio secret configuration failed: {exc}", channel="twilio") from exc

    try:
        client = Client(account_sid, auth_token)
        client.messages.create(body=message, from_=from_phone, to=phone_number)
    except Exception as exc:
        raise NotificationDeliveryError(f"Twilio send failed: {exc}", channel="twilio") from exc

    logger.info("SMS notification sent", extra={"event": "notification_provider_sent", "provider": "twilio"})


def send_email_smtp(email, subject, message, database_path=None):
    settings = _load_settings("SMTP", database_path)
    try:
        sender_email = _required_setting(settings, "sender_email", "SMTP")
        sender_password = decrypt_secret(_required_setting(settings, "sender_password", "SMTP"))
        smtp_server = _required_setting(settings, "smtp_server", "SMTP")
        smtp_port = int(_required_setting(settings, "smtp_port", "SMTP"))
    except SecretConfigurationError as exc:
        raise NotificationDeliveryError(f"SMTP secret configuration failed: {exc}", channel="smtp") from exc
    except ValueError as exc:
        raise NotificationDeliveryError("SMTP smtp_port must be an integer.", channel="smtp") from exc

    email_message = MIMEMultipart()
    email_message["From"] = sender_email
    email_message["To"] = email
    email_message["Subject"] = subject
    email_message.attach(MIMEText(message, "html"))

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, email, email_message.as_string())
    except Exception as exc:
        raise NotificationDeliveryError(f"SMTP send failed: {exc}", channel="smtp") from exc

    logger.info("SMTP notification sent", extra={"event": "notification_provider_sent", "provider": "smtp"})


def _load_settings(integration_name, database_path):
    conn = connect_database(database_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT key, value FROM settings
            WHERE integration_name = ? AND status = 1
            """,
            (integration_name,),
        )
        return {key: value for key, value in cursor.fetchall()}
    finally:
        conn.close()


def _required_setting(settings, key, integration_name):
    value = settings.get(key)
    if value in (None, ""):
        raise NotificationDeliveryError(
            f"{integration_name} integration is missing required setting: {key}",
            channel=integration_name.lower(),
        )
    return value
