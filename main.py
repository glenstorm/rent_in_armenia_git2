# base url for apartaments:
# https://www.list.am/ru/category/56
# params:
# cmtype={1|2} = {частные|агентства}
# type={1|2} = {предлагаю|ищу}
# n={id} — see DISTRICTS in city.py (explicit list.am id → name)

import sqlite3

from scraper import run_scrape

if __name__ == "__main__":
    try:
        run_scrape()
    except sqlite3.Error as error:
        print("Error while working with sqlite database:", error)
    except Exception as error:
        print("Unexpected error while scraping:", error)
