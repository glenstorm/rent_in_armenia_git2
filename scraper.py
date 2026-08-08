"""Scrape list.am rent listings into real_estate.db."""

import sqlite3
import time

from city import districts
from currency_rates import CurrencyRates
from page_parser import PageParser
from scrape_meta import ensure_scrape_runs_table, record_scrape_run
from web_page import WebPage

REQUEST_DELAY_SEC = 2.0


def process_page(district_num, page_num):
    return WebPage.download(
        f"https://www.list.am/ru/category/56/{page_num}?cmtype=1&type=1&po=1&n={district_num}"
    )


def run_scrape(db_path="real_estate.db", progress=print):
    """
    Gather listings for Yerevan districts and store them in sqlite.
    `progress` is a callable used for status lines (default: print).
    """
    rates = CurrencyRates()
    total_saved = 0
    finished_at = None

    try:
        with sqlite3.connect(db_path) as connection:
            ensure_scrape_runs_table(connection)
            progress("Loading currency rates...")
            currencies = rates.get_rates(connection)
            progress(f"Rates ready: USD={currencies[1]}, EUR={currencies[2]}")

            district_ids = range(2, len(districts) + 1)
            for district_id in district_ids:
                name = districts[district_id - 1]
                progress(f"\n[{district_id - 1}/{len(districts) - 1}] {name}")
                district_saved = 0

                for page_num in range(1, 21):
                    if page_num > 1 or district_id > 2:
                        time.sleep(REQUEST_DELAY_SEC)

                    progress(f"  page {page_num}...")
                    content = process_page(district_id, page_num)
                    if not content:
                        progress("  no more pages")
                        break

                    district = PageParser.transform(content, district_id, currencies)
                    count = len(district.apartments)
                    district.flush_to_db(connection)
                    district_saved += count
                    total_saved += count
                    progress(f"  {count} listings")

                progress(f"  done: {district_saved} listings from {name}")
    finally:
        # Always persist finish time on a fresh connection (survives scrape errors /
        # closed handles from the long-lived scrape connection).
        try:
            with sqlite3.connect(db_path) as connection:
                finished_at = record_scrape_run(
                    connection, listings_processed=total_saved
                )
        except Exception as exc:
            progress(f"Failed to record scrape time: {exc}")

    progress(f"\nFinished at {finished_at}. Total listings processed: {total_saved}")
    return total_saved
