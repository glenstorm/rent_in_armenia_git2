import sqlite3
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from charts import build_rent_box_figure
from dashboard.scheduler import is_scrape_running, start_scrape_in_background


def _listing_stats(db_path):
    path = Path(db_path)
    if not path.exists():
        return {"count": 0, "latest_date": None, "regions": 0}

    with sqlite3.connect(path) as connection:
        cur = connection.cursor()
        try:
            count = cur.execute("SELECT COUNT(*) FROM REAL_ESTATE").fetchone()[0]
            latest = cur.execute("SELECT MAX(ddate) FROM REAL_ESTATE").fetchone()[0]
            regions = cur.execute(
                "SELECT COUNT(DISTINCT region_id) FROM REAL_ESTATE"
            ).fetchone()[0]
        except sqlite3.Error:
            return {"count": 0, "latest_date": None, "regions": 0}

    return {"count": count, "latest_date": latest, "regions": regions}


def home(request):
    y = request.GET.get("y", "price")
    if y not in ("price", "price_per_square"):
        y = "price"

    db_path = settings.RENT_DB_PATH
    stats = _listing_stats(db_path)
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
            "scrape_hour": settings.SCRAPE_CRON_HOUR,
            "scrape_minute": settings.SCRAPE_CRON_MINUTE,
            "timezone": settings.TIME_ZONE,
        },
    )


@require_POST
def scrape_now(request):
    if start_scrape_in_background():
        messages.info(request, "Scrape started in the background. Refresh later to see new data.")
    else:
        messages.warning(request, "A scrape is already running.")
    return redirect("home")
