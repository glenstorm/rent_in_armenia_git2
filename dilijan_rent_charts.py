"""Plotly charts for Dilijan long-term rent (apartments + houses)."""

import sqlite3

import pandas as pd
import plotly.graph_objects as go

from dilijan_rent import PROPERTY_APARTMENT, PROPERTY_HOUSE

PROPERTY_TYPES = (PROPERTY_APARTMENT, PROPERTY_HOUSE)
PROPERTY_LABELS = {
    PROPERTY_APARTMENT: "Apartments",
    PROPERTY_HOUSE: "Houses",
}


def load_dilijan_rent(db_path, property_types=None):
    types = list(property_types) if property_types else list(PROPERTY_TYPES)
    if not types:
        return pd.DataFrame()
    placeholders = ",".join("?" * len(types))
    try:
        with sqlite3.connect(db_path) as connection:
            return pd.read_sql_query(
                f"""
                SELECT *
                FROM DILIJAN_RENT
                WHERE property_type IN ({placeholders})
                """,
                connection,
                params=tuple(types),
            )
    except sqlite3.Error:
        return pd.DataFrame()


def dilijan_rent_stats(db_path, property_types=None):
    df = load_dilijan_rent(db_path, property_types)
    if df.empty:
        return {"count": 0, "by_type": [], "by_rooms": []}

    by_type = (
        df.groupby("property_type", dropna=False)
        .size()
        .reset_index(name="count")
    )
    type_order = {name: idx for idx, name in enumerate(PROPERTY_TYPES)}
    by_type = by_type.sort_values(
        "property_type",
        key=lambda s: s.map(lambda n: type_order.get(n, 99)),
    )

    by_rooms = (
        df.groupby("room_num", dropna=False)
        .size()
        .reset_index(name="count")
        .sort_values("room_num")
    )
    return {
        "count": int(len(df)),
        "by_type": [
            {
                "name": PROPERTY_LABELS.get(row.property_type, row.property_type),
                "property_type": row.property_type,
                "count": int(row.count),
            }
            for row in by_type.itertuples(index=False)
        ],
        "by_rooms": [
            {"rooms": str(int(row.room_num)), "count": int(row.count)}
            for row in by_rooms.itertuples(index=False)
        ],
    }


def build_dilijan_rent_type_box_figure(db_path, y="price", property_types=None):
    if y not in ("price", "price_per_square"):
        y = "price"
    df = load_dilijan_rent(db_path, property_types)
    if df.empty:
        fig = go.Figure()
        fig.update_layout(
            title="Dilijan rent — no data",
            width=1200,
            height=420,
        )
        return fig

    plot_df = df.dropna(subset=[y]) if y == "price_per_square" else df
    if plot_df.empty:
        fig = go.Figure()
        fig.update_layout(
            title=f"Dilijan rent — no data for {y}",
            width=1200,
            height=420,
        )
        return fig

    order = [t for t in PROPERTY_TYPES if t in set(plot_df["property_type"])]
    fig = go.Figure()
    for prop in order:
        vals = plot_df.loc[plot_df["property_type"] == prop, y].tolist()
        if not vals:
            continue
        fig.add_trace(
            go.Box(
                y=vals,
                name=PROPERTY_LABELS.get(prop, prop),
                boxpoints="outliers",
            )
        )
    ylabel = "AMD / month" if y == "price" else "AMD / m² / month"
    fig.update_layout(
        title=f"Dilijan long-term rent — {y.replace('_', ' ')} by type ({len(plot_df)} listings)",
        yaxis_title=ylabel,
        width=1200,
        height=480,
        showlegend=False,
    )
    return fig


def build_dilijan_rent_room_box_figure(db_path, y="price", property_types=None):
    if y not in ("price", "price_per_square"):
        y = "price"
    df = load_dilijan_rent(db_path, property_types)
    if df.empty:
        fig = go.Figure()
        fig.update_layout(
            title="Dilijan rent by rooms — no data",
            width=1200,
            height=420,
        )
        return fig

    plot_df = df.dropna(subset=[y]) if y == "price_per_square" else df
    if plot_df.empty:
        fig = go.Figure()
        fig.update_layout(
            title=f"Dilijan rent by rooms — no data for {y}",
            width=1200,
            height=420,
        )
        return fig

    room_order = sorted(int(r) for r in plot_df["room_num"].dropna().unique())
    fig = go.Figure()
    for rooms in room_order:
        vals = plot_df.loc[plot_df["room_num"] == rooms, y].tolist()
        if not vals:
            continue
        fig.add_trace(
            go.Box(
                y=vals,
                name=str(rooms),
                boxpoints="outliers",
            )
        )
    ylabel = "AMD / month" if y == "price" else "AMD / m² / month"
    fig.update_layout(
        title=f"Dilijan long-term rent — {y.replace('_', ' ')} by rooms ({len(plot_df)} listings)",
        xaxis_title="rooms",
        yaxis_title=ylabel,
        width=1200,
        height=480,
        showlegend=False,
        xaxis=dict(
            type="category",
            categoryorder="array",
            categoryarray=[str(r) for r in room_order],
        ),
    )
    return fig


def list_dilijan_rent_budget(
    db_path,
    property_types=None,
    max_price_amd=400_000,
    limit=30,
):
    df = load_dilijan_rent(db_path, property_types)
    if df.empty:
        return []
    df = df[df["price"] < int(max_price_amd)].copy()
    df = df.sort_values(["price", "room_num"], ascending=[True, True])
    if limit:
        df = df.head(int(limit))

    rows = []
    for row in df.itertuples(index=False):
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
        rows.append(
            {
                "property_type": row.property_type,
                "type_label": PROPERTY_LABELS.get(
                    row.property_type, row.property_type
                ),
                "price": int(row.price),
                "price_display": f"{int(row.price):,}".replace(",", " "),
                "rooms": int(row.room_num),
                "square": square,
                "ppm2_display": (
                    f"{int(round(ppm2)):,}".replace(",", " ")
                    if ppm2 is not None
                    else "—"
                ),
                "address": row.address,
                "link": row.link,
            }
        )
    return rows
