import secrets
import sqlite3
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import redirect, render

from charts import (
    build_district_trend_figure,
    build_rent_box_figure,
    list_districts_with_data,
    list_room_groups,
    parse_room_group,
)
from dilijan_rent_charts import (
    PROPERTY_APARTMENT,
    PROPERTY_HOUSE,
    build_dilijan_rent_room_box_figure,
    build_dilijan_rent_type_box_figure,
    dilijan_rent_stats,
    list_dilijan_rent_budget,
)
from dilijan_rent_store import dedupe_dilijan_rent_links, ensure_dilijan_rent_schema
from house_charts import (
    HOUSE_BUDGET_MAX_AMD,
    HOUSE_LARGE_ROOM_GROUP,
    HOUSE_TREND_ROOM_GROUPS,
    build_house_room_box_figure,
    build_house_town_box_figure,
    build_house_trend_figure,
    house_listing_stats,
    list_budget_houses_by_rooms,
    rank_best_buys,
    tavush_location_names,
)
from house_store import dedupe_house_links, ensure_houses_schema
from dashboard.bot_gate import (
    captcha_code,
    check_answer,
    is_locked,
    is_verified,
    issue_captcha,
    render_captcha_svg,
    safe_next_url,
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


def bot_verify(request):
    next_url = safe_next_url(
        request, request.POST.get("next") or request.GET.get("next")
    )
    if is_verified(request):
        return redirect(next_url)

    error = ""
    if request.method == "POST":
        ok, error = check_answer(
            request,
            answer=request.POST.get("captcha", ""),
            honeypot=request.POST.get("company_url", ""),
        )
        if ok:
            return redirect(next_url)
    elif captcha_code(request) is None:
        issue_captcha(request)

    return render(
        request,
        "dashboard/verify.html",
        {
            "nav": None,
            "hide_nav": True,
            "next_url": next_url,
            "error": error,
            "locked": is_locked(request),
            "captcha_nonce": secrets.token_hex(4),
        },
    )


def bot_captcha_image(request):
    code = captcha_code(request) or issue_captcha(request)
    response = HttpResponse(render_captcha_svg(code), content_type="image/svg+xml")
    response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response


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


def tavush_houses(request):
    y = _parse_y(request)
    db_path = str(settings.RENT_DB_PATH)
    with sqlite3.connect(db_path) as connection:
        ensure_houses_schema(connection)
        dedupe_house_links(connection)
    towns = tavush_location_names()
    selected_town = request.GET.get("town") or "all"
    if selected_town != "all" and selected_town not in towns:
        selected_town = "all"
    location_names = towns if selected_town == "all" else [selected_town]

    house_stats = house_listing_stats(db_path, location_names)
    budget_max = HOUSE_BUDGET_MAX_AMD
    town_box_html = ""
    room_box_html = ""
    trend_sections = []
    best_buys = []

    if house_stats["count"]:
        town_fig = build_house_town_box_figure(
            db_path, y=y, location_names=location_names
        )
        room_fig = build_house_room_box_figure(
            db_path, y=y, location_names=location_names
        )
        town_box_html = town_fig.to_html(full_html=False, include_plotlyjs="cdn")
        room_box_html = room_fig.to_html(full_html=False, include_plotlyjs=False)

        best_buys = rank_best_buys(
            db_path,
            location_names=location_names,
            max_price_amd=budget_max,
            limit=25,
        )

        budget_by_rooms = {
            section["room_group"]: section
            for section in list_budget_houses_by_rooms(
                db_path,
                location_names=location_names,
                max_price_amd=budget_max,
            )
        }
        for room_group in HOUSE_TREND_ROOM_GROUPS:
            trend_fig = build_house_trend_figure(
                db_path,
                y=y,
                location_names=location_names,
                room_group=room_group,
            )
            trend_html = trend_fig.to_html(full_html=False, include_plotlyjs=False)
            budget = budget_by_rooms.get(room_group, {})
            trend_sections.append(
                {
                    "rooms_label": (
                        "8+"
                        if room_group == HOUSE_LARGE_ROOM_GROUP
                        else str(room_group)
                    ),
                    "trend_html": trend_html,
                    "listings": budget.get("listings", []),
                }
            )

    return render(
        request,
        "dashboard/tavush_houses.html",
        {
            "nav": "tavush_houses",
            "y": y,
            "towns": towns,
            "selected_town": selected_town,
            "house_stats": house_stats,
            "town_box_html": town_box_html,
            "room_box_html": room_box_html,
            "best_buys": best_buys,
            "trend_sections": trend_sections,
            "budget_max": budget_max,
            "budget_max_display": f"{budget_max:,}".replace(",", " "),
            **_schedule_context(),
        },
    )


def dilijan_houses(request):
    """Old URL — redirect to Tavush houses page."""
    return redirect("tavush_houses")


def dilijan_rent(request):
    y = _parse_y(request)
    db_path = str(settings.RENT_DB_PATH)
    with sqlite3.connect(db_path) as connection:
        ensure_dilijan_rent_schema(connection)
        dedupe_dilijan_rent_links(connection)

    selected_type = request.GET.get("type") or "all"
    if selected_type not in ("all", PROPERTY_APARTMENT, PROPERTY_HOUSE):
        selected_type = "all"
    property_types = (
        None
        if selected_type == "all"
        else [selected_type]
    )

    rent_stats = dilijan_rent_stats(db_path, property_types)
    budget_max = 400_000
    type_box_html = ""
    room_box_html = ""
    budget_listings = []

    if rent_stats["count"]:
        type_fig = build_dilijan_rent_type_box_figure(
            db_path, y=y, property_types=property_types
        )
        room_fig = build_dilijan_rent_room_box_figure(
            db_path, y=y, property_types=property_types
        )
        type_box_html = type_fig.to_html(full_html=False, include_plotlyjs="cdn")
        room_box_html = room_fig.to_html(full_html=False, include_plotlyjs=False)
        budget_listings = list_dilijan_rent_budget(
            db_path,
            property_types=property_types,
            max_price_amd=budget_max,
            limit=40,
        )

    return render(
        request,
        "dashboard/dilijan_rent.html",
        {
            "nav": "dilijan_rent",
            "y": y,
            "selected_type": selected_type,
            "rent_stats": rent_stats,
            "type_box_html": type_box_html,
            "room_box_html": room_box_html,
            "budget_listings": budget_listings,
            "budget_max": budget_max,
            "budget_max_display": f"{budget_max:,}".replace(",", " "),
            **_schedule_context(),
        },
    )
