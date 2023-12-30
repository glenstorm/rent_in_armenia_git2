# base url for apartaments:
# https://www.list.am/ru/category/56
# params:
# cmtype={1|2} = {частные|агентства}
# type={1|2} = {предлагаю|ищу}
# n={i}, где i - район
# n=1 - Yerevan
# n=2 - Achapnyack
# n=3 - Arabkir
# n=4 - Avan
# n=5 - Davidashen
# n=6 - Erebuni
# n=7 - Zeitun_Kanaker
# n=8 - Kentron
# n=9 - Malatia_Sebastia
# n=10 - Nor_Nork
# n=11 - Nork_Marash
# n=12 - Nubarashen
# n=13 - Shengavit


import sqlite3
from time import sleep
from city import districts
from web_page import WebPage
from district import District
from page_parser import PageParser
from currency_rates import CurrencyRates

def process_page(district_num, page_num):
	return WebPage.download('https://www.list.am/ru/category/56/{1}?cmtype=1&type=1&po=1&n={0}'.format(district_num, page_num))


if __name__ == "__main__":
	# update currency rates
	try:
		connection = sqlite3.connect('real_estate.db')
		# cur = connection.cursor()
		# cur.execute("REPLACE INTO CURRENCIES (cur_date, usd_rate, eur_rate) VALUES (?, ?, ?)", (CurrencyRates.get_rates()))
		# connection.commit()

		# districts = ['Yerevan', 'Achapnyack', 'Arabkir', 'Avan', 'Davidashen', 'Erebuni', 'Zeitun_Kanaker', 'Kentron', 'Malatia_Sebastia', 'Nor_Nork', 'Nork_Marash', 'Nubarashen', 'Shengavit']
		for district_id in range(2, len(districts)):
			for y in range(1, 21):
				content = process_page(district_id, y)
				if content:
					district = PageParser.transform(content, district_id, CurrencyRates.get_rates())
					district.flush_to_db(connection)
					exit()
					# district.print_apartments()
					# text_file = open("{0}-{1}.html".format(districts[x-1], y), "w")
					# n = text_file.write(content)
					# text_file.close()
				else:
					break;
	finally:
		connection.close()
