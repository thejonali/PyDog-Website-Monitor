import sqlite3
from pathlib import Path


MIGRATIONS = [
    (
        1,
        "initial schema",
        [
            """
            CREATE TABLE IF NOT EXISTS websites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                website_url TEXT(150),
                monitor_status INTEGER
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contact_name TEXT(50),
                email TEXT(50),
                phone_number INTEGER(15),
                preferred_contact TEXT(50)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                integration_name TEXT(50),
                key TEXT(150),
                value TEXT(150),
                status INTEGER
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS down_tracking (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                website_id INTEGER,
                time_stamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                error_code TEXT(50),
                sent_contact INTEGER,
                FOREIGN KEY (website_id) REFERENCES websites(id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS website_monitor (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                website_id INTEGER,
                contact_id INTEGER,
                FOREIGN KEY (website_id) REFERENCES websites(id),
                FOREIGN KEY (contact_id) REFERENCES contacts(id)
            )
            """,
            """
            INSERT INTO settings (integration_name, key, value, status)
            SELECT 'monitor_header', 'header',
                   '{"User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.76 Safari/537.36"}',
                   1
            WHERE NOT EXISTS (
                SELECT 1 FROM settings
                WHERE integration_name = 'monitor_header' AND key = 'header'
            )
            """,
        ],
    )
]


def migrate_database(database_path):
    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        applied_versions = {
            row[0] for row in conn.execute("SELECT version FROM schema_migrations").fetchall()
        }
        for version, name, statements in MIGRATIONS:
            if version in applied_versions:
                continue
            with conn:
                for statement in statements:
                    conn.execute(statement)
                conn.execute(
                    "INSERT INTO schema_migrations (version, name) VALUES (?, ?)",
                    (version, name),
                )
    finally:
        conn.close()
