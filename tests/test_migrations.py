import sqlite3

from migrations import migrate_database


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
    finally:
        conn.close()

    assert migration_count == 1
    assert header_count == 1
