"""Track scrape run timestamps in real_estate.db."""

from datetime import datetime, timezone


def ensure_scrape_runs_table(connection):
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS SCRAPE_RUNS (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            finished_at TEXT NOT NULL,
            listings_processed INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    connection.commit()


def record_scrape_run(connection, listings_processed=0):
    ensure_scrape_runs_table(connection)
    finished_at = datetime.now(timezone.utc).isoformat()
    connection.execute(
        """
        INSERT INTO SCRAPE_RUNS (finished_at, listings_processed)
        VALUES (?, ?)
        """,
        (finished_at, listings_processed),
    )
    connection.commit()
    return finished_at


def latest_scrape_finished_at(connection):
    ensure_scrape_runs_table(connection)
    row = connection.execute(
        "SELECT finished_at FROM SCRAPE_RUNS ORDER BY id DESC LIMIT 1"
    ).fetchone()
    return row[0] if row else None
