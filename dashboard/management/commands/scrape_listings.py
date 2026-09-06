"""Run the list.am scrape into real_estate.db (same work as main.py)."""

from django.conf import settings
from django.core.management.base import BaseCommand

from house_scraper import run_house_scrape
from scraper import run_scrape


class Command(BaseCommand):
    help = "Scrape list.am rent flats and Tavush house sales into real_estate.db"

    def add_arguments(self, parser):
        parser.add_argument(
            "--houses-only",
            action="store_true",
            help="Only scrape Tavush houses (skip Yerevan rent flats)",
        )
        parser.add_argument(
            "--flats-only",
            action="store_true",
            help="Only scrape Yerevan rent flats (skip houses)",
        )

    def handle(self, *args, **options):
        db_path = str(settings.RENT_DB_PATH)
        houses_only = options["houses_only"]
        flats_only = options["flats_only"]

        total_flats = 0
        total_houses = 0

        if not houses_only:
            self.stdout.write(f"Scraping rent flats into {db_path} ...")
            total_flats = run_scrape(db_path=db_path, progress=self.stdout.write)

        if not flats_only:
            self.stdout.write(f"Scraping Tavush houses into {db_path} ...")
            total_houses = run_house_scrape(
                db_path=db_path, progress=self.stdout.write
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Flats={total_flats}, houses={total_houses}."
            )
        )
