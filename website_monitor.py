import sqlite3
import time
import random
import requests
import base64
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from requests import HTTPError
from twilio.rest import Client
import json
from security import SecretConfigurationError, decrypt_secret

def run_monitor():
    print("Running monitor...")
    while True:
        conn = sqlite3.connect('data/webMonitor.db')
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

        if header_value:
            headers = json.loads(header_value[0])
        else:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.76 Safari/537.36'}

        for website in websites:
            website_id, website_url, contact_id, contact_name, preferred_contact, email, phone_number = website
            try:
                response = requests.get(website_url, headers=headers)
                if response.status_code != 200:
                    notify_contact(website_id, website_url, contact_id, contact_name, preferred_contact, email, phone_number, response.status_code)
            except requests.RequestException as e:
                notify_contact(website_id, website_url, contact_id, contact_name, preferred_contact, email, phone_number, str(e))

        sleep_time = random.randint(180, 300)
        print("Website: ", website_url, " is ok. Sleeping for", sleep_time, "seconds...")
        time.sleep(sleep_time)

def notify_contact(website_id, website_url, contact_id, contact_name, preferred_contact, email, phone_number, error_code):
    msgText = f"Alert: The website {website_url} is down. Error code: {error_code}"
    msgHTML = f"<p>Alert: The website <a href='{website_url}'>{website_url}</a> is down.</p><p>Error code: {error_code}</p>"
    if preferred_contact == 'email':
        if os.path.exists('client_secret.json'):
            send_email(email, msgText, msgHTML, website_url)
        else:
            send_email_smtp(email, "Website Down Alert", msgHTML)
    elif preferred_contact == 'phone':
        send_sms(phone_number, msgText)

    conn = sqlite3.connect('data/webMonitor.db')
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO down_tracking (website_id, error_code, sent_contact)
    VALUES (?, ?, ?)
    ''', (website_id, error_code, contact_id))
    conn.commit()
    conn.close()

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
    conn = sqlite3.connect('data/webMonitor.db')
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
    conn = sqlite3.connect('data/webMonitor.db')
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
