from django.apps import AppConfig


class DashboardConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "dashboard"

    def ready(self):
        import os
        import sys

        from django.conf import settings

        if not getattr(settings, "ENABLE_SCRAPE_SCHEDULER", True):
            return

        # Only while serving; skip migrate/shell/setup/etc.
        if len(sys.argv) < 2 or sys.argv[1] != "runserver":
            return

        # Skip Django autoreloader parent process
        if os.environ.get("RUN_MAIN") != "true":
            return

        from dashboard.scheduler import start_scheduler

        start_scheduler()
