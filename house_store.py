"""Persist Dilijan (and other) house-sale listings + price history."""

from datetime import datetime, timezone

import numpy as np

from house import house_price_is_plausible


def ensure_houses_schema(connection):
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS HOUSES (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            square INTEGER,
            is_agent INTEGER,
            region_id INTEGER,
            price INTEGER NOT NULL,
            price_per_square REAL,
            room_num INTEGER NOT NULL,
            address TEXT NOT NULL,
            link TEXT NOT NULL UNIQUE,
            ddate DATE NOT NULL DEFAULT CURRENT_DATE,
            FOREIGN KEY(region_id) REFERENCES REGION(id)
        );
        CREATE TABLE IF NOT EXISTS HOUSE_PRICE_HISTORY (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            listing_id INTEGER NOT NULL,
            price INTEGER NOT NULL,
            price_per_square REAL,
            scraped_at TEXT NOT NULL,
            FOREIGN KEY(listing_id) REFERENCES HOUSES(id)
        );
        CREATE INDEX IF NOT EXISTS idx_house_price_history_listing_time
            ON HOUSE_PRICE_HISTORY(listing_id, scraped_at);
        """
    )
    connection.commit()


def ensure_house_locations(connection, locations):
    """Insert REGION rows for house locations if missing."""
    cur = connection.cursor()
    for location_id, name in locations.items():
        cur.execute(
            """
            INSERT OR IGNORE INTO REGION (id, region_name)
            VALUES (?, ?)
            """,
            (location_id, name),
        )
    connection.commit()


def record_house_price_history(
    connection, listing_id, price, price_per_square, scraped_at=None
):
    if scraped_at is None:
        scraped_at = datetime.now(timezone.utc).isoformat()
    connection.execute(
        """
        INSERT INTO HOUSE_PRICE_HISTORY
            (listing_id, price, price_per_square, scraped_at)
        VALUES (?, ?, ?, ?)
        """,
        (listing_id, price, price_per_square, scraped_at),
    )


def flush_houses_to_db(batch, connection):
    """Write a HouseBatch to HOUSES and append history rows."""
    houses = list(batch.houses)
    if houses:
        prices = [h.price for h in houses]
        mean = np.mean(prices)
        stdev = np.std(prices) if len(prices) > 1 else 0.0
        if stdev > 0:
            lower = mean - 3 * stdev
            upper = mean + 3 * stdev
            houses = [h for h in houses if lower <= h.price <= upper]
        houses = [h for h in houses if house_price_is_plausible(h.price)]

    cur = connection.cursor()
    scraped_at = datetime.now(timezone.utc).isoformat()

    for house in houses:
        cur.execute("SELECT id FROM HOUSES WHERE link = ? LIMIT 1", (house.link,))
        row = cur.fetchone()
        if row:
            listing_id = row[0]
            cur.execute(
                """
                UPDATE HOUSES
                SET square = ?,
                    is_agent = ?,
                    region_id = ?,
                    price = ?,
                    price_per_square = ?,
                    room_num = ?,
                    address = ?
                WHERE id = ?
                """,
                (
                    house.square,
                    house.is_agent,
                    batch.id,
                    house.price,
                    house.price_per_square,
                    house.room_num,
                    house.address,
                    listing_id,
                ),
            )
        else:
            cur.execute(
                """
                INSERT INTO HOUSES
                    (square, is_agent, region_id, price, price_per_square,
                     room_num, address, link)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    house.square,
                    house.is_agent,
                    batch.id,
                    house.price,
                    house.price_per_square,
                    house.room_num,
                    house.address,
                    house.link,
                ),
            )
            listing_id = cur.lastrowid

        record_house_price_history(
            connection,
            listing_id=listing_id,
            price=house.price,
            price_per_square=house.price_per_square,
            scraped_at=scraped_at,
        )

    connection.commit()
    return len(houses)
