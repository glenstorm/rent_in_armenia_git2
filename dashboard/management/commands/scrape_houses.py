"""Scrape Tavush house-sale listings into real_estate.db (HOUSES table)."""

from django.conf import settings
from django.core.management.base import BaseCommand

from house_scraper import run_house_scrape


class Command(BaseCommand):
    help = (
        "Scrape list.am Tavush house sales "
        "(Dilijan, Ijevan, Haghartsin, Hovk; category 1386) "
        "into HOUSES"
    )

    def handle(self, *args, **options):
        db_path = str(settings.RENT_DB_PATH)
        self.stdout.write(f"Scraping Tavush houses into {db_path} ...")
        total = run_house_scrape(db_path=db_path, progress=self.stdout.write)
        self.stdout.write(self.style.SUCCESS(f"Done. Processed {total} houses."))
