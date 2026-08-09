"""Background daily scrape of list.am into real_estate.db."""

import logging
import sys
import threading

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from django.conf import settings

logger = logging.getLogger(__name__)

_scheduler = None
_scheduler_lock = threading.Lock()
_scrape_lock = threading.Lock()


def _progress(msg):
    """Write scrape progress to stdout (visible in the runserver console)."""
    text = str(msg).rstrip()
    if not text:
        return
    print(text, flush=True)
    logger.info("%s", text)


def _execute_scrape():
    from scraper import run_scrape

    print("Starting list.am scrape...", flush=True)
    try:
        run_scrape(db_path=str(settings.RENT_DB_PATH), progress=_progress)
        print("Scrape finished.", flush=True)
    except Exception:
        logger.exception("Scrape failed")
        print("Scrape failed.", file=sys.stderr, flush=True)
        raise


def _run_scheduled_scrape():
    if not _scrape_lock.acquire(blocking=False):
        logger.warning("Scrape already running; skipping scheduled run")
        return
    try:
        _execute_scrape()
    except Exception:
        pass
    finally:
        _scrape_lock.release()


def is_scrape_running():
    return _scrape_lock.locked()


def start_scheduler():
    global _scheduler
    with _scheduler_lock:
        if _scheduler is not None:
            return

        _scheduler = BackgroundScheduler(timezone=settings.TIME_ZONE)
        _scheduler.add_job(
            _run_scheduled_scrape,
            trigger=CronTrigger(
                day_of_week=settings.SCRAPE_CRON_DAY_OF_WEEK,
                hour=settings.SCRAPE_CRON_HOUR,
                minute=settings.SCRAPE_CRON_MINUTE,
                timezone=settings.TIME_ZONE,
            ),
            id="weekly_listam_scrape",
            replace_existing=True,
            max_instances=1,
        )
        _scheduler.start()
        msg = (
            f"Scrape scheduler started "
            f"(weekly on {settings.SCRAPE_CRON_DAY_OF_WEEK} at "
            f"{settings.SCRAPE_CRON_HOUR:02d}:{settings.SCRAPE_CRON_MINUTE:02d} "
            f"{settings.TIME_ZONE})"
        )
        print(msg, flush=True)
        logger.info("%s", msg)
