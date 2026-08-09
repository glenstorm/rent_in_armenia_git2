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
