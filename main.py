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

from scraper import run_scrape

if __name__ == "__main__":
    try:
        run_scrape()
    except sqlite3.Error as error:
        print("Error while working with sqlite database:", error)
    except Exception as error:
        print("Unexpected error while scraping:", error)
