"""Dilijan long-term rent listing helpers (apartments + houses)."""

PROPERTY_APARTMENT = "apartment"
PROPERTY_HOUSE = "house"

# Monthly rent sanity bands in AMD (after FX conversion).
MIN_RENT_PRICE_AMD = 20_000
MAX_RENT_PRICE_AMD = 5_000_000


def rent_price_is_plausible(price_amd) -> bool:
    try:
        price = int(price_amd)
    except (TypeError, ValueError):
        return False
    return MIN_RENT_PRICE_AMD <= price <= MAX_RENT_PRICE_AMD


class RentListing:
    def __init__(
        self,
        property_type,
        address="",
        room_num=0,
        price=0,
        square=None,
        link="",
        is_agent=False,
    ):
        self.property_type = property_type
        self.address = address
        self.room_num = int(room_num)
        self.price = int(price)
        self.square = int(square) if square not in (None, "") else None
        if self.square and self.square > 0:
            self.price_per_square = self.price / float(self.square)
        else:
            self.price_per_square = None
        self.link = link
        self.is_agent = bool(is_agent)
