import requests

class CurrencyRates:

	@staticmethod
	def get_rates():
		response = requests.get("https://api.exchangerate-api.com/v4/latest/USD")
		date = response.json()['date']
		usd = response.json()['rates']['AMD']

		response = requests.get("https://api.exchangerate-api.com/v4/latest/EUR")
		eur = response.json()['rates']['AMD']

		return (date, usd, eur)
