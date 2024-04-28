from city import districts
from apartment import Apartment
import numpy as np

class District:
	'''
	DistrictChunk: info about prices in region
	'''

	def __init__(self, id):
		self.id = id
		self.name = districts[self.id]
		self.apartments = []

	def add(self, apartment):
		self.apartments.append(apartment)

	def print_apartments(self):
		for x in self.apartments:
			print(x)

	def __fix_data(self):
		if len(self.apartments) == 0:
			return

		prices = [obj.price for obj in self.apartments]
		# print(f"price median = {median(prices)}")
		# print(f"price stdev = {stdev(prices)}")
		mean = np.mean(prices)
		stdev = np.std(prices)
		# Define the range
		lower_bound = mean - 3 * stdev
		upper_bound = mean + 3 * stdev

		self.apartments = list(filter(lambda data: (data.price >= lower_bound) & (data.price <= upper_bound), self.apartments))

	def flush_to_db(self, connection):
		self.__fix_data()

		cur = connection.cursor()
		for x in self.apartments:
			cur.execute("INSERT INTO REAL_ESTATE (square, is_agent, region_id, price, price_per_square, room_num, address, link) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (x.square, x.is_agent, self.id, x.price, x.price_per_square, x.room_num, x.address, x.link))

		connection.commit()
