from datetime import datetime

from restapi.air.reading import AirReading


class PostgresAirReadingRepository:
    def __init__(self, pool):
        self._pool = pool

    def list_rooms(self) -> list[str]:
        rows = self._query("SELECT DISTINCT room FROM air_measurements ORDER BY room")
        return [room for (room,) in rows]

    def latest(self) -> list[AirReading]:
        rows = self._query(
            "SELECT DISTINCT ON (room) room, time, co2_ppm, temperature_celsius, humidity_percent "
            "FROM air_measurements ORDER BY room, time DESC"
        )
        return [self._to_reading(row) for row in rows]

    def latest_for_room(self, room: str) -> AirReading | None:
        rows = self._query(
            "SELECT room, time, co2_ppm, temperature_celsius, humidity_percent "
            "FROM air_measurements WHERE room = %s ORDER BY time DESC LIMIT 1",
            (room,),
        )
        return self._to_reading(rows[0]) if rows else None

    def history(self, room: str, start: datetime, end: datetime, limit: int) -> list[AirReading]:
        rows = self._query(
            "SELECT room, time, co2_ppm, temperature_celsius, humidity_percent "
            "FROM air_measurements WHERE room = %s AND time >= %s AND time <= %s "
            "ORDER BY time ASC LIMIT %s",
            (room, start, end, limit),
        )
        return [self._to_reading(row) for row in rows]

    def _query(self, sql: str, params: tuple = ()) -> list[tuple]:
        connection = self._pool.getconn()
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
                return cursor.fetchall()
        finally:
            self._pool.putconn(connection)

    @staticmethod
    def _to_reading(row: tuple) -> AirReading:
        room, time, co2_ppm, temperature_celsius, humidity_percent = row
        return AirReading(
            room=room,
            time=time,
            co2_ppm=co2_ppm,
            temperature_celsius=temperature_celsius,
            humidity_percent=humidity_percent,
        )
