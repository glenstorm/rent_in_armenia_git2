from apartment import Apartment

class District:
	'''
	DistrictChunk: info about prices in region
	'''

	def __init__(self, id):
		self.id = id
		self.apartments = []

	def add(self, apartment):
		self.apartments.append(apartment)

	def print_apartments(self):
		for x in self.apartments:
			print(x)

	def flush_to_db(self, connection):
		cur = connection.cursor()
		for x in self.apartments:
			cur.execute("INSERT INTO REAL_ESTATE (square, is_agent, region_id, price, price_per_square, room_num, address, link) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (x.square, x.is_agent, self.id, x.price, x.price/float(x.square), x.room_num, x.address, x.link))

		connection.commit()
