import os
from lxml import html
from district import District
from apartment import Apartment

class PageParser:
	'''
	PageParser:: transform html page to data
	'''
	@staticmethod
	def transform(page_content, region_id, currencies):
		dc = District(region_id)
		tree = html.fromstring(page_content)
		aparts = tree.xpath('//*[@id="contentr"]/div[@class="dl"]/div[@class="gl"]/a[*]')

		for apart in aparts:
			price = None
			where = None
			link = apart.values()[0]
			for divs in apart:
				if divs.attrib == {'class': 'p'}:
					price = divs.text
				if divs.attrib == {'class': 'at'}:
					where = divs.text

			if price is not None and where is not None:
				# price part
				intprice = 0
				price = price.replace(',', '')
				index = price.find(' ')
				if index != -1:
					price = price[:index]

				if price[0] == '$':
					price = price[1:]
					intprice = int(price) * currencies[1]
				elif price[0] == '€':
					price = price[1:]
					intprice = int(price) * currencies[2]
				else:
					intprice = int(price)

				# square part
				index_where = where.find(" кв.м.")
				leftborderwhere = -1
				if index_where != -1:
					leftborderwhere = where.rfind(', ', 0, index_where)

				index_rooms = where.find(" ком.")
				leftborderrooms = -1
				if index_rooms != -1:
					leftborderrooms  = where.rfind(', ', 0, index_rooms)
				# print(str(leftborderwhere))
				if leftborderwhere != -1 and leftborderrooms != -1:
					newwhere = where[leftborderwhere+2:index_where]
					newrooms = where[leftborderrooms+2:index_rooms]
					dc.add(Apartment(where, newrooms, intprice, newwhere, "https://www.list.am" + link))

		return dc
