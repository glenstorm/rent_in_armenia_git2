from dash import Dash, dcc, html, Input, Output
import plotly.express as px
import sqlite3
import pandas as pd

app = Dash(__name__)


app.layout = html.Div([
	html.H4("Analysis of the restaurant's revenue"),
	html.P("x-axis:"),
	dcc.Checklist(
		id='box-plots-x-x-axis',
		options=['room_num', 'region_id'],
		value=['room_num'],
		inline=True
	),
	html.P("y-axis:"),
	dcc.RadioItems(
		id='box-plots-x-y-axis',
		options=['price', 'price_per_square'],
		value='price',
		inline=True
	),
	dcc.Graph(id="box-plots-x-graph"),
])


@app.callback(
	Output("box-plots-x-graph", "figure"),
	Input("box-plots-x-x-axis", "value"),
	Input("box-plots-x-y-axis", "value"))
def generate_chart(x, y):
	try:
		with sqlite3.connect('real_estate.db') as connection:
			df = pd.read_sql_query("SELECT * FROM real_estate WHERE region_id = 3", connection)
			fig = px.box(df, x=x, y=y, width=1600, height=1600)
			return fig
	finally:
		connection.close()


if __name__ == "__main__":
	app.run_server(debug=True)
