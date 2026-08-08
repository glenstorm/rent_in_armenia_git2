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


def build_rent_box_figure(db_path, y="price"):
    """
    One subplot per room group (1, 2, 3, 4, then 5+ combined).
    X-axis labels are district name plus how many flats of that room
    group exist in the district. Districts with no listings overall
    are omitted from every plot.
    """
    if y not in ("price", "price_per_square"):
        y = "price"

    df, districts = load_listings(db_path)
    if df.empty or districts.empty:
        fig = go.Figure()
        fig.update_layout(
            title="No listings yet — run a scrape first",
            width=1200,
            height=400,
        )
        return fig

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

    counts = (
        df.groupby(["room_group", "region_name"], dropna=False)
        .size()
        .to_dict()
    )

    y_label = "price" if y == "price" else "price per m²"
    n_rows = len(room_groups)
    subplot_titles = []
    for g in room_groups:
        total = int(sum(counts.get((g, name), 0) for name in region_order))
        label = f"rooms: {g}" if g != LARGE_ROOM_GROUP else "rooms: 5+"
        subplot_titles.append(f"{label} ({total} flats)")

    # Modest gap so titles/labels fit without large empty bands.
    # Plotly requires vertical_spacing * (n_rows - 1) < 1.
    if n_rows > 1:
        vertical_spacing = min(0.07, 0.55 / (n_rows - 1))
    else:
        vertical_spacing = 0.05

    fig = make_subplots(
        rows=n_rows,
        cols=1,
        shared_xaxes=False,
        subplot_titles=subplot_titles,
        vertical_spacing=vertical_spacing,
    )

    for row_idx, room_group in enumerate(room_groups):
        row = row_idx + 1
        line_color, fill_color = PLOT_COLORS[row_idx % len(PLOT_COLORS)]
        sub = df[df["room_group"] == room_group]
        ticktext = [
            f"{name} ({counts.get((room_group, name), 0)})" for name in region_order
        ]

        # Always keep every district column, including empty ones (count 0),
        # so each plot has the same full district axis.
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
                ),
                row=row,
                col=1,
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
            row=row,
            col=1,
        )
        fig.update_yaxes(
            title_text=y_label,
            automargin=True,
            showline=True,
            linewidth=1,
            linecolor="#5c6673",
            mirror=True,
            row=row,
            col=1,
        )

    fig.update_layout(
        width=1200,
        height=580 * max(1, n_rows),
        margin=dict(t=70, b=80, l=70, r=30),
        boxgap=0.15,
        boxgroupgap=0.1,
    )
    return fig
