import sqlite3
import time
import random
import requests
import base64
import smtplib
import os
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from requests import HTTPError
from twilio.rest import Client
import json
from config import load_config
from db import connect_database
from errors import MonitorError
from security import SecretConfigurationError, decrypt_secret

logger = logging.getLogger(__name__)


def run_monitor(config=None, stop_event=None, once=False):
    config = config or load_config()
    logger.info("Monitor started", extra={"event": "monitor_started"})

    while True:
        websites, headers = load_monitor_targets(config.database_path)

        if not websites:
            logger.info("No monitored websites found", extra={"event": "monitor_no_targets"})

        for website in websites:
            if stop_event and stop_event.is_set():
                logger.info("Monitor shutdown requested", extra={"event": "monitor_shutdown_requested"})
                return
            check_website(website, headers, config)

        if once:
            return

        sleep_time = random.randint(
            config.monitor_min_sleep_seconds,
            config.monitor_max_sleep_seconds,
        )
        logger.info(
            "Monitor sleeping",
            extra={"event": "monitor_sleep", "sleep_seconds": sleep_time},
        )
        if stop_event:
            if stop_event.wait(sleep_time):
                logger.info("Monitor stopped", extra={"event": "monitor_stopped"})
                return
        else:
            time.sleep(sleep_time)


def load_monitor_targets(database_path):
    try:
        conn = connect_database(database_path)
        cursor = conn.cursor()
        cursor.execute('''
        SELECT w.id, w.website_url, c.id, c.contact_name, c.preferred_contact, c.email, c.phone_number
        FROM websites w
        LEFT JOIN website_monitor wm ON w.id = wm.website_id
        LEFT JOIN contacts c ON wm.contact_id = c.id
        WHERE w.monitor_status = 1
        ''')
        websites = cursor.fetchall()

        cursor.execute('''
        SELECT value FROM settings WHERE integration_name = 'monitor_header' AND key = 'header' AND status = 1
        ''')
        header_value = cursor.fetchone()
        conn.close()
    except sqlite3.Error as exc:
        raise MonitorError("Failed to load monitor targets.", {"database_path": str(database_path)}) from exc

    if header_value:
        try:
            headers = json.loads(header_value[0])
        except json.JSONDecodeError as exc:
            raise MonitorError("Monitor header setting is not valid JSON.") from exc
    else:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.76 Safari/537.36'
        }

    return websites, headers


def check_website(website, headers, config):
    website_id, website_url, contact_id, contact_name, preferred_contact, email, phone_number = website
    try:
        response = requests.get(
            website_url,
            headers=headers,
            timeout=config.request_timeout_seconds,
        )
        if response.status_code == 200:
            logger.info(
                "Website check succeeded",
                extra={
                    "event": "website_check_ok",
                    "website_id": website_id,
                    "website_url": website_url,
                    "status_code": response.status_code,
                },
            )
            return

        notify_contact(
            website_id,
            website_url,
            contact_id,
            contact_name,
            preferred_contact,
            email,
            phone_number,
            str(response.status_code),
            config.database_path,
        )
    except requests.RequestException as exc:
        notify_contact(
            website_id,
            website_url,
            contact_id,
            contact_name,
            preferred_contact,
            email,
            phone_number,
            str(exc),
            config.database_path,
        )


def notify_contact(
    website_id,
    website_url,
    contact_id,
    contact_name,
    preferred_contact,
    email,
    phone_number,
    error_code,
    database_path=None,
):
    msgText = f"Alert: The website {website_url} is down. Error code: {error_code}"
    msgHTML = f"<p>Alert: The website <a href='{website_url}'>{website_url}</a> is down.</p><p>Error code: {error_code}</p>"
    if preferred_contact == 'email':
        if os.path.exists('client_secret.json'):
            send_email(email, msgText, msgHTML, website_url)
        else:
            send_email_smtp(email, "Website Down Alert", msgHTML)
    elif preferred_contact == 'phone':
        send_sms(phone_number, msgText)

    conn = connect_database(database_path)
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO down_tracking (website_id, error_code, sent_contact)
    VALUES (?, ?, ?)
    ''', (website_id, error_code, contact_id))
    conn.commit()
    conn.close()
    logger.warning(
        "Website down notification recorded",
        extra={
            "event": "website_down",
            "website_id": website_id,
            "website_url": website_url,
            "error_code": error_code,
        },
    )

def send_email(email, msgText, msgHTML, website_url):
    SCOPES = [
            "https://www.googleapis.com/auth/gmail.send"
        ]
    flow = InstalledAppFlow.from_client_secrets_file(
                'client_secret.json', SCOPES)
    creds = flow.run_local_server(port=0)
    service = build('gmail', 'v1', credentials=creds)
    message = MIMEMultipart('alternative')
    msgT = MIMEText(msgText, 'plain')
    msgH = MIMEText(msgHTML, 'html')
    message.attach(msgT)
    message.attach(msgH)
    message['to'] = email
    message['subject'] = 'Website - ' + website_url + ' is down'
    create_message = {'raw': base64.urlsafe_b64encode(message.as_bytes()).decode()}
    try:
        message = (service.users().messages().send(userId="me", body=create_message).execute())
        print(F'sent message to {message} Message Id: {message["id"]}')
    except HTTPError as error:
        print(F'An error occurred: {error}')
        message = None

def send_sms(phone_number, message):
    conn = connect_database()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT key, value FROM settings WHERE integration_name = 'Twilio' AND status = 1
    ''')
    settings = cursor.fetchall()
    conn.close()

    twilio_settings = {key: value for key, value in settings}
    account_sid = twilio_settings['account_sid']
    try:
        auth_token = decrypt_secret(twilio_settings['auth_token'])
    except SecretConfigurationError as e:
        print(f"Twilio Integration failed: {e}")
        return
    from_phone = twilio_settings['from_phone']

    client = Client(account_sid, auth_token)
    client.messages.create(
        body=message,
        from_=from_phone,
        to=phone_number
    )
    print(f"Sending SMS to {phone_number}: {message}")

def send_email_smtp(email, subject, message):
    conn = connect_database()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT key, value FROM settings WHERE integration_name = 'SMTP' AND status = 1
    ''')
    settings = cursor.fetchall()
    conn.close()

    smtp_settings = {key: value for key, value in settings}
    sender_email = smtp_settings['sender_email']
    try:
        sender_password = decrypt_secret(smtp_settings['sender_password'])
    except SecretConfigurationError as e:
        print(f"SMTP Email Integration failed: {e}")
        return
    smtp_server = smtp_settings['smtp_server']
    smtp_port = smtp_settings['smtp_port']

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = email
    msg['Subject'] = subject

    msg.attach(MIMEText(message, 'html'))

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail(sender_email, email, text)
        server.quit()
        print(f"Email sent to {email}: {message}")
    except Exception as e:
        print(f"Failed to send email to {email}: {e}")
