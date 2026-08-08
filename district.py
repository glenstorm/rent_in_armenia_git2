import numpy as np

from city import districts


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
        for x in self.apartments:
            cur.execute("SELECT 1 FROM REAL_ESTATE WHERE link = ? LIMIT 1", (x.link,))
            if cur.fetchone():
                continue

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

        connection.commit()
