"""Scrape Dilijan long-term apartment and house rentals from list.am."""

import sqlite3
import time

from city import (
    APARTMENT_RENT_CATEGORY_ID,
    DILIJAN_LOCATION_ID,
    DILIJAN_LOCATION_NAME,
    HOUSE_RENT_CATEGORY_ID,
)
from currency_rates import CurrencyRates
from dilijan_rent import PROPERTY_APARTMENT, PROPERTY_HOUSE, RentListing, rent_price_is_plausible
from dilijan_rent_store import (
    delete_dilijan_rent_not_seen,
    ensure_dilijan_region,
    ensure_dilijan_rent_schema,
    flush_dilijan_rent_to_db,
)
from house_parser import HousePageParser, extract_item_links
from listam_links import normalize_listam_link
from page_parser import PageParser
from scrape_meta import ensure_scrape_runs_table, record_scrape_run
from web_page import WebPage

REQUEST_DELAY_SEC = 2.0
MAX_CATEGORY_PAGES = 500


def _download_category_page(category_id, location_id, page_num):
    if page_num <= 1:
        url = f"https://www.list.am/ru/category/{category_id}?n={location_id}"
    else:
        url = (
            f"https://www.list.am/ru/category/{category_id}/{page_num}"
            f"?n={location_id}"
        )
    return WebPage.download(url)


def _scrape_property_type(
    *,
    connection,
    currencies,
    property_type,
    category_id,
    progress,
    parse_page,
):
    saved_total = 0
    seen_links = set()
    page_num = 1

    while page_num <= MAX_CATEGORY_PAGES:
        if page_num > 1:
            time.sleep(REQUEST_DELAY_SEC)

        progress(f"  page {page_num}...")
        content = _download_category_page(
            category_id, DILIJAN_LOCATION_ID, page_num
        )
        if not content:
            progress("  no more pages")
            break

        listings, page_links = parse_page(content, currencies)
        if not listings and not page_links:
            progress("  0 listings — skipping further pages")
            break
        if not listings:
            progress("  0 matching listings — skipping further pages")
            break

        seen_links.update(page_links)
        saved = flush_dilijan_rent_to_db(
            listings, connection, region_id=DILIJAN_LOCATION_ID
        )
        saved_total += saved
        progress(f"  {len(listings)} matching / {saved} saved")
        page_num += 1
    else:
        progress(f"  reached safety page limit ({MAX_CATEGORY_PAGES}); stopping")

    if saved_total > 0 and seen_links:
        removed = delete_dilijan_rent_not_seen(
            connection, property_type, seen_links
        )
        if removed:
            progress(f"  removed {removed} stale {property_type} rent listing(s)")

    return saved_total


def _parse_apartments(content, currencies):
    apartments = PageParser.parse_apartments(content, currencies)
    listings = []
    links = set()
    for apt in apartments:
        if not rent_price_is_plausible(apt.price):
            continue
        link = normalize_listam_link(apt.link) or apt.link
        links.add(link)
        listings.append(
            RentListing(
                property_type=PROPERTY_APARTMENT,
                address=apt.address,
                room_num=apt.room_num,
                price=apt.price,
                square=apt.square,
                link=link,
                is_agent=apt.is_agent,
            )
        )
    # Also track all card links so unparsed active ads are not pruned.
    links.update(extract_item_links(content))
    return listings, links


def _parse_houses(content, currencies):
    batch = HousePageParser.transform(
        content,
        DILIJAN_LOCATION_ID,
        currencies,
        price_check=rent_price_is_plausible,
        region_name=DILIJAN_LOCATION_NAME,
    )
    listings = []
    links = set()
    for house in batch.houses:
        link = normalize_listam_link(house.link) or house.link
        links.add(link)
        listings.append(
            RentListing(
                property_type=PROPERTY_HOUSE,
                address=house.address,
                room_num=house.room_num,
                price=house.price,
                square=house.square,
                link=link,
                is_agent=house.is_agent,
            )
        )
    links.update(extract_item_links(content))
    return listings, links


def run_dilijan_rent_scrape(db_path="real_estate.db", progress=print):
    """Scrape Dilijan apartment + house long-term rents into DILIJAN_RENT."""
    rates = CurrencyRates()
    total_saved = 0
    finished_at = None

    try:
        with sqlite3.connect(db_path) as connection:
            ensure_scrape_runs_table(connection)
            ensure_dilijan_rent_schema(connection)
            ensure_dilijan_region(
                connection, DILIJAN_LOCATION_ID, DILIJAN_LOCATION_NAME
            )
            progress("Loading currency rates (Dilijan rent)...")
            currencies = rates.get_rates(connection)
            progress(f"Rates ready: USD={currencies[1]}, EUR={currencies[2]}")

            progress(
                f"\n[Dilijan rent 1/2] apartments "
                f"(category={APARTMENT_RENT_CATEGORY_ID}, n={DILIJAN_LOCATION_ID})"
            )
            total_saved += _scrape_property_type(
                connection=connection,
                currencies=currencies,
                property_type=PROPERTY_APARTMENT,
                category_id=APARTMENT_RENT_CATEGORY_ID,
                progress=progress,
                parse_page=_parse_apartments,
            )

            time.sleep(REQUEST_DELAY_SEC)
            progress(
                f"\n[Dilijan rent 2/2] houses "
                f"(category={HOUSE_RENT_CATEGORY_ID}, n={DILIJAN_LOCATION_ID})"
            )
            total_saved += _scrape_property_type(
                connection=connection,
                currencies=currencies,
                property_type=PROPERTY_HOUSE,
                category_id=HOUSE_RENT_CATEGORY_ID,
                progress=progress,
                parse_page=_parse_houses,
            )
    finally:
        try:
            with sqlite3.connect(db_path) as connection:
                finished_at = record_scrape_run(
                    connection, listings_processed=total_saved
                )
        except Exception as exc:
            progress(f"Failed to record Dilijan rent scrape time: {exc}")

    progress(
        f"\nDilijan rent scrape finished at {finished_at}. "
        f"Total listings processed: {total_saved}"
    )
    return total_saved
