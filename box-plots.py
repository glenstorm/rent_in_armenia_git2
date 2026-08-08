from dash import Dash, Input, Output, dcc, html

from charts import build_rent_box_figure

app = Dash(__name__)

app.layout = html.Div(
    [
        html.H4("Analysis of the rent statistics in Yerevan"),
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
    Input("box-plots-x-y-axis", "value"),
)
def generate_chart(y):
    return build_rent_box_figure("real_estate.db", y=y)


if __name__ == "__main__":
    app.run(debug=True)
