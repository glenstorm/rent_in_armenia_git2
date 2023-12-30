class Apartment:

	def __init__(self, address='', room_num=0, price=0, square=0, link='', is_agent=False):
		self.address  = address
		self.room_num = room_num
		self.price    = price
		self.square   = square
		self.link     = link
		self.is_agent = is_agent

	def __str__(self):
		return "{0}\t{1}\t{2}\t{3}\t{4}\t{5}".format(self.address, self.room_num, self.price, self.square, self.link, self.is_agent)
