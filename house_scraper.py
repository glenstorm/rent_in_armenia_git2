"""Scrape list.am house-sale listings for Tavush towns (category 1386)."""

import sqlite3
import time
from urllib.parse import quote

from city import (
    HOUSE_LOCATIONS,
    HOUSE_SALE_CATEGORY_ID,
    HOUSE_SEARCH_LOCATIONS,
    all_house_region_map,
)
from currency_rates import CurrencyRates
from house_parser import HousePageParser
from house_store import ensure_house_locations, ensure_houses_schema, flush_houses_to_db
from scrape_meta import ensure_scrape_runs_table, record_scrape_run
from web_page import WebPage

REQUEST_DELAY_SEC = 2.0


def process_house_page(location_id, page_num, category_id=HOUSE_SALE_CATEGORY_ID):
    if page_num <= 1:
        url = f"https://www.list.am/ru/category/{category_id}?n={location_id}"
    else:
        url = (
            f"https://www.list.am/ru/category/{category_id}/{page_num}"
            f"?n={location_id}"
        )
    return WebPage.download(url)


def process_house_search_page(query, page_num, category_id=HOUSE_SALE_CATEGORY_ID):
    q = quote(query)
    if page_num <= 1:
        url = f"https://www.list.am/ru/category/{category_id}?q={q}"
    else:
        url = f"https://www.list.am/ru/category/{category_id}/{page_num}?q={q}"
    return WebPage.download(url)


def _scrape_location_pages(
    *,
    connection,
    currencies,
    location_id,
    name,
    progress,
    fetch_page,
    place_aliases=None,
):
    location_saved = 0
    for page_num in range(1, 21):
        if page_num > 1:
            time.sleep(REQUEST_DELAY_SEC)

        progress(f"  page {page_num}...")
        content = fetch_page(page_num)
        if not content:
            progress("  no more pages")
            break

        batch = HousePageParser.transform(
            content,
            location_id,
            currencies,
            place_aliases=place_aliases,
        )
        count = len(batch.houses)
        if count == 0:
            progress("  0 matching listings — skipping further pages")
            break

        saved = flush_houses_to_db(batch, connection)
        location_saved += saved
        progress(f"  {saved} houses saved ({count} parsed)")

    progress(f"  done: {location_saved} houses from {name}")
    return location_saved


def run_house_scrape(db_path="real_estate.db", progress=print):
    """
    Gather Tavush house-sale listings:
    Dilijan / Ijevan (by n=),
    Haghartsin / Hovk (by search query + place-name filter).
    """
    rates = CurrencyRates()
    total_saved = 0
    finished_at = None

    try:
        with sqlite3.connect(db_path) as connection:
            ensure_scrape_runs_table(connection)
            ensure_houses_schema(connection)
            ensure_house_locations(connection, all_house_region_map())
            progress("Loading currency rates (houses)...")
            currencies = rates.get_rates(connection)
            progress(f"Rates ready: USD={currencies[1]}, EUR={currencies[2]}")

            locations = list(HOUSE_LOCATIONS.items())
            searches = list(HOUSE_SEARCH_LOCATIONS.items())
            total_targets = len(locations) + len(searches)
            index = 0

            for location_id, name in locations:
                index += 1
                if index > 1:
                    time.sleep(REQUEST_DELAY_SEC)
                progress(
                    f"\n[houses {index}/{total_targets}] {name} "
                    f"(category={HOUSE_SALE_CATEGORY_ID}, n={location_id})"
                )
                total_saved += _scrape_location_pages(
                    connection=connection,
                    currencies=currencies,
                    location_id=location_id,
                    name=name,
                    progress=progress,
                    fetch_page=lambda page_num, loc_id=location_id: process_house_page(
                        loc_id, page_num
                    ),
                )

            for location_id, meta in searches:
                index += 1
                time.sleep(REQUEST_DELAY_SEC)
                name = meta["name"]
                query = meta["query"]
                aliases = meta["place_aliases"]
                progress(
                    f"\n[houses {index}/{total_targets}] {name} "
                    f"(category={HOUSE_SALE_CATEGORY_ID}, search-query)"
                )
                total_saved += _scrape_location_pages(
                    connection=connection,
                    currencies=currencies,
                    location_id=location_id,
                    name=name,
                    progress=progress,
                    fetch_page=lambda page_num, q=query: process_house_search_page(
                        q, page_num
                    ),
                    place_aliases=aliases,
                )
    finally:
        try:
            with sqlite3.connect(db_path) as connection:
                finished_at = record_scrape_run(
                    connection, listings_processed=total_saved
                )
        except Exception as exc:
            progress(f"Failed to record house scrape time: {exc}")

    progress(
        f"\nHouse scrape finished at {finished_at}. "
        f"Total houses processed: {total_saved}"
    )
    return total_saved
