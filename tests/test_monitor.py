import sqlite3

from pydog_monitor import monitor
from pydog_monitor.config import AppConfig
from pydog_monitor.migrations import migrate_database
from pydog_monitor.notifications import NotificationDeliveryError
from pydog_monitor import notifications


def test_new_incident_notifies_each_contact_once(tmp_path, monkeypatch):
    database_path = tmp_path / "webMonitor.db"
    migrate_database(database_path)
    _insert_monitor_target(database_path, contact_count=2)
    sent_notifications = []
    monkeypatch.setattr(
        notifications,
        "send_email_smtp",
        lambda *args, **kwargs: sent_notifications.append(args),
    )

    def fake_get(url, headers=None, timeout=None):
        assert url == "https://example.com"
        assert timeout == 3
        return _response(503)

    monkeypatch.setattr(monitor.requests, "get", fake_get)
    config = _test_config(database_path)

    monitor.run_monitor(config=config, once=True)

    conn = sqlite3.connect(database_path)
    try:
        rows = conn.execute(
            """
            SELECT website_id, error_code, sent_contact, notification_type,
                   notification_status, notification_channel
            FROM down_tracking
            ORDER BY sent_contact
            """
        ).fetchall()
        incident = conn.execute(
            "SELECT website_id, status, failure_count, last_error_code FROM incidents"
        ).fetchone()
    finally:
        conn.close()

    assert rows == [
        (1, "503", 1, "outage", "sent", "smtp"),
        (1, "503", 2, "outage", "sent", "smtp"),
    ]
    assert incident == (1, "open", 1, "503")
    assert len(sent_notifications) == 2


def test_repeated_failure_updates_incident_without_duplicate_notification(tmp_path, monkeypatch):
    database_path = tmp_path / "webMonitor.db"
    migrate_database(database_path)
    _insert_monitor_target(database_path)
    sent_notifications = []
    monkeypatch.setattr(
        notifications,
        "send_email_smtp",
        lambda *args, **kwargs: sent_notifications.append(args),
    )
    monkeypatch.setattr(monitor.requests, "get", lambda *args, **kwargs: _response(503))
    config = _test_config(database_path)

    monitor.run_monitor(config=config, once=True)
    monitor.run_monitor(config=config, once=True)

    conn = sqlite3.connect(database_path)
    try:
        notification_count = conn.execute("SELECT COUNT(*) FROM down_tracking").fetchone()[0]
        incident = conn.execute(
            "SELECT status, failure_count, last_error_code FROM incidents"
        ).fetchone()
    finally:
        conn.close()

    assert notification_count == 1
    assert incident == ("open", 2, "503")
    assert len(sent_notifications) == 1


def test_success_resolves_open_incident(tmp_path, monkeypatch):
    database_path = tmp_path / "webMonitor.db"
    migrate_database(database_path)
    _insert_monitor_target(database_path)
    sent_notifications = []
    monkeypatch.setattr(
        notifications,
        "send_email_smtp",
        lambda *args, **kwargs: sent_notifications.append(args),
    )
    responses = iter([_response(503), _response(200)])
    monkeypatch.setattr(monitor.requests, "get", lambda *args, **kwargs: next(responses))
    config = _test_config(database_path)

    monitor.run_monitor(config=config, once=True)
    monitor.run_monitor(config=config, once=True)

    conn = sqlite3.connect(database_path)
    try:
        incident = conn.execute(
            "SELECT status, failure_count, resolved_at IS NOT NULL FROM incidents"
        ).fetchone()
        notifications_recorded = conn.execute(
            """
            SELECT notification_type, notification_status, notification_channel
            FROM down_tracking
            ORDER BY id
            """
        ).fetchall()
    finally:
        conn.close()

    assert incident == ("resolved", 1, 1)
    assert notifications_recorded == [
        ("outage", "sent", "smtp"),
        ("recovery", "sent", "smtp"),
    ]
    assert len(sent_notifications) == 2


def test_notification_failure_is_recorded_without_crashing_monitor(tmp_path, monkeypatch):
    database_path = tmp_path / "webMonitor.db"
    migrate_database(database_path)
    _insert_monitor_target(database_path)

    def fail_smtp(*args, **kwargs):
        raise NotificationDeliveryError("SMTP send failed: timeout", channel="smtp")

    monkeypatch.setattr(notifications, "send_email_smtp", fail_smtp)
    monkeypatch.setattr(monitor.requests, "get", lambda *args, **kwargs: _response(503))
    config = _test_config(database_path)

    monitor.run_monitor(config=config, once=True)

    conn = sqlite3.connect(database_path)
    try:
        notification = conn.execute(
            """
            SELECT notification_type, notification_status, notification_channel, notification_error
            FROM down_tracking
            """
        ).fetchone()
        incident = conn.execute("SELECT status, failure_count FROM incidents").fetchone()
    finally:
        conn.close()

    assert notification == ("outage", "failed", "smtp", "SMTP send failed: timeout")
    assert incident == ("open", 1)


def _response(status_code):
    class Response:
        pass

    response = Response()
    response.status_code = status_code
    return response


def _test_config(database_path):
    return AppConfig(
        database_path=database_path,
        monitor_min_sleep_seconds=1,
        monitor_max_sleep_seconds=1,
        request_timeout_seconds=3,
        log_level="INFO",
        log_format="text",
    )


def _insert_monitor_target(database_path, contact_count=1):
    conn = sqlite3.connect(database_path)
    try:
        conn.execute(
            "INSERT INTO websites (id, website_url, monitor_status) VALUES (1, 'https://example.com', 1)"
        )
        for contact_id in range(1, contact_count + 1):
            conn.execute(
                """
                INSERT INTO contacts (id, contact_name, email, phone_number, preferred_contact)
                VALUES (?, ?, ?, '5551234567', 'email')
                """,
                (contact_id, f"Ops {contact_id}", f"ops{contact_id}@example.com"),
            )
            conn.execute(
                "INSERT INTO website_monitor (website_id, contact_id) VALUES (1, ?)",
                (contact_id,),
            )
        conn.commit()
    finally:
        conn.close()
