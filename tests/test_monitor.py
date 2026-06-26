import sqlite3

import website_monitor
from config import AppConfig
from migrations import migrate_database


def test_run_monitor_once_records_failed_check(tmp_path, monkeypatch):
    database_path = tmp_path / "webMonitor.db"
    migrate_database(database_path)
    _insert_monitor_target(database_path)
    monkeypatch.setattr(website_monitor, "send_email_smtp", lambda *args, **kwargs: None)

    class Response:
        status_code = 503

    def fake_get(url, headers=None, timeout=None):
        assert url == "https://example.com"
        assert timeout == 3
        return Response()

    monkeypatch.setattr(website_monitor.requests, "get", fake_get)
    config = AppConfig(
        database_path=database_path,
        monitor_min_sleep_seconds=1,
        monitor_max_sleep_seconds=1,
        request_timeout_seconds=3,
        log_level="INFO",
        log_format="text",
    )

    website_monitor.run_monitor(config=config, once=True)

    conn = sqlite3.connect(database_path)
    try:
        row = conn.execute("SELECT website_id, error_code, sent_contact FROM down_tracking").fetchone()
    finally:
        conn.close()

    assert row == (1, "503", 1)


def _insert_monitor_target(database_path):
    conn = sqlite3.connect(database_path)
    try:
        conn.execute(
            "INSERT INTO websites (id, website_url, monitor_status) VALUES (1, 'https://example.com', 1)"
        )
        conn.execute(
            """
            INSERT INTO contacts (id, contact_name, email, phone_number, preferred_contact)
            VALUES (1, 'Ops', 'ops@example.com', '5551234567', 'email')
            """
        )
        conn.execute("INSERT INTO website_monitor (website_id, contact_id) VALUES (1, 1)")
        conn.commit()
    finally:
        conn.close()
