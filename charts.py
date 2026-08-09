"""Plotly chart builders for rent statistics."""

import sqlite3

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Distinct colors per room-group subplot (line, translucent fill)
PLOT_COLORS = [
    ("#0f6e56", "rgba(15, 110, 86, 0.35)"),    # 1-room teal
    ("#1f4e79", "rgba(31, 78, 121, 0.35)"),   # 2-room blue
    ("#8a4b08", "rgba(138, 75, 8, 0.35)"),    # 3-room brown
    ("#6c3483", "rgba(108, 52, 131, 0.35)"),  # 4-room purple
    ("#922b21", "rgba(146, 43, 33, 0.35)"),   # 5+ red
]

# 5+ room flats are shown together on one subplot
LARGE_ROOM_GROUP = "5+"


def _room_group(room_num):
    try:
        n = int(room_num)
    except (TypeError, ValueError):
        return None
    if n >= 5:
        return LARGE_ROOM_GROUP
    return n


def load_listings(db_path):
    with sqlite3.connect(db_path) as connection:
        listings = pd.read_sql_query(
            """
            SELECT r.*, g.region_name
            FROM REAL_ESTATE r
            LEFT JOIN REGION g ON g.id = r.region_id
            WHERE g.region_name IS NOT NULL
              AND g.region_name != 'Yerevan'
            """,
            connection,
        )
        # Only districts that currently have at least one listing
        districts = pd.read_sql_query(
            """
            SELECT g.id AS region_id, g.region_name
            FROM REGION g
            INNER JOIN REAL_ESTATE r ON r.region_id = g.id
            WHERE g.region_name != 'Yerevan'
            GROUP BY g.id, g.region_name
            HAVING COUNT(r.id) > 0
            ORDER BY g.id
            """,
            connection,
        )
    return listings, districts


def _prepare_listings_frame(db_path):
    df, districts = load_listings(db_path)
    if df.empty or districts.empty:
        return df, districts, []

    region_order = districts["region_name"].tolist()
    df = df.copy()
    df = df[df["region_name"].isin(region_order)]
    df["room_group"] = df["room_num"].map(_room_group)
    df = df.dropna(subset=["room_group"])

    numeric_groups = sorted(
        g for g in df["room_group"].unique() if isinstance(g, int)
    )
    room_groups = numeric_groups + (
        [LARGE_ROOM_GROUP] if LARGE_ROOM_GROUP in set(df["room_group"]) else []
    )
    return df, districts, room_groups


def list_room_groups(db_path):
    """Room-group tabs labels, e.g. ['1', '2', '3', '4', '5+']."""
    _, _, room_groups = _prepare_listings_frame(db_path)
    return [str(g) for g in room_groups]


def parse_room_group(value):
    if value is None:
        return None
    text = str(value).strip()
    if text == LARGE_ROOM_GROUP:
        return LARGE_ROOM_GROUP
    try:
        return int(text)
    except (TypeError, ValueError):
        return None


def build_rent_box_figure(db_path, y="price", room_group=None):
    """
    Box plot of districts for one room group (1, 2, 3, 4, or 5+).
    X-axis labels include flat counts per district for that room group.
    """
    if y not in ("price", "price_per_square"):
        y = "price"

    df, districts, room_groups = _prepare_listings_frame(db_path)
    if df.empty or districts.empty or not room_groups:
        fig = go.Figure()
        fig.update_layout(
            title="No listings yet — run a scrape first",
            width=1200,
            height=400,
        )
        return fig

    if room_group is None:
        room_group = room_groups[0]
    elif room_group not in room_groups:
        room_group = room_groups[0]

    region_order = districts["region_name"].tolist()
    counts = (
        df.groupby(["room_group", "region_name"], dropna=False)
        .size()
        .to_dict()
    )
    y_label = "price" if y == "price" else "price per m²"
    color_idx = room_groups.index(room_group)
    line_color, fill_color = PLOT_COLORS[color_idx % len(PLOT_COLORS)]

    sub = df[df["room_group"] == room_group]
    total = int(sum(counts.get((room_group, name), 0) for name in region_order))
    title_group = f"rooms: {room_group}" if room_group != LARGE_ROOM_GROUP else "rooms: 5+"
    ticktext = [
        f"{name} ({counts.get((room_group, name), 0)})" for name in region_order
    ]

    fig = go.Figure()
    for name in region_order:
        vals = sub.loc[sub["region_name"] == name, y].tolist()
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
        title=f"{title_group} ({total} flats)",
        width=1200,
        height=560,
        margin=dict(t=70, b=80, l=70, r=30),
        boxgap=0.15,
        boxgroupgap=0.1,
    )
    fig.update_xaxes(
        title_text="district (N flats with this room count)",
        title_standoff=18,
        type="category",
        categoryorder="array",
        categoryarray=region_order,
        tickmode="array",
        tickvals=region_order,
        ticktext=ticktext,
        tickangle=45,
        showticklabels=True,
        automargin=True,
        showline=True,
        linewidth=1,
        linecolor="#5c6673",
        mirror=True,
        range=[-0.5, len(region_order) - 0.5],
    )
    fig.update_yaxes(
        title_text=y_label,
        automargin=True,
        showline=True,
        linewidth=1,
        linecolor="#5c6673",
        mirror=True,
    )
    return fig


