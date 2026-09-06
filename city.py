"""Yerevan districts for list.am.

Keys are the `n` query parameter values used in:
  https://www.list.am/ru/category/56/...?n=<id>

Nubarashen (n=12) is omitted entirely.
"""

# Explicit ordered mapping: list.am GET `n` → district name
DISTRICTS = {
    1: "Yerevan",
    2: "Achapnyack",
    3: "Arabkir",
    4: "Avan",
    5: "Davidashen",
    6: "Erebuni",
    7: "Zeitun_Kanaker",
    8: "Kentron",
    9: "Malatia_Sebastia",
    10: "Nor_Nork",
    11: "Nork_Marash",
    13: "Shengavit",
}


def district_name(district_id):
    """Return the display name for a list.am district id."""
    try:
        return DISTRICTS[district_id]
    except KeyError as exc:
        raise ValueError(f"Unknown district id: {district_id}") from exc


def scrape_district_ids():
    """District ids to scrape (all mapped districts except city-wide Yerevan)."""
    return [district_id for district_id in DISTRICTS if district_id != 1]


# Backward-compatible name list in mapping order (includes Yerevan).
districts = list(DISTRICTS.values())


# list.am location `n` for Tavush house-sale scrapes (category 1386)
HOUSE_LOCATIONS = {
    58: "Dilijan",
    60: "Ijevan",
}

# Villages without a stable list.am `n` filter — scrape via ?q= and match place name.
# REGION ids are synthetic (do not collide with list.am n values above).
HOUSE_SEARCH_LOCATIONS = {
    1001: {
        "name": "Haghartsin",
        "query": "Агарцин",
        "place_aliases": ("Агарцин", "Haghartsin", "Հաղարծին"),
    },
    1002: {
        "name": "Hovk",
        "query": "Hovk",
        "place_aliases": ("Овк", "Hovk", "Հովք"),
    },
}

# Houses for sale on list.am
HOUSE_SALE_CATEGORY_ID = 1386

# Dilijan long-term rent (list.am n=58)
DILIJAN_LOCATION_ID = 58
DILIJAN_LOCATION_NAME = "Dilijan"
APARTMENT_RENT_CATEGORY_ID = 56  # same category as Yerevan flats
HOUSE_RENT_CATEGORY_ID = 1377


def all_house_region_map():
    """region_id → display name for every house market we store."""
    regions = dict(HOUSE_LOCATIONS)
    for location_id, meta in HOUSE_SEARCH_LOCATIONS.items():
        regions[location_id] = meta["name"]
    return regions
