"""Plotly charts for Tavush house-sale listings (Dilijan, Ijevan, Haghartsin, Hovk)."""

import sqlite3

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from city import all_house_region_map

HOUSE_LARGE_ROOM_GROUP = "8+"
HOUSE_TREND_ROOM_GROUPS = [2, 3, 4, 5, 6, 7, HOUSE_LARGE_ROOM_GROUP]
HOUSE_BUDGET_MAX_AMD = 30_000_000
HOUSE_PLOT_COLORS = [
    ("#0f6e56", "rgba(15, 110, 86, 0.35)"),
    ("#1f4e79", "rgba(31, 78, 121, 0.35)"),
    ("#8a4b08", "rgba(138, 75, 8, 0.35)"),
    ("#6c3483", "rgba(108, 52, 131, 0.35)"),
    ("#922b21", "rgba(146, 43, 33, 0.35)"),
    ("#1a5653", "rgba(26, 86, 83, 0.35)"),
    ("#5d4e37", "rgba(93, 78, 55, 0.35)"),
]


def tavush_location_names():
    return list(all_house_region_map().values())


def dilijan_location_names():
    """Backward-compatible alias."""
    return tavush_location_names()


def _house_room_group(room_num):
    try:
        n = int(room_num)
    except (TypeError, ValueError):
        return None
    if n >= 8:
        return HOUSE_LARGE_ROOM_GROUP
    return n


def _normalize_locations(location_names):
    if location_names is None:
        return tavush_location_names()
    if isinstance(location_names, str):
        return [location_names]
    return list(location_names)


def load_houses(db_path, location_names=None):
    names = _normalize_locations(location_names)
    if not names:
        return pd.DataFrame()
    placeholders = ",".join("?" * len(names))
    try:
        with sqlite3.connect(db_path) as connection:
            return pd.read_sql_query(
                f"""
                SELECT h.*, g.region_name
                FROM HOUSES h
                JOIN REGION g ON g.id = h.region_id
                WHERE g.region_name IN ({placeholders})
                """,
                connection,
                params=tuple(names),
            )
    except sqlite3.Error:
        return pd.DataFrame()


def house_listing_stats(db_path, location_names=None):
    names = _normalize_locations(location_names)
    df = load_houses(db_path, names)
    if df.empty:
        return {"count": 0, "by_rooms": [], "by_town": []}

    df = df.copy()
    df["room_group"] = df["room_num"].map(_house_room_group)
    df = df.dropna(subset=["room_group"])

    by_rooms = (
        df.groupby("room_group", dropna=False)
        .size()
        .reset_index(name="count")
        .sort_values(
            "room_group",
            key=lambda s: s.map(
                lambda g: 99 if g == HOUSE_LARGE_ROOM_GROUP else int(g)
            ),
        )
    )
    town_order = {name: idx for idx, name in enumerate(names)}
    by_town = (
        df.groupby("region_name", dropna=False)
        .size()
        .reset_index(name="count")
        .sort_values(
            "region_name",
            key=lambda s: s.map(lambda n: town_order.get(n, 999)),
        )
    )
    return {
        "count": int(len(df)),
        "by_rooms": [
            {"rooms": str(row.room_group), "count": int(row.count)}
            for row in by_rooms.itertuples(index=False)
        ],
        "by_town": [
            {"name": row.region_name, "count": int(row.count)}
            for row in by_town.itertuples(index=False)
        ],
    }


