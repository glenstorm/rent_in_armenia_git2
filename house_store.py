"""Persist Dilijan (and other) house-sale listings + price history."""

from datetime import datetime, timezone

import numpy as np

from house import house_price_is_plausible
from listam_links import (
    dedupe_table_by_link,
    find_listing_id_by_link,
    normalize_listam_link,
)


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
    dedupe_house_links(connection)


def dedupe_house_links(connection):
    """Collapse HOUSES rows that differ only by ?ld_src=… etc."""
    return dedupe_table_by_link(
        connection,
        table="HOUSES",
        history_table="HOUSE_PRICE_HISTORY",
        listing_fk="listing_id",
    )


def delete_house(connection, listing_id):
    """Remove one HOUSES row and its price history."""
    cur = connection.cursor()
    cur.execute(
        "DELETE FROM HOUSE_PRICE_HISTORY WHERE listing_id = ?",
        (listing_id,),
    )
    cur.execute("DELETE FROM HOUSES WHERE id = ?", (listing_id,))
    connection.commit()
    return cur.rowcount


def delete_houses_not_seen(connection, region_id, seen_links):
    """
    Remove HOUSES in region_id whose canonical link was not observed
    in the latest successful scrape of that location.
    """
    canonical_seen = {
        normalize_listam_link(link) or link for link in seen_links if link
    }
    if not canonical_seen:
        return 0

    cur = connection.cursor()
    rows = cur.execute(
        "SELECT id, link FROM HOUSES WHERE region_id = ?",
        (region_id,),
    ).fetchall()
    removed = 0
    for listing_id, link in rows:
        if (normalize_listam_link(link) or link) in canonical_seen:
            continue
        delete_house(connection, listing_id)
        removed += 1
    return removed


def prune_inactive_houses(
    connection,
    progress=print,
    delay_sec=1.0,
    check_fn=None,
):
    """
    Drop HOUSES rows whose list.am item page is gone (404 etc.).

    Unknown / transient check failures are left in place.
    Returns dict with removed / kept / unknown counts.
    """
    import time

    from web_page import WebPage

    if check_fn is None:
        check_fn = WebPage.item_is_active

    cur = connection.cursor()
    rows = cur.execute("SELECT id, link FROM HOUSES ORDER BY id").fetchall()
    removed = 0
    kept = 0
    unknown = 0

    progress(f"Checking {len(rows)} house listing(s) for removed ads...")
    for index, (listing_id, link) in enumerate(rows, start=1):
        if index > 1 and delay_sec > 0:
            time.sleep(delay_sec)
        url = normalize_listam_link(link) or link
        status = check_fn(url)
        if status is True:
            kept += 1
            continue
        if status is None:
            unknown += 1
            progress(f"  skip (unknown): {url}")
            continue
        delete_house(connection, listing_id)
        removed += 1
        progress(f"  removed inactive: {url}")

    progress(
        f"Inactive prune done: removed={removed}, kept={kept}, unknown={unknown}"
    )
    return {"removed": removed, "kept": kept, "unknown": unknown}


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
        link = normalize_listam_link(house.link) or house.link
        listing_id = find_listing_id_by_link(cur, "HOUSES", link)
        if listing_id:
            cur.execute(
                """
                UPDATE HOUSES
                SET square = ?,
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
                    house.square,
                    house.is_agent,
                    batch.id,
                    house.price,
                    house.price_per_square,
                    house.room_num,
                    house.address,
                    link,
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
                    link,
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
