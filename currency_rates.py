import requests

class CurrencyRates:
	def __init__(self):
		self.cur_currency = None

	def get_rates(self, sqlite_conn):
		if self.cur_currency is None:
			cur = sqlite_conn.cursor()
			cur.execute("SELECT * FROM CURRENCIES WHERE cur_date = CURRENT_DATE")
			row = cur.fetchone()
			if row:
				self.cur_currency = (row[1], row[2], row[3])
			else:
				response = requests.get("https://api.exchangerate-api.com/v4/latest/USD")
				date = response.json()['date']
				usd = response.json()['rates']['AMD']

				response = requests.get("https://api.exchangerate-api.com/v4/latest/EUR")
				eur = response.json()['rates']['AMD']

				cur.execute("INSERT INTO CURRENCIES (cur_date, usd_rate, eur_rate) VALUES (?, ?, ?)", (date, usd, eur))
				sqlite_conn.commit()

				self.cur_currency = (date, usd, eur)

		return self.cur_currency