def build_house_town_box_figure(db_path, y="price", location_names=None):
    """Box plot comparing house sale prices across Tavush towns."""
    if y not in ("price", "price_per_square"):
        y = "price"
    names = _normalize_locations(location_names)
    df = load_houses(db_path, names)
    fig = go.Figure()
    y_label = "price (AMD)" if y == "price" else "price per m² (AMD)"

    if df.empty:
        fig.update_layout(
            title="Tavush: no house listings yet",
            width=1200,
            height=520,
        )
        return fig

    df = df.copy()
    df = df.dropna(subset=[y])
    if y == "price_per_square":
        df = df[df[y].notna() & (df[y] > 0)]
    if df.empty:
        fig.update_layout(title=f"Tavush: no data for {y}", width=1200, height=520)
        return fig

    counts = df.groupby("region_name").size().to_dict()
    ticktext = [f"{name} ({counts.get(name, 0)})" for name in names]

    for idx, name in enumerate(names):
        vals = df.loc[df["region_name"] == name, y].tolist()
        line_color, fill_color = HOUSE_PLOT_COLORS[idx % len(HOUSE_PLOT_COLORS)]
        has_data = bool(vals)
        fig.add_trace(
            go.Box(
                x=[name] * len(vals) if has_data else [name],
                y=vals if has_data else [None],
                name=name,
                showlegend=False,
                boxpoints=False,
                width=0.55,
                line=dict(
                    width=1 if has_data else 0,
                    color=line_color if has_data else "rgba(0,0,0,0)",
                ),
                fillcolor=fill_color if has_data else "rgba(0,0,0,0)",
                whiskerwidth=0.6 if has_data else 0,
                opacity=1 if has_data else 0,
            )
        )

    fig.update_layout(
        title=f"Tavush houses for sale — price by town ({len(df)} listings)",
        width=1200,
        height=560,
        margin=dict(t=70, b=80, l=70, r=30),
        boxgap=0.15,
    )
    fig.update_xaxes(
        title_text="town",
        type="category",
        categoryorder="array",
        categoryarray=names,
        tickmode="array",
        tickvals=names,
        ticktext=ticktext,
        automargin=True,
    )
    fig.update_yaxes(title_text=y_label, automargin=True)
    return fig


def build_dilijan_house_box_figure(db_path, y="price", location_name="Dilijan"):
    """Backward-compatible single-town room box plot."""
    return build_house_room_box_figure(
        db_path, y=y, location_names=[location_name]
    )


def build_house_room_box_figure(db_path, y="price", location_names=None):
    """Box plot comparing prices across room groups (one or more towns)."""
    if y not in ("price", "price_per_square"):
        y = "price"
    names = _normalize_locations(location_names)
    df = load_houses(db_path, names)
    fig = go.Figure()
    label = ", ".join(names) if len(names) <= 2 else "Tavush"
    y_label = "price (AMD)" if y == "price" else "price per m² (AMD)"

    if df.empty:
        fig.update_layout(
            title=f"{label}: no house listings yet",
            width=1200,
            height=520,
        )
        return fig

    df = df.copy()
    df["room_group"] = df["room_num"].map(_house_room_group)
    df = df.dropna(subset=["room_group", y])
    if y == "price_per_square":
        df = df[df[y].notna() & (df[y] > 0)]
    if df.empty:
        fig.update_layout(title=f"{label}: no data for {y}", width=1200, height=520)
        return fig

    numeric = sorted(g for g in df["room_group"].unique() if isinstance(g, int))
    room_order = numeric + (
        [HOUSE_LARGE_ROOM_GROUP]
        if HOUSE_LARGE_ROOM_GROUP in set(df["room_group"])
        else []
    )
    counts = df.groupby("room_group").size().to_dict()
    ticktext = [
        f"{g} ({counts.get(g, 0)})"
        if g != HOUSE_LARGE_ROOM_GROUP
        else f"8+ ({counts.get(g, 0)})"
        for g in room_order
    ]

    for idx, room_group in enumerate(room_order):
        vals = df.loc[df["room_group"] == room_group, y].tolist()
        line_color, fill_color = HOUSE_PLOT_COLORS[idx % len(HOUSE_PLOT_COLORS)]
        fig.add_trace(
            go.Box(
                x=[str(room_group)] * len(vals),
                y=vals,
                name=str(room_group),
                showlegend=False,
                boxpoints=False,
                width=0.55,
                line=dict(width=1, color=line_color),
                fillcolor=fill_color,
                whiskerwidth=0.6,
            )
        )

    fig.update_layout(
        title=f"{label} houses — price by rooms ({len(df)} listings)",
        width=1200,
        height=560,
        margin=dict(t=70, b=80, l=70, r=30),
        boxgap=0.15,
    )
    fig.update_xaxes(
        title_text="rooms",
        type="category",
        categoryorder="array",
        categoryarray=[str(g) for g in room_order],
        tickmode="array",
        tickvals=[str(g) for g in room_order],
        ticktext=ticktext,
        automargin=True,
    )
    fig.update_yaxes(title_text=y_label, automargin=True)
    return fig


