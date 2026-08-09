"""Listing price history helpers for real_estate.db."""

from datetime import datetime, timezone


def ensure_price_history_table(connection):
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS LISTING_PRICE_HISTORY (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            listing_id INTEGER NOT NULL,
            price INTEGER NOT NULL,
            price_per_square REAL NOT NULL,
            scraped_at TEXT NOT NULL,
            FOREIGN KEY(listing_id) REFERENCES REAL_ESTATE(id)
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_listing_price_history_listing_time
        ON LISTING_PRICE_HISTORY(listing_id, scraped_at)
        """
    )
    connection.commit()


def backfill_price_history(connection):
    """
    Seed one history row per existing listing that has no history yet.
    Uses REAL_ESTATE.ddate at noon UTC when available.
    """
    ensure_price_history_table(connection)
    connection.execute(
        """
        INSERT INTO LISTING_PRICE_HISTORY
            (listing_id, price, price_per_square, scraped_at)
        SELECT
            r.id,
            r.price,
            r.price_per_square,
            COALESCE(r.ddate || 'T12:00:00+00:00', ?)
        FROM REAL_ESTATE r
        WHERE NOT EXISTS (
            SELECT 1 FROM LISTING_PRICE_HISTORY h WHERE h.listing_id = r.id
        )
        """,
        (datetime.now(timezone.utc).isoformat(),),
    )
    connection.commit()


def record_price_history(connection, listing_id, price, price_per_square, scraped_at=None):
    if scraped_at is None:
        scraped_at = datetime.now(timezone.utc).isoformat()
    connection.execute(
        """
        INSERT INTO LISTING_PRICE_HISTORY
            (listing_id, price, price_per_square, scraped_at)
        VALUES (?, ?, ?, ?)
        """,
        (listing_id, price, price_per_square, scraped_at),
    )
