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
from house_parser import HousePageParser, extract_item_links
from house_store import (
    delete_houses_not_seen,
    ensure_house_locations,
    ensure_houses_schema,
    flush_houses_to_db,
    prune_inactive_houses,
)
from listam_links import normalize_listam_link
from scrape_meta import ensure_scrape_runs_table, record_scrape_run
from web_page import WebPage

REQUEST_DELAY_SEC = 2.0
MAX_CATEGORY_PAGES = 500


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
    seen_links = set()
    page_num = 1
    while page_num <= MAX_CATEGORY_PAGES:
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

        if place_aliases:
            seen_links.update(
                normalize_listam_link(h.link) or h.link for h in batch.houses
            )
        else:
            seen_links.update(extract_item_links(content))

        saved = flush_houses_to_db(batch, connection)
        location_saved += saved
        progress(f"  {count} matching / {saved} saved")
        page_num += 1
    else:
        progress(f"  reached safety page limit ({MAX_CATEGORY_PAGES}); stopping")

    if location_saved > 0 and seen_links:
        removed = delete_houses_not_seen(connection, location_id, seen_links)
        if removed:
            progress(
                f"  removed {removed} stale listing(s) no longer on list.am for {name}"
            )

    progress(f"  done: {location_saved} houses from {name}")
    return location_saved


def run_house_scrape(
    db_path="real_estate.db",
    progress=print,
    prune_inactive=False,
    prune_only=False,
):
    """
    Gather Tavush house-sale listings:
    Dilijan / Ijevan (by n=),
    Haghartsin / Hovk (by search query + place-name filter).

    After each successful town scrape, listings no longer present on
    list.am for that town are removed. Optional HTTP prune checks every
    stored item page (use --prune-inactive-only).
    """
    rates = CurrencyRates()
    total_saved = 0
    finished_at = None
    prune_stats = None

    try:
        with sqlite3.connect(db_path) as connection:
            ensure_scrape_runs_table(connection)
            ensure_houses_schema(connection)
            ensure_house_locations(connection, all_house_region_map())

            if not prune_only:
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

            if prune_inactive or prune_only:
                progress("\nPruning inactive house listings...")
                prune_stats = prune_inactive_houses(
                    connection,
                    progress=progress,
                    delay_sec=REQUEST_DELAY_SEC,
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
    if prune_stats:
        progress(
            f"Inactive removed: {prune_stats['removed']} "
            f"(kept={prune_stats['kept']}, unknown={prune_stats['unknown']})"
        )
    return total_saved
