"""Parse list.am house-sale category pages into House objects."""

import re

from lxml import html

from city import all_house_region_map
from house import (
    House,
    house_area_is_plausible,
    house_price_is_plausible,
    house_rooms_are_plausible,
)


def _card_links(tree):
    return tree.xpath(
        '//*[@id="contentr"]//div[contains(@class,"gl")]'
        '//a[contains(@href,"/item/")]'
    )


def _child_text(node):
    return (node.text_content() or "").strip()


def _normalize_item_link(href):
    if not href:
        return None
    path = href.split("?", 1)[0]
    if path.startswith("http"):
        return path
    return "https://www.list.am" + path


class HouseBatch:
    def __init__(self, location_id):
        self.id = location_id
        self.name = all_house_region_map()[location_id]
        self.houses = []

    def add(self, house):
        if not house_rooms_are_plausible(house.room_num):
            return
        if not house_price_is_plausible(house.price):
            return
        if not house_area_is_plausible(house.square):
            return
        self.houses.append(house)


class HousePageParser:
    """Transform a house-sale category HTML page into a HouseBatch."""

    @staticmethod
    def transform(page_content, location_id, currencies, place_aliases=None):
        batch = HouseBatch(location_id)
        tree = html.fromstring(page_content)
        cards = _card_links(tree)

        for card in cards:
            price_text = None
            where = None
            title = None
            link = _normalize_item_link(card.get("href"))
            if not link:
                continue

            for child in card:
                classes = (child.get("class") or "").strip()
                if classes == "p" or classes.startswith("p "):
                    price_text = _child_text(child)
                elif classes == "l" or classes.startswith("l "):
                    title = _child_text(child) or None
                elif (classes == "at" or classes.startswith("at ")) and "location" not in classes:
                    where = _child_text(child)

            location_nodes = card.xpath(
                './/*[contains(@class, "category-data-list-card__location")]'
            )
            location = _child_text(location_nodes[0]) if location_nodes else None

            if price_text is None or where is None:
                continue

            place_for_filter = location or where
            if place_aliases and not HousePageParser._place_matches(
                place_for_filter, place_aliases
            ):
                continue

            intprice = HousePageParser._parse_price(price_text, currencies)
            if intprice is None:
                continue

            room_num = HousePageParser._parse_rooms(where)
            if room_num is None:
                continue

            # Living area is in the listing title (div.l), e.g.
            # "... в Дилижане, 222 кв.м., на участке 344 кв.м., 2 ванные"
            square = HousePageParser._parse_living_square(title or where)

            batch.add(
                House(
                    address=title or where,
                    room_num=room_num,
                    price=intprice,
                    square=square,
                    link=link,
                )
            )

        return batch

    @staticmethod
    def _place_matches(where, aliases):
        # New cards: location is a short place name ("Дилижан").
        # Older cards: place is the first comma-separated token of .at.
        place = where.split(",")[0].strip().casefold()
        return any(place == str(alias).strip().casefold() for alias in aliases)

    @staticmethod
    def _parse_price(price_text, currencies):
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
            if "€" in text:
                num = re.search(r"([\d.]+)", text)
                if not num:
                    return None
                return int(float(num.group(1)) * currencies[2])
            num = re.search(r"([\d.]+)", text.replace("֏", " "))
            if not num:
                return None
            return int(float(num.group(1)))
        except (ValueError, TypeError, IndexError):
            return None

    @staticmethod
    def _parse_rooms(where):
        """Subtitle may be "Дилижан, 4 ком." or just "4 ком."."""
        match = re.search(r"(\d+)\s*ком\.", where or "")
        if not match:
            return None
        try:
            return int(float(match.group(1)))
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _parse_living_square(title_text):
        """
        Extract house living area from title text.

        Prefer the first "N кв.м." that is not the land plot size
        ("на участке N кв.м.").
        """
        if not title_text:
            return None

        # Drop the land-plot clause so we never pick plot m² by mistake.
        living_part = re.split(
            r"\bна участке\b", title_text, maxsplit=1, flags=re.IGNORECASE
        )[0]

        match = re.search(
            r"(\d[\d\s\u00a0,]*)\s*кв\.?\s*м\.?",
            living_part,
            flags=re.IGNORECASE,
        )
        if not match:
            return None

        raw = match.group(1).replace("\u00a0", "").replace(" ", "")
        # list.am uses comma as thousands separator in titles ("2,000")
        raw = raw.replace(",", "")
        try:
            value = int(float(raw))
        except (ValueError, TypeError):
            return None
        return value if value > 0 else None
