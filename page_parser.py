from lxml import html
import re

from apartment import Apartment, area_is_plausible
from district import District
from listam_links import normalize_listam_link


def _card_links(tree):
    """Listing cards under category grids (old direct <a> or redesigned wrappers)."""
    return tree.xpath(
        '//*[@id="contentr"]//div[contains(@class,"gl")]'
        '//a[contains(@href,"/item/")]'
    )


def _child_text(node):
    return (node.text_content() or "").strip()


def _parse_price_amd(price_text, currencies):
    """Parse list.am price text into AMD integer."""
    if not price_text:
        return None
    text = (
        price_text.replace("\u00a0", " ")
        .replace(",", "")
        .strip()
    )
    text = re.sub(r"в\s*месяц.*$", "", text, flags=re.IGNORECASE).strip()
    if not text:
        return None

    try:
        if "$" in text:
            num = re.search(r"([\d.]+)", text.replace("$", " "))
            if not num:
                return None
            return int(float(num.group(1)) * currencies[1])
        if "€" in text or "EUR" in text.upper():
            num = re.search(r"([\d.]+)", text)
            if not num:
                return None
            return int(float(num.group(1)) * currencies[2])
        # AMD (plain digits or ֏ suffix)
        num = re.search(r"([\d.]+)", text.replace("֏", " "))
        if not num:
            return None
        return int(float(num.group(1)))
    except (ValueError, TypeError, IndexError):
        return None


def _parse_rooms_and_square(detail_text):
    """
    Extract rooms + living m² from subtitle lines such as:
      "Кентрон, 2 ком., 55 кв.м."
      "2 ком., 55 кв.м., 3/8 этаж"
    """
    if not detail_text:
        return None, None
    rooms_match = re.search(r"(\d+)\s*ком\.", detail_text)
    square_match = re.search(
        r"(\d[\d\s\u00a0,]*)\s*кв\.?\s*м\.?",
        detail_text,
        flags=re.IGNORECASE,
    )
    if not rooms_match or not square_match:
        return None, None
    try:
        rooms = int(float(rooms_match.group(1)))
        raw = (
            square_match.group(1)
            .replace("\u00a0", "")
            .replace(" ", "")
            .replace(",", "")
        )
        square = int(float(raw))
    except (ValueError, TypeError):
        return None, None
    return rooms, square


class PageParser:
    """
    PageParser:: transform html page to data
    """

    @staticmethod
    def transform(page_content, region_id, currencies):
        dc = District(region_id)
        tree = html.fromstring(page_content)
        aparts = _card_links(tree)

        for apart in aparts:
            price = None
            where = None
            title = None
            link = normalize_listam_link(apart.get("href"))
            if not link:
                continue

            for divs in apart:
                classes = (divs.get("class") or "").strip()
                if classes == "p" or classes.startswith("p "):
                    price = _child_text(divs)
                elif classes == "l" or classes.startswith("l "):
                    title = _child_text(divs) or None
                elif (classes == "at" or classes.startswith("at ")) and "location" not in classes:
                    where = _child_text(divs)

            location_nodes = apart.xpath(
                './/*[contains(concat(" ", normalize-space(@class), " "), " location ")]'
                ' | .//*[contains(@class, "category-data-list-card__location")]'
            )
            location = _child_text(location_nodes[0]) if location_nodes else None

            if price is None or where is None:
                continue

            intprice = _parse_price_amd(price, currencies)
            if intprice is None:
                continue

            room_num, square = _parse_rooms_and_square(where)
            if room_num is None or square is None:
                continue
            if square <= 0 or room_num <= 0:
                continue
            if not area_is_plausible(room_num, square):
                continue

            if location and where:
                address = f"{location}, {where}"
            else:
                address = title or where

            dc.add(
                Apartment(
                    address,
                    room_num,
                    intprice,
                    square,
                    link,
                )
            )

        return dc
