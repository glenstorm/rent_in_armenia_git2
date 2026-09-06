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

    def add_arguments(self, parser):
        parser.add_argument(
            "--prune-inactive-only",
            action="store_true",
            help="Only remove HOUSES whose list.am pages are gone (HTTP check; no scrape)",
        )
        parser.add_argument(
            "--prune-inactive",
            action="store_true",
            help="After scraping, also HTTP-check every stored house page",
        )

    def handle(self, *args, **options):
        db_path = str(settings.RENT_DB_PATH)
        prune_only = options["prune_inactive_only"]
        prune_inactive = options["prune_inactive"] or prune_only

        if prune_only:
            self.stdout.write(f"Pruning inactive Tavush houses in {db_path} ...")
        else:
            self.stdout.write(f"Scraping Tavush houses into {db_path} ...")

        total = run_house_scrape(
            db_path=db_path,
            progress=self.stdout.write,
            prune_inactive=prune_inactive,
            prune_only=prune_only,
        )
        if prune_only:
            self.stdout.write(self.style.SUCCESS("Done pruning inactive houses."))
        else:
            self.stdout.write(self.style.SUCCESS(f"Done. Processed {total} houses."))