def build_dilijan_house_trend_figure(
    db_path, y="price", location_name="Dilijan", room_group=None
):
    return build_house_trend_figure(
        db_path,
        y=y,
        location_names=[location_name] if location_name else None,
        room_group=room_group,
    )


def build_house_trend_figure(
    db_path, y="price", location_names=None, room_group=None
):
    """Trend chart for house prices across one or more Tavush towns."""
    if y not in ("price", "price_per_square"):
        y = "price"
    y_label = "price (AMD)" if y == "price" else "price per m² (AMD)"
    names = _normalize_locations(location_names)
    placeholders = ",".join("?" * len(names))

    try:
        with sqlite3.connect(db_path) as connection:
            hist = pd.read_sql_query(
                f"""
                SELECT h.price, h.price_per_square, h.scraped_at, hs.room_num
                FROM HOUSE_PRICE_HISTORY h
                JOIN HOUSES hs ON hs.id = h.listing_id
                JOIN REGION g ON g.id = hs.region_id
                WHERE g.region_name IN ({placeholders})
                """,
                connection,
                params=tuple(names),
            )
    except sqlite3.Error:
        hist = pd.DataFrame()

    room_groups = [room_group] if room_group is not None else list(HOUSE_TREND_ROOM_GROUPS)
    n_rows = len(room_groups)
    scope = ", ".join(names) if len(names) <= 2 else "Tavush"
    fig = make_subplots(
        rows=n_rows,
        cols=1,
        shared_xaxes=False,
        subplot_titles=[
            f"rooms: {g}" if g != HOUSE_LARGE_ROOM_GROUP else "rooms: 8+"
            for g in room_groups
        ],
        vertical_spacing=min(0.06, 0.5 / max(n_rows - 1, 1)) if n_rows > 1 else 0.08,
    )

    if hist.empty:
        fig.update_layout(
            title=f"{scope}: no house price history yet",
            width=1200,
            height=360 if n_rows == 1 else 320 * n_rows,
        )
        return fig

    hist = hist.copy()
    hist["room_group"] = hist["room_num"].map(_house_room_group)
    hist["scrape_day"] = pd.to_datetime(hist["scraped_at"], utc=True, errors="coerce")
    hist = hist.dropna(subset=["scrape_day", "room_group", y])
    if y == "price_per_square":
        hist = hist[hist[y].notna() & (hist[y] > 0)]
    hist["scrape_day"] = hist["scrape_day"].dt.tz_convert(None).dt.normalize()

    series = [
        ("min", "#922b21", "dash"),
        ("q1", "#8a4b08", "dot"),
        ("median", "#0f6e56", "solid"),
        ("q3", "#1f4e79", "dot"),
        ("max", "#6c3483", "dash"),
    ]

    for row_idx, group in enumerate(room_groups):
        row = row_idx + 1
        sub = hist[hist["room_group"] == group]
        show_legend = row_idx == 0
        if sub.empty:
            fig.update_xaxes(title_text="time", row=row, col=1)
            fig.update_yaxes(title_text=y_label, row=row, col=1)
            continue

        stats = (
            sub.groupby("scrape_day", as_index=False)[y]
            .agg(
                min="min",
                q1=lambda s: float(s.quantile(0.25)),
                median="median",
                q3=lambda s: float(s.quantile(0.75)),
                max="max",
            )
            .sort_values("scrape_day")
        )
        total = len(sub)
        fig.layout.annotations[row_idx].text = (
            f"rooms: {group} ({total} history points)"
            if group != HOUSE_LARGE_ROOM_GROUP
            else f"rooms: 8+ ({total} history points)"
        )
        fig.add_trace(
            go.Scatter(
                x=list(stats["scrape_day"]) + list(stats["scrape_day"][::-1]),
                y=list(stats["q3"]) + list(stats["q1"][::-1]),
                fill="toself",
                fillcolor="rgba(15, 110, 86, 0.12)",
                line=dict(width=0),
                name="IQR (Q1–Q3)",
                hoverinfo="skip",
                showlegend=show_legend,
                legendgroup="iqr",
            ),
            row=row,
            col=1,
        )
        for col, color, dash in series:
            label = col.upper() if col in ("q1", "q3") else col.capitalize()
            fig.add_trace(
                go.Scatter(
                    x=stats["scrape_day"],
                    y=stats[col],
                    mode="lines+markers",
                    name=label,
                    legendgroup=col,
                    showlegend=show_legend,
                    line=dict(
                        color=color,
                        width=2 if col == "median" else 1.5,
                        dash=dash,
                    ),
                    marker=dict(size=7),
                ),
                row=row,
                col=1,
            )
        fig.update_xaxes(title_text="time", showgrid=True, row=row, col=1)
        fig.update_yaxes(
            title_text=y_label, showgrid=True, automargin=True, row=row, col=1
        )

    title = (
        f"{scope} houses: rooms {room_group} trend"
        if room_group is not None
        else f"{scope} houses: price trends by room count"
    )
    fig.update_layout(
        title=title,
        width=1200,
        height=420 if n_rows == 1 else 360 * n_rows,
        margin=dict(t=70, b=80 if n_rows == 1 else 100, l=70, r=30),
        legend=dict(
            orientation="h",
            yanchor="bottom" if n_rows == 1 else "top",
            y=1.02 if n_rows == 1 else -0.02,
            x=0,
            xanchor="left",
        ),
        hovermode="x unified",
    )
    return fig


