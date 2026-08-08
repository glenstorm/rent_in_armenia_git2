import sqlite3
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from charts import build_rent_box_figure
from dashboard import scrape_progress
from dashboard.scheduler import is_scrape_running, start_scrape_in_background
from scrape_meta import latest_scrape_finished_at


def _parse_iso(raw):
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    return dt


def _listing_stats(db_path, progress_finished_at=None):
    path = Path(db_path)
    if not path.exists():
        return {"count": 0, "latest_scrape": None, "regions": 0}

    with sqlite3.connect(path) as connection:
        cur = connection.cursor()
        try:
            count = cur.execute("SELECT COUNT(*) FROM REAL_ESTATE").fetchone()[0]
            regions = cur.execute(
                "SELECT COUNT(DISTINCT region_id) FROM REAL_ESTATE"
            ).fetchone()[0]
            latest_raw = latest_scrape_finished_at(connection)
        except sqlite3.Error:
            return {"count": 0, "latest_scrape": None, "regions": 0}

    candidates = []
    for raw in (latest_raw, progress_finished_at):
        dt = _parse_iso(raw)
        if dt is not None:
            candidates.append(dt)

    latest_scrape = None
    if candidates:
        latest_scrape = max(candidates).astimezone(ZoneInfo(settings.TIME_ZONE)).strftime(
            "%Y-%m-%d %H:%M:%S %Z"
        )

    return {
        "count": count,
        "latest_scrape": latest_scrape,
        "regions": regions,
    }


def home(request):
    y = request.GET.get("y", "price")
    if y not in ("price", "price_per_square"):
        y = "price"

    db_path = settings.RENT_DB_PATH
    progress = scrape_progress.snapshot()
    stats = _listing_stats(db_path, progress_finished_at=progress.get("finished_at"))
    chart_html = ""
    if stats["count"]:
        fig = build_rent_box_figure(str(db_path), y=y)
        chart_html = fig.to_html(full_html=False, include_plotlyjs="cdn")

    return render(
        request,
        "dashboard/home.html",
        {
            "chart_html": chart_html,
            "y": y,
            "stats": stats,
            "scrape_running": is_scrape_running(),
            "progress_lines": progress["lines"],
            "scrape_hour": settings.SCRAPE_CRON_HOUR,
            "scrape_minute": settings.SCRAPE_CRON_MINUTE,
            "timezone": settings.TIME_ZONE,
        },
    )


def scrape_status(request):
    data = scrape_progress.snapshot()
    data["running"] = is_scrape_running()
    return JsonResponse(data)


@require_POST
def scrape_now(request):
    if start_scrape_in_background():
        messages.info(request, "Scrape started. Progress appears below.")
    else:
        messages.warning(request, "A scrape is already running.")
    return redirect("home")
