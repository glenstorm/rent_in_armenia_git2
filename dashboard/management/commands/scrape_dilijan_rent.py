"""Scrape Dilijan long-term apartment and house rents into DILIJAN_RENT."""

from django.conf import settings
from django.core.management.base import BaseCommand

from dilijan_rent_scraper import run_dilijan_rent_scrape


class Command(BaseCommand):
    help = (
        "Scrape list.am Dilijan long-term rents "
        "(apartments category 56, houses category 1377; n=58) "
        "into DILIJAN_RENT"
    )

    def handle(self, *args, **options):
        db_path = str(settings.RENT_DB_PATH)
        self.stdout.write(f"Scraping Dilijan rent into {db_path} ...")
        total = run_dilijan_rent_scrape(
            db_path=db_path, progress=self.stdout.write
        )
        self.stdout.write(
            self.style.SUCCESS(f"Done. Processed {total} Dilijan rent listings.")
        )
