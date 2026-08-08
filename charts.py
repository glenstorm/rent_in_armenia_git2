"""Plotly chart builders for rent statistics."""

import sqlite3

import pandas as pd
import plotly.express as px


def load_listings(db_path):
    with sqlite3.connect(db_path) as connection:
        return pd.read_sql_query(
            """
            SELECT r.*, g.region_name
            FROM REAL_ESTATE r
            LEFT JOIN REGION g ON g.id = r.region_id
            """,
            connection,
        )


def build_rent_box_figure(db_path, y="price"):
    """Box plots by region, one row per room count."""
    if y not in ("price", "price_per_square"):
        y = "price"

    df = load_listings(db_path)
    if df.empty:
        fig = px.scatter(title="No listings yet — run a scrape first")
        fig.update_layout(width=1200, height=400)
        return fig

    region_order = (
        df[["region_id", "region_name"]]
        .drop_duplicates()
        .sort_values("region_id")["region_name"]
        .tolist()
    )
    room_order = sorted(df["room_num"].dropna().unique().tolist())

    fig = px.box(
        df,
        x="region_name",
        y=y,
        facet_row="room_num",
        category_orders={
            "region_name": region_order,
            "room_num": room_order,
        },
        labels={
            "region_name": "region",
            "room_num": "rooms",
            "price": "price",
            "price_per_square": "price per m²",
        },
        width=1200,
        height=550 * max(1, len(room_order)),
    )
    fig.update_xaxes(title_text="region", tickangle=45, showticklabels=True)
    fig.update_yaxes(matches=None)
    fig.for_each_annotation(
        lambda a: a.update(text=a.text.replace("rooms=", "rooms: "))
    )
    return fig
