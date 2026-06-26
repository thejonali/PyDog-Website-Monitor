from pydog_monitor.db import connect_database


def record_failure(website_id, error_code, database_path):
    conn = connect_database(database_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id FROM incidents
            WHERE website_id = ? AND status = 'open'
            ORDER BY opened_at DESC
            LIMIT 1
            """,
            (website_id,),
        )
        open_incident = cursor.fetchone()
        if open_incident:
            incident_id = open_incident[0]
            cursor.execute(
                """
                UPDATE incidents
                SET failure_count = failure_count + 1,
                    last_seen_at = CURRENT_TIMESTAMP,
                    last_error_code = ?
                WHERE id = ?
                """,
                (error_code, incident_id),
            )
            conn.commit()
            return incident_id, False

        cursor.execute(
            """
            INSERT INTO incidents (website_id, last_error_code)
            VALUES (?, ?)
            """,
            (website_id, error_code),
        )
        incident_id = cursor.lastrowid
        conn.commit()
        return incident_id, True
    finally:
        conn.close()


def resolve_open_incident(website_id, database_path):
    conn = connect_database(database_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id FROM incidents
            WHERE website_id = ? AND status = 'open'
            ORDER BY opened_at DESC
            LIMIT 1
            """,
            (website_id,),
        )
        open_incident = cursor.fetchone()
        if not open_incident:
            return None

        incident_id = open_incident[0]
        cursor.execute(
            """
            UPDATE incidents
            SET status = 'resolved',
                resolved_at = CURRENT_TIMESTAMP,
                last_seen_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (incident_id,),
        )
        conn.commit()
        return incident_id
    finally:
        conn.close()
