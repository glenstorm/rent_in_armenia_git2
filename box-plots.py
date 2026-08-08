import sqlite3

import pandas as pd
import plotly.express as px
from dash import Dash, Input, Output, dcc, html

app = Dash(__name__)


app.layout = html.Div(
    [
        html.H4("Analysis of the rent statistics in Yerevan"),
        html.P("x-axis:"),
        dcc.Checklist(
            id="box-plots-x-x-axis",
            options=["room_num", "region_id"],
            value=["room_num"],
            inline=True,
        ),
        html.P("y-axis:"),
        dcc.RadioItems(
            id="box-plots-x-y-axis",
            options=["price", "price_per_square"],
            value="price",
            inline=True,
        ),
        dcc.Graph(id="box-plots-x-graph"),
    ]
)


@app.callback(
    Output("box-plots-x-graph", "figure"),
    Input("box-plots-x-x-axis", "value"),
    Input("box-plots-x-y-axis", "value"),
)
def generate_chart(x, y):
    with sqlite3.connect("real_estate.db") as connection:
        df = pd.read_sql_query("SELECT * FROM real_estate", connection)
        fig = px.box(df, x=x, y=y, width=1600, height=1600)
        return fig


if __name__ == "__main__":
    app.run(debug=True)
