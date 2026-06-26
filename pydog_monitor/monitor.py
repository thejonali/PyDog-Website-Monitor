import sqlite3
import time
import random
import requests
import logging
import json
from pydog_monitor.config import load_config
from pydog_monitor.db import connect_database
from pydog_monitor.errors import MonitorError
from pydog_monitor.incidents import record_failure, resolve_open_incident
from pydog_monitor.notifications import deliver_notification, record_notification_attempt

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
        rows = cursor.fetchall()

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

    return group_monitor_targets(rows), headers


def group_monitor_targets(rows):
    targets_by_website = {}
    for row in rows:
        website_id, website_url, contact_id, contact_name, preferred_contact, email, phone_number = row
        target = targets_by_website.setdefault(
            website_id,
            {"website_id": website_id, "website_url": website_url, "contacts": []},
        )
        if contact_id is not None:
            target["contacts"].append(
                {
                    "contact_id": contact_id,
                    "contact_name": contact_name,
                    "preferred_contact": preferred_contact,
                    "email": email,
                    "phone_number": phone_number,
                }
            )
    return list(targets_by_website.values())


def check_website(website, headers, config):
    website_id = website["website_id"]
    website_url = website["website_url"]
    contacts = website["contacts"]
    try:
        response = requests.get(
            website_url,
            headers=headers,
            timeout=config.request_timeout_seconds,
        )
        if response.status_code == 200:
            handle_success(website_id, website_url, response.status_code, contacts, config.database_path)
            return

        handle_failure(
            website_id,
            website_url,
            contacts,
            str(response.status_code),
            config.database_path,
        )
    except requests.RequestException as exc:
        handle_failure(
            website_id,
            website_url,
            contacts,
            str(exc),
            config.database_path,
        )


def handle_success(website_id, website_url, status_code, contacts, database_path):
    resolved_incident_id = resolve_open_incident(website_id, database_path)
    if resolved_incident_id:
        logger.info(
            "Website incident resolved",
            extra={
                "event": "incident_resolved",
                "website_id": website_id,
                "website_url": website_url,
                "status_code": status_code,
                "incident_id": resolved_incident_id,
            },
        )
        notify_contacts(
            website_id,
            website_url,
            contacts,
            resolved_incident_id,
            "recovery",
            "recovered",
            database_path,
        )
        return

    logger.info(
        "Website check succeeded",
        extra={
            "event": "website_check_ok",
            "website_id": website_id,
            "website_url": website_url,
            "status_code": status_code,
        },
    )


def handle_failure(
    website_id,
    website_url,
    contacts,
    error_code,
    database_path,
):
    incident_id, is_new_incident = record_failure(website_id, error_code, database_path)
    if not is_new_incident:
        logger.warning(
            "Website is still down",
            extra={
                "event": "incident_still_open",
                "website_id": website_id,
                "website_url": website_url,
                "error_code": error_code,
                "incident_id": incident_id,
            },
        )
        return

    logger.warning(
        "Website incident opened",
        extra={
            "event": "incident_opened",
            "website_id": website_id,
            "website_url": website_url,
            "error_code": error_code,
            "incident_id": incident_id,
        },
    )
    notify_contacts(
        website_id,
        website_url,
        contacts,
        incident_id,
        "outage",
        error_code,
        database_path,
    )


def notify_contacts(
    website_id,
    website_url,
    contacts,
    incident_id,
    notification_type,
    error_code,
    database_path,
):
    if not contacts:
        logger.warning(
            "No contacts configured for notification",
            extra={
                "event": "notification_skipped",
                "website_id": website_id,
                "website_url": website_url,
                "incident_id": incident_id,
                "notification_type": notification_type,
            },
        )
        return

    for contact in contacts:
        result = deliver_notification(
            contact,
            website_url,
            notification_type,
            database_path,
            error_code=error_code,
        )
        record_notification_attempt(
            website_id,
            contact["contact_id"],
            incident_id,
            notification_type,
            error_code,
            result,
            database_path,
        )
        log_notification_result(
            website_id,
            website_url,
            contact["contact_id"],
            incident_id,
            notification_type,
            result,
        )


def log_notification_result(
    website_id,
    website_url,
    contact_id,
    incident_id,
    notification_type,
    result,
):
    level = logger.info if result.status == "sent" else logger.error
    level(
        "Notification delivery recorded",
        extra={
            "event": "notification_delivery",
            "website_id": website_id,
            "website_url": website_url,
            "contact_id": contact_id,
            "incident_id": incident_id,
            "notification_type": notification_type,
            "notification_status": result.status,
            "notification_channel": result.channel,
            "notification_error": result.error,
        },
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
    contact = {
        "contact_id": contact_id,
        "contact_name": contact_name,
        "preferred_contact": preferred_contact,
        "email": email,
        "phone_number": phone_number,
    }
    result = deliver_notification(contact, website_url, "outage", database_path, error_code=error_code)
    record_notification_attempt(
        website_id,
        contact_id,
        None,
        "outage",
        error_code,
        result,
        database_path,
    )
    log_notification_result(
        website_id,
        website_url,
        contact_id,
        None,
        "outage",
        result,
    )
