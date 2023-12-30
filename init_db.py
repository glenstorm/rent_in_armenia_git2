import sqlite3
from city import districts

connection = sqlite3.connect('real_estate.db')
try:
	with open('schema.sql') as f:
		connection.executescript(f.read())

	cur = connection.cursor()
	for index, val in enumerate(districts):
		cur.execute("INSERT INTO REGION (id, region_name) VALUES (?, ?)", (index+1, val))
	connection.commit()
finally:
	connection.close()
