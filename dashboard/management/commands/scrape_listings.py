"""Run the list.am scrape into real_estate.db (same work as main.py)."""

from django.conf import settings
from django.core.management.base import BaseCommand

from scraper import run_scrape


class Command(BaseCommand):
    help = "Scrape list.am rent listings into real_estate.db"

    def handle(self, *args, **options):
        db_path = str(settings.RENT_DB_PATH)
        self.stdout.write(f"Scraping into {db_path} ...")
        total = run_scrape(db_path=db_path, progress=self.stdout.write)
        self.stdout.write(self.style.SUCCESS(f"Done. Processed {total} listings."))
