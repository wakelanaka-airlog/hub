from collector.reading import Reading


class PostgresReadingRepository:
    def __init__(self, connection):
        self._connection = connection

    def save(self, reading: Reading) -> None:
        with self._connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO air_measurements (time, room, co2_ppm, temperature_celsius, humidity_percent) "
                "VALUES (to_timestamp(%s / 1000.0), %s, %s, %s, %s)",
                (reading.timestamp_unix_millis, reading.room, reading.co2_ppm,
                reading.temperature_celsius, reading.humidity_percent),
            )
        self._connection.commit()
