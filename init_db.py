import sqlite3

from city import DISTRICTS


def init_db(db_path="real_estate.db", schema_path="schema.sql"):
    connection = sqlite3.connect(db_path)
    try:
        with open(schema_path, encoding="utf-8") as f:
            connection.executescript(f.read())

        cur = connection.cursor()
        for district_id, region_name in DISTRICTS.items():
            cur.execute(
                "INSERT INTO REGION (id, region_name) VALUES (?, ?)",
                (district_id, region_name),
            )
        connection.commit()
    finally:
        connection.close()


if __name__ == "__main__":
    init_db()