def list_districts_with_data(db_path):
    """District names that have at least one listing (excluding Yerevan)."""
    _, districts = load_listings(db_path)
    if districts.empty:
        return []
    return districts["region_name"].tolist()


def build_district_trend_figure(db_path, district_name, y="price"):
    """
    Five time-series subplots for one district (rooms 1, 2, 3, 4, 5+).
    Each shows min, Q1, median, Q3, max from LISTING_PRICE_HISTORY.
    """
    if y not in ("price", "price_per_square"):
        y = "price"

    y_label = "price" if y == "price" else "price per m²"
    room_groups = [1, 2, 3, 4, LARGE_ROOM_GROUP]

    with sqlite3.connect(db_path) as connection:
        try:
            hist = pd.read_sql_query(
                """
                SELECT h.price, h.price_per_square, h.scraped_at, r.room_num
                FROM LISTING_PRICE_HISTORY h
                JOIN REAL_ESTATE r ON r.id = h.listing_id
                JOIN REGION g ON g.id = r.region_id
                WHERE g.region_name = ?
                """,
                connection,
                params=(district_name,),
            )
        except sqlite3.Error:
            hist = pd.DataFrame()

    n_rows = len(room_groups)
    fig = make_subplots(
        rows=n_rows,
        cols=1,
        shared_xaxes=False,
        subplot_titles=[
            f"rooms: {g}" if g != LARGE_ROOM_GROUP else "rooms: 5+"
            for g in room_groups
        ],
        vertical_spacing=min(0.07, 0.55 / max(n_rows - 1, 1)),
    )

    if hist.empty:
        fig.update_layout(
            title=f"{district_name}: no price history yet",
            width=1200,
            height=420 * n_rows,
        )
        return fig

    hist = hist.copy()
    hist["room_group"] = hist["room_num"].map(_room_group)
    hist["scrape_day"] = pd.to_datetime(hist["scraped_at"], utc=True, errors="coerce")
    hist = hist.dropna(subset=["scrape_day", "room_group", y])
    hist["scrape_day"] = hist["scrape_day"].dt.tz_convert(None).dt.normalize()

    series = [
        ("min", "#922b21", "dash"),
        ("q1", "#8a4b08", "dot"),
        ("median", "#0f6e56", "solid"),
        ("q3", "#1f4e79", "dot"),
        ("max", "#6c3483", "dash"),
    ]

    for row_idx, room_group in enumerate(room_groups):
        row = row_idx + 1
        sub = hist[hist["room_group"] == room_group]
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
            f"rooms: {room_group} ({total} history points)"
            if room_group != LARGE_ROOM_GROUP
            else f"rooms: 5+ ({total} history points)"
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
            title_text=y_label,
            showgrid=True,
            automargin=True,
            matches=None,
            row=row,
            col=1,
        )

    fig.update_layout(
        title=dict(
            text=f"{district_name}: price trends by room count",
            y=0.995,
            yanchor="top",
        ),
        width=1200,
        height=420 * n_rows,
        margin=dict(t=70, b=100, l=70, r=30),
        # Keep legend under all subplots so it never covers the title
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.02,
            x=0,
            xanchor="left",
        ),
        hovermode="x unified",
    )
    return fig
