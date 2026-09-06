"""House-for-sale listing model (list.am category 1386, etc.)."""


class House:
    def __init__(
        self,
        address="",
        room_num=0,
        price=0,
        square=None,
        link="",
        is_agent=False,
    ):
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

    def __str__(self):
        return (
            f"{self.address}\t{self.room_num}\t{self.price}\t{self.square}\t"
            f"{self.price_per_square}\t{self.link}\t{self.is_agent}"
        )


# Sale-price sanity band in AMD (after FX conversion). Filters typos like $100.
MIN_HOUSE_PRICE_AMD = 3_000_000
MAX_HOUSE_PRICE_AMD = 2_000_000_000


def house_price_is_plausible(price_amd) -> bool:
    try:
        price = int(price_amd)
    except (TypeError, ValueError):
        return False
    return MIN_HOUSE_PRICE_AMD <= price <= MAX_HOUSE_PRICE_AMD


def house_rooms_are_plausible(room_num) -> bool:
    try:
        rooms = int(room_num)
    except (TypeError, ValueError):
        return False
    return 1 <= rooms <= 30


def house_area_is_plausible(square) -> bool:
    """Optional living area; list cards often omit it."""
    if square in (None, ""):
        return True
    try:
        area = int(square)
    except (TypeError, ValueError):
        return False
    return 20 <= area <= 5000
