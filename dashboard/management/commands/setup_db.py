"""Initialize rent SQLite DB the same way as init_db.py (safe if already set up)."""

import sqlite3
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from init_db import init_db


class Command(BaseCommand):
    help = "Create real_estate.db schema and seed REGION rows (like init_db.py)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Drop and recreate rent tables (DESTROYS existing listing data)",
        )

    def handle(self, *args, **options):
        db_path = Path(settings.RENT_DB_PATH)
        schema_path = Path(settings.RENT_SCHEMA_PATH)

        if not schema_path.exists():
            self.stderr.write(self.style.ERROR(f"Schema not found: {schema_path}"))
            return

        if db_path.exists() and not options["force"]:
            with sqlite3.connect(db_path) as connection:
                cur = connection.cursor()
                try:
                    row = cur.execute("SELECT COUNT(*) FROM REGION").fetchone()
                except sqlite3.Error:
                    row = (0,)
            if row and row[0] > 0:
                self.stdout.write(
                    self.style.WARNING(
                        f"Rent DB already initialized at {db_path} "
                        "(use --force to recreate)."
                    )
                )
                return

        init_db(db_path=str(db_path), schema_path=str(schema_path))
        self.stdout.write(self.style.SUCCESS(f"Initialized rent DB at {db_path}"))
