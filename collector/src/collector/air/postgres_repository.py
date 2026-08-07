from collector.air.reading import AirReading


class PostgresAirReadingRepository:
    def __init__(self, connection):
        self._connection = connection

    def save(self, reading: AirReading) -> None:
        try:
            with self._connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO air_measurements (time, room, co2_ppm, temperature_celsius, humidity_percent) "
                    "VALUES (to_timestamp(%s / 1000.0), %s, %s, %s, %s)",
                    (reading.timestamp_unix_millis, reading.room, reading.co2_ppm,
                    reading.temperature_celsius, reading.humidity_percent),
                )
            self._connection.commit()
        except Exception:
            self._connection.rollback()
            raise
