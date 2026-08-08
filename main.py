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
import time

from city import districts
from currency_rates import CurrencyRates
from page_parser import PageParser
from web_page import WebPage

# Pause between requests so list.am is less likely to return 429
REQUEST_DELAY_SEC = 2.0


def process_page(district_num, page_num):
    return WebPage.download(
        f"https://www.list.am/ru/category/56/{page_num}?cmtype=1&type=1&po=1&n={district_num}"
    )


if __name__ == "__main__":
    rates = CurrencyRates()
    try:
        with sqlite3.connect("real_estate.db") as connection:
            print("Loading currency rates...", flush=True)
            currencies = rates.get_rates(connection)
            print(f"Rates ready: USD={currencies[1]}, EUR={currencies[2]}", flush=True)

            total_saved = 0
            # URL n is 1-based: 2..13 are districts (skip city-wide Yerevan = 1)
            district_ids = range(2, len(districts) + 1)
            for district_id in district_ids:
                name = districts[district_id - 1]
                print(f"\n[{district_id - 1}/{len(districts) - 1}] {name}", flush=True)
                district_saved = 0

                for page_num in range(1, 21):
                    if page_num > 1 or district_id > 2:
                        time.sleep(REQUEST_DELAY_SEC)

                    print(f"  page {page_num}...", end=" ", flush=True)
                    content = process_page(district_id, page_num)
                    if not content:
                        print("no more pages", flush=True)
                        break

                    district = PageParser.transform(
                        content, district_id, currencies
                    )
                    count = len(district.apartments)
                    district.flush_to_db(connection)
                    district_saved += count
                    total_saved += count
                    print(f"{count} listings", flush=True)

                print(f"  done: {district_saved} listings from {name}", flush=True)

            print(f"\nFinished. Total listings processed: {total_saved}", flush=True)

    except sqlite3.Error as error:
        print("Error while working with sqlite database:", error)
    except Exception as error:
        print("Unexpected error while scraping:", error)
