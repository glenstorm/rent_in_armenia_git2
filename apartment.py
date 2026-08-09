class Apartment:
    def __init__(
        self, address="", room_num=0, price=0, square=0, link="", is_agent=False
    ):
        self.address = address
        self.room_num = int(room_num)
        self.price = int(price)
        self.square = int(square)
        self.price_per_square = (
            (self.price / float(self.square)) if self.square else 0.0
        )
        self.link = link
        self.is_agent = bool(is_agent)

    def __str__(self):
        return f"{self.address}\t{self.room_num}\t{self.price}\t{self.square}\t{self.price_per_square}\t{self.link}\t{self.is_agent}"


# Wide but realistic living-area band (m²) for Yerevan flat rentals on list.am.
# Tiny values (3–14 m²) and huge typos (640 m²) are rejected; large luxury flats pass.
_SQUARE_BOUNDS_BY_ROOMS = {
    1: (16, 150),
    2: (25, 220),
    3: (40, 350),
    4: (50, 450),
}


def area_is_plausible(room_num, square) -> bool:
    """Return False for listings with impossible square vs room count."""
    try:
        rooms = int(room_num)
        area = int(square)
    except (TypeError, ValueError):
        return False
    if rooms <= 0 or area <= 0:
        return False
    if rooms >= 5:
        return 60 <= area <= 500
    low, high = _SQUARE_BOUNDS_BY_ROOMS.get(rooms, (16, 400))
    return low <= area <= high
