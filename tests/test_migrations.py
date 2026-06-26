import sqlite3

from pydog_monitor.migrations import migrate_database


def test_migrate_database_is_idempotent(tmp_path):
    database_path = tmp_path / "webMonitor.db"

    migrate_database(database_path)
    migrate_database(database_path)

    conn = sqlite3.connect(database_path)
    try:
        migration_count = conn.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0]
        header_count = conn.execute(
            """
            SELECT COUNT(*) FROM settings
            WHERE integration_name = 'monitor_header' AND key = 'header'
            """
        ).fetchone()[0]
        incident_indexes = conn.execute(
            """
            SELECT COUNT(*) FROM sqlite_master
            WHERE type = 'index' AND name = 'idx_incidents_website_status'
            """
        ).fetchone()[0]
        down_tracking_columns = {
            row[1] for row in conn.execute("PRAGMA table_info(down_tracking)").fetchall()
        }
    finally:
        conn.close()

    assert migration_count == 3
    assert header_count == 1
    assert incident_indexes == 1
    assert {
        "incident_id",
        "notification_type",
        "notification_status",
        "notification_channel",
        "notification_error",
    }.issubset(down_tracking_columns)
