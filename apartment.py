class Apartment:

	def __init__(self, address='', room_num=0, price=0, square=0, link='', is_agent=False):
		self.address  = address
		self.room_num = room_num
		self.price    = price
		self.square   = square
		self.price_per_square = self.price/float(self.square)
		self.link     = link
		self.is_agent = is_agent

	def __str__(self):
		return f"{self.address}\t{self.room_num}\t{self.price}\t{self.square}\t{self.price_per_square}\t{self.link}\t{self.is_agent}"