def _listing_dict(row):
    square = (
        int(row.square)
        if getattr(row, "square", None) is not None and not pd.isna(row.square)
        else None
    )
    ppm2 = (
        float(row.price_per_square)
        if getattr(row, "price_per_square", None) is not None
        and not pd.isna(row.price_per_square)
        else None
    )
    return {
        "town": row.region_name,
        "price": int(row.price),
        "price_display": f"{int(row.price):,}".replace(",", " "),
        "rooms": int(row.room_num),
        "square": square,
        "ppm2": ppm2,
        "ppm2_display": (
            f"{int(round(ppm2)):,}".replace(",", " ") if ppm2 is not None else "—"
        ),
        "address": row.address,
        "link": row.link,
    }


def list_budget_houses_by_rooms(
    db_path,
    location_names=None,
    max_price_amd=HOUSE_BUDGET_MAX_AMD,
    room_groups=None,
    location_name=None,
):
    """Houses under max_price_amd, grouped by room tabs."""
    if location_name is not None and location_names is None:
        location_names = [location_name]
    if room_groups is None:
        room_groups = list(HOUSE_TREND_ROOM_GROUPS)

    df = load_houses(db_path, location_names)
    sections = []
    if df.empty:
        for group in room_groups:
            sections.append(
                {
                    "rooms": str(group),
                    "rooms_label": (
                        "8+" if group == HOUSE_LARGE_ROOM_GROUP else str(group)
                    ),
                    "room_group": group,
                    "listings": [],
                }
            )
        return sections

    df = df.copy()
    df["room_group"] = df["room_num"].map(_house_room_group)
    df = df.dropna(subset=["room_group"])
    df = df[df["price"] < int(max_price_amd)]
    df = df.sort_values(["price", "room_num"], ascending=[True, True])

    for group in room_groups:
        sub = df[df["room_group"] == group]
        sections.append(
            {
                "rooms": str(group),
                "rooms_label": (
                    "8+" if group == HOUSE_LARGE_ROOM_GROUP else str(group)
                ),
                "room_group": group,
                "listings": [_listing_dict(row) for row in sub.itertuples(index=False)],
            }
        )
    return sections


def rank_best_buys(
    db_path,
    location_names=None,
    max_price_amd=HOUSE_BUDGET_MAX_AMD,
    limit=25,
    require_square=True,
):
    """
    Rank Tavush houses under max_price_amd.
    Prefer lowest AMD/m² when square is known; otherwise sort by price.
    """
    df = load_houses(db_path, location_names)
    if df.empty:
        return []

    df = df.copy()
    df = df[df["price"] < int(max_price_amd)]
    if require_square:
        df = df[df["square"].notna() & (df["square"] > 0)]
        df = df[df["price_per_square"].notna() & (df["price_per_square"] > 0)]
        df = df.sort_values(
            ["price_per_square", "price", "square"],
            ascending=[True, True, False],
        )
    else:
        df = df.sort_values(["price", "room_num"], ascending=[True, True])

    if limit:
        df = df.head(int(limit))
    return [_listing_dict(row) for row in df.itertuples(index=False)]
