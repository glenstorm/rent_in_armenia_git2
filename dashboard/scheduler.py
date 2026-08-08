"""Background daily scrape of list.am into real_estate.db."""

import logging
import threading

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from django.conf import settings

from dashboard import scrape_progress

logger = logging.getLogger(__name__)

_scheduler = None
_scheduler_lock = threading.Lock()
_scrape_lock = threading.Lock()


def _progress(msg):
    scrape_progress.append(msg)
    logger.info("%s", msg)


def _execute_scrape():
    from scraper import run_scrape

    scrape_progress.clear_and_start()
    try:
        run_scrape(db_path=str(settings.RENT_DB_PATH), progress=_progress)
        scrape_progress.finish()
    except Exception as exc:
        logger.exception("Scrape failed")
        scrape_progress.finish(error=exc)
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


def start_scrape_in_background():
    """Start a scrape in a daemon thread (for manual trigger from the UI)."""
    if not _scrape_lock.acquire(blocking=False):
        return False

    def _target():
        try:
            _execute_scrape()
        except Exception:
            pass
        finally:
            _scrape_lock.release()

    threading.Thread(target=_target, daemon=True, name="listam-scrape").start()
    return True


def is_scrape_running():
    return _scrape_lock.locked() or scrape_progress.snapshot()["running"]


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
