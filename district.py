from datetime import datetime, timezone

import numpy as np

from city import districts
from listing_history import record_price_history


class District:
    """
    DistrictChunk: info about prices in region
    """

    def __init__(self, id):
        # URL / DB region ids are 1-based; districts list is 0-based
        self.id = id
        if not 1 <= id <= len(districts):
            raise ValueError(f"Invalid district id: {id}")
        self.name = districts[self.id - 1]
        self.apartments = []

    def add(self, apartment):
        self.apartments.append(apartment)

    def print_apartments(self):
        for x in self.apartments:
            print(x)

    def __filter_data(self):
        if len(self.apartments) == 0:
            return

        prices = [obj.price for obj in self.apartments]
        mean = np.mean(prices)
        stdev = np.std(prices)
        lower_bound = mean - 3 * stdev
        upper_bound = mean + 3 * stdev

        self.apartments = list(
            filter(
                lambda data: (data.price >= lower_bound) & (data.price <= upper_bound),
                self.apartments,
            )
        )

    def flush_to_db(self, connection):
        self.__filter_data()

        cur = connection.cursor()
        scraped_at = datetime.now(timezone.utc).isoformat()

        for x in self.apartments:
            cur.execute(
                "SELECT id FROM REAL_ESTATE WHERE link = ? LIMIT 1",
                (x.link,),
            )
            row = cur.fetchone()
            if row:
                listing_id = row[0]
                cur.execute(
                    """
                    UPDATE REAL_ESTATE
                    SET square = ?,
                        is_agent = ?,
                        region_id = ?,
                        price = ?,
                        price_per_square = ?,
                        room_num = ?,
                        address = ?
                    WHERE id = ?
                    """,
                    (
                        x.square,
                        x.is_agent,
                        self.id,
                        x.price,
                        x.price_per_square,
                        x.room_num,
                        x.address,
                        listing_id,
                    ),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO REAL_ESTATE
                    (square, is_agent, region_id, price, price_per_square, room_num, address, link)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        x.square,
                        x.is_agent,
                        self.id,
                        x.price,
                        x.price_per_square,
                        x.room_num,
                        x.address,
                        x.link,
                    ),
                )
                listing_id = cur.lastrowid

            record_price_history(
                connection,
                listing_id=listing_id,
                price=x.price,
                price_per_square=x.price_per_square,
                scraped_at=scraped_at,
            )

        connection.commit()
