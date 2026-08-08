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
                try:
                    usd_response = requests.get(
                        "https://api.exchangerate-api.com/v4/latest/USD",
                        timeout=30,
                    )
                    usd_response.raise_for_status()
                    usd_data = usd_response.json()

                    eur_response = requests.get(
                        "https://api.exchangerate-api.com/v4/latest/EUR",
                        timeout=30,
                    )
                    eur_response.raise_for_status()
                    eur_data = eur_response.json()

                    date = usd_data["date"]
                    usd = float(usd_data["rates"]["AMD"])
                    eur = float(eur_data["rates"]["AMD"])
                except (
                    requests.RequestException,
                    KeyError,
                    TypeError,
                    ValueError,
                ) as e:
                    raise RuntimeError(f"Failed to fetch currency rates: {e}") from e

                cur.execute(
                    "INSERT INTO CURRENCIES (cur_date, usd_rate, eur_rate) VALUES (?, ?, ?)",
                    (date, usd, eur),
                )
                sqlite_conn.commit()
                self.cur_currency = (date, usd, eur)
        return self.cur_currency
