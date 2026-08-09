from datetime import datetime, timezone

import numpy as np

from apartment import area_is_plausible
from city import district_name
from listing_history import record_price_history


class District:
    """
    DistrictChunk: info about prices in region
    """

    def __init__(self, id):
        # id is the list.am `n` parameter / REGION.id
        self.id = id
        self.name = district_name(id)
        self.apartments = []

    def add(self, apartment):
        if not area_is_plausible(apartment.room_num, apartment.square):
            return
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

    def __purge_invalid_squares(self, connection):
        """Drop stored listings in this district with impossible area values."""
        cur = connection.cursor()
        rows = cur.execute(
            """
            SELECT id, room_num, square
            FROM REAL_ESTATE
            WHERE region_id = ?
            """,
            (self.id,),
        ).fetchall()
        bad_ids = [
            listing_id
            for listing_id, room_num, square in rows
            if not area_is_plausible(room_num, square)
        ]
        if not bad_ids:
            return 0

        placeholders = ",".join("?" * len(bad_ids))
        cur.execute(
            f"DELETE FROM LISTING_PRICE_HISTORY WHERE listing_id IN ({placeholders})",
            bad_ids,
        )
        cur.execute(
            f"DELETE FROM REAL_ESTATE WHERE id IN ({placeholders})",
            bad_ids,
        )
        return len(bad_ids)

    def flush_to_db(self, connection):
        before = len(self.apartments)
        self.apartments = [
            apt
            for apt in self.apartments
            if area_is_plausible(apt.room_num, apt.square)
        ]
        skipped_area = before - len(self.apartments)
        if skipped_area:
            print(
                f"{self.name}: skipped {skipped_area} listing(s) with invalid square",
                flush=True,
            )

        self.__filter_data()
        removed = self.__purge_invalid_squares(connection)
        if removed:
            print(
                f"{self.name}: removed {removed} stored listing(s) with invalid square",
                flush=True,
            )

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
