"""Background daily scrape of list.am into real_estate.db."""

import logging
import threading

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from django.conf import settings

logger = logging.getLogger(__name__)

_scheduler = None
_scheduler_lock = threading.Lock()
_scrape_lock = threading.Lock()


def _run_scheduled_scrape():
    if not _scrape_lock.acquire(blocking=False):
        logger.warning("Scrape already running; skipping scheduled run")
        return
    try:
        from scraper import run_scrape

        logger.info("Starting scheduled list.am scrape")
        run_scrape(
            db_path=str(settings.RENT_DB_PATH),
            progress=lambda msg: logger.info("%s", msg),
        )
        logger.info("Scheduled scrape finished")
    except Exception:
        logger.exception("Scheduled scrape failed")
    finally:
        _scrape_lock.release()


def start_scrape_in_background():
    """Start a scrape in a daemon thread (for manual trigger from the UI)."""
    if not _scrape_lock.acquire(blocking=False):
        return False

    def _target():
        try:
            from scraper import run_scrape

            run_scrape(
                db_path=str(settings.RENT_DB_PATH),
                progress=lambda msg: logger.info("%s", msg),
            )
        except Exception:
            logger.exception("Manual scrape failed")
        finally:
            _scrape_lock.release()

    threading.Thread(target=_target, daemon=True, name="listam-scrape").start()
    return True


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
                hour=settings.SCRAPE_CRON_HOUR,
                minute=settings.SCRAPE_CRON_MINUTE,
                timezone=settings.TIME_ZONE,
            ),
            id="daily_listam_scrape",
            replace_existing=True,
            max_instances=1,
        )
        _scheduler.start()
        logger.info(
            "Scrape scheduler started (daily at %02d:%02d %s)",
            settings.SCRAPE_CRON_HOUR,
            settings.SCRAPE_CRON_MINUTE,
            settings.TIME_ZONE,
        )
