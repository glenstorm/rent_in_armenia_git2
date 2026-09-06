"""Persist Dilijan long-term rent listings (apartments + houses)."""

from datetime import datetime, timezone

import numpy as np

from dilijan_rent import rent_price_is_plausible
from listam_links import (
    dedupe_table_by_link,
    find_listing_id_by_link,
    normalize_listam_link,
)


def ensure_dilijan_rent_schema(connection):
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS DILIJAN_RENT (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            property_type TEXT NOT NULL,
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
        CREATE TABLE IF NOT EXISTS DILIJAN_RENT_PRICE_HISTORY (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            listing_id INTEGER NOT NULL,
            price INTEGER NOT NULL,
            price_per_square REAL,
            scraped_at TEXT NOT NULL,
            FOREIGN KEY(listing_id) REFERENCES DILIJAN_RENT(id)
        );
        CREATE INDEX IF NOT EXISTS idx_dilijan_rent_type
            ON DILIJAN_RENT(property_type);
        CREATE INDEX IF NOT EXISTS idx_dilijan_rent_history_listing_time
            ON DILIJAN_RENT_PRICE_HISTORY(listing_id, scraped_at);
        """
    )
    connection.commit()
    dedupe_dilijan_rent_links(connection)


def dedupe_dilijan_rent_links(connection):
    return dedupe_table_by_link(
        connection,
        table="DILIJAN_RENT",
        history_table="DILIJAN_RENT_PRICE_HISTORY",
        listing_fk="listing_id",
    )


def ensure_dilijan_region(connection, location_id, location_name):
    connection.execute(
        """
        INSERT OR IGNORE INTO REGION (id, region_name)
        VALUES (?, ?)
        """,
        (location_id, location_name),
    )
    connection.commit()


def delete_dilijan_rent(connection, listing_id):
    cur = connection.cursor()
    cur.execute(
        "DELETE FROM DILIJAN_RENT_PRICE_HISTORY WHERE listing_id = ?",
        (listing_id,),
    )
    cur.execute("DELETE FROM DILIJAN_RENT WHERE id = ?", (listing_id,))
    connection.commit()
    return cur.rowcount


def delete_dilijan_rent_not_seen(connection, property_type, seen_links):
    canonical_seen = {
        normalize_listam_link(link) or link for link in seen_links if link
    }
    if not canonical_seen:
        return 0

    cur = connection.cursor()
    rows = cur.execute(
        "SELECT id, link FROM DILIJAN_RENT WHERE property_type = ?",
        (property_type,),
    ).fetchall()
    removed = 0
    for listing_id, link in rows:
        if (normalize_listam_link(link) or link) in canonical_seen:
            continue
        delete_dilijan_rent(connection, listing_id)
        removed += 1
    return removed


def flush_dilijan_rent_to_db(listings, connection, region_id):
    """Write RentListing objects; return number saved."""
    rows = [x for x in listings if rent_price_is_plausible(x.price)]
    if rows:
        prices = [x.price for x in rows]
        mean = np.mean(prices)
        stdev = np.std(prices) if len(prices) > 1 else 0.0
        if stdev > 0:
            lower = mean - 3 * stdev
            upper = mean + 3 * stdev
            rows = [x for x in rows if lower <= x.price <= upper]

    cur = connection.cursor()
    scraped_at = datetime.now(timezone.utc).isoformat()

    for item in rows:
        link = normalize_listam_link(item.link) or item.link
        listing_id = find_listing_id_by_link(cur, "DILIJAN_RENT", link)
        if listing_id:
            cur.execute(
                """
                UPDATE DILIJAN_RENT
                SET property_type = ?,
                    square = ?,
                    is_agent = ?,
                    region_id = ?,
                    price = ?,
                    price_per_square = ?,
                    room_num = ?,
                    address = ?,
                    link = ?
                WHERE id = ?
                """,
                (
                    item.property_type,
                    item.square,
                    item.is_agent,
                    region_id,
                    item.price,
                    item.price_per_square,
                    item.room_num,
                    item.address,
                    link,
                    listing_id,
                ),
            )
        else:
            cur.execute(
                """
                INSERT INTO DILIJAN_RENT
                    (property_type, square, is_agent, region_id, price,
                     price_per_square, room_num, address, link)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item.property_type,
                    item.square,
                    item.is_agent,
                    region_id,
                    item.price,
                    item.price_per_square,
                    item.room_num,
                    item.address,
                    link,
                ),
            )
            listing_id = cur.lastrowid

        cur.execute(
            """
            INSERT INTO DILIJAN_RENT_PRICE_HISTORY
                (listing_id, price, price_per_square, scraped_at)
            VALUES (?, ?, ?, ?)
            """,
            (listing_id, item.price, item.price_per_square, scraped_at),
        )

    connection.commit()
    return len(rows)
