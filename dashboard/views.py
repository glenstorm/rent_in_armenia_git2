import sqlite3
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from django.conf import settings
from django.shortcuts import render

from charts import (
    build_district_trend_figure,
    build_rent_box_figure,
    list_districts_with_data,
    list_room_groups,
    parse_room_group,
)
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


def _parse_y(request):
    y = request.GET.get("y", "price")
    if y not in ("price", "price_per_square"):
        return "price"
    return y


def _listing_stats(db_path):
    empty = {"count": 0, "latest_scrape": None, "by_district": []}
    path = Path(db_path)
    if not path.exists():
        return empty

    with sqlite3.connect(path) as connection:
        cur = connection.cursor()
        try:
            count = cur.execute(
                """
                SELECT COUNT(*)
                FROM REAL_ESTATE r
                JOIN REGION g ON g.id = r.region_id
                WHERE g.region_name != 'Yerevan'
                """
            ).fetchone()[0]
            by_district = cur.execute(
                """
                SELECT g.region_name, COUNT(r.id) AS listing_count
                FROM REAL_ESTATE r
                JOIN REGION g ON g.id = r.region_id
                WHERE g.region_name != 'Yerevan'
                GROUP BY g.id, g.region_name
                HAVING COUNT(r.id) > 0
                ORDER BY g.id
                """
            ).fetchall()
            latest_raw = latest_scrape_finished_at(connection)
        except sqlite3.Error:
            return empty

    latest_scrape = None
    dt = _parse_iso(latest_raw)
    if dt is not None:
        latest_scrape = dt.astimezone(ZoneInfo(settings.TIME_ZONE)).strftime(
            "%Y-%m-%d %H:%M:%S %Z"
        )

    return {
        "count": count,
        "latest_scrape": latest_scrape,
        "by_district": [
            {"name": name, "count": listing_count} for name, listing_count in by_district
        ],
    }


def _schedule_context():
    return {
        "scrape_day": settings.SCRAPE_CRON_DAY_OF_WEEK,
        "scrape_hour": settings.SCRAPE_CRON_HOUR,
        "scrape_minute": settings.SCRAPE_CRON_MINUTE,
        "timezone": settings.TIME_ZONE,
    }


def home(request):
    db_path = str(settings.RENT_DB_PATH)
    stats = _listing_stats(db_path)
    return render(
        request,
        "dashboard/home.html",
        {
            "nav": "home",
            "stats": stats,
            **_schedule_context(),
        },
    )


def trends(request):
    y = _parse_y(request)
    db_path = str(settings.RENT_DB_PATH)
    stats = _listing_stats(db_path)
    districts = list_districts_with_data(db_path) if stats["count"] else []

    district = request.GET.get("district") or (districts[0] if districts else None)
    if district and district not in districts:
        district = districts[0] if districts else None

    trend_html = ""
    if district:
        trend_fig = build_district_trend_figure(db_path, district, y=y)
        trend_html = trend_fig.to_html(full_html=False, include_plotlyjs="cdn")

    return render(
        request,
        "dashboard/trends.html",
        {
            "nav": "trends",
            "y": y,
            "districts": districts,
            "selected_district": district,
            "trend_html": trend_html,
            **_schedule_context(),
        },
    )


def distribution(request):
    y = _parse_y(request)
    db_path = str(settings.RENT_DB_PATH)
    stats = _listing_stats(db_path)
    room_tabs = list_room_groups(db_path) if stats["count"] else []

    room_param = request.GET.get("rooms") or (room_tabs[0] if room_tabs else None)
    if room_param and room_param not in room_tabs:
        room_param = room_tabs[0] if room_tabs else None
    room_group = parse_room_group(room_param)

    chart_html = ""
    if stats["count"]:
        fig = build_rent_box_figure(db_path, y=y, room_group=room_group)
        chart_html = fig.to_html(full_html=False, include_plotlyjs="cdn")

    return render(
        request,
        "dashboard/distribution.html",
        {
            "nav": "distribution",
            "y": y,
            "room_tabs": room_tabs,
            "selected_rooms": room_param,
            "chart_html": chart_html,
            **_schedule_context(),
        },
    )
