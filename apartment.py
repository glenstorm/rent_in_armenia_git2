class Apartment:
    def __init__(self, address='', room_num=0, price=0, square=0, link='', is_agent=False):
        self.address = address
        self.room_num = int(room_num)
        self.price = int(price)
        self.square = int(square)
        self.price_per_square = (self.price / float(self.square)) if self.square else 0.0
        self.link = link
        self.is_agent = bool(is_agent)

    def __str__(self):
        return f"{self.address}\t{self.room_num}\t{self.price}\t{self.square}\t{self.price_per_square}\t{self.link}\t{self.is_agent}"
