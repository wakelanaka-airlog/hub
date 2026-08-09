from pathlib import Path

import psycopg2
import pytest
from testcontainers.community.postgres import PostgresContainer

from collector.air.postgres_repository import PostgresAirReadingRepository
from collector.air.reading import AirReading

TIMESCALEDB_INIT_DIR = Path(__file__).resolve().parents[3] / "timescaledb" / "init"


def _apply_sql_migrations(connection) -> None:
    with connection.cursor() as cursor:
        cursor.execute((TIMESCALEDB_INIT_DIR / "001-measurements.sql").read_text())
        cursor.execute((TIMESCALEDB_INIT_DIR / "004-air-measurements-unique-room-time.sql").read_text())
    connection.commit()


def test_save_persists_reading():
    with PostgresContainer("timescale/timescaledb:latest-pg16", driver=None) as postgres:
        connection = psycopg2.connect(postgres.get_connection_url())
        _apply_sql_migrations(connection)

        repository = PostgresAirReadingRepository(connection)
        reading = AirReading(
            room="living_room",
            timestamp_unix_millis=1738156800000,
            co2_ppm=404,
            temperature_celsius=25.0,
            humidity_percent=50.0,
        )

        repository.save(reading)

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT room, co2_ppm, temperature_celsius, humidity_percent, "
                "EXTRACT(EPOCH FROM time) * 1000 FROM air_measurements"
            )
            room, co2_ppm, temperature_celsius, humidity_percent, timestamp_millis = cursor.fetchone()

        assert room == "living_room"
        assert co2_ppm == 404
        assert temperature_celsius == 25.0
        assert humidity_percent == 50.0
        assert timestamp_millis == pytest.approx(1738156800000, abs=1000)


def test_save_recovers_after_a_failed_insert_so_the_connection_stays_usable():
    with PostgresContainer("timescale/timescaledb:latest-pg16", driver=None) as postgres:
        connection = psycopg2.connect(postgres.get_connection_url())
        _apply_sql_migrations(connection)

        repository = PostgresAirReadingRepository(connection)

        invalid_reading = AirReading(
            room=None,  # violates the NOT NULL constraint on room
            timestamp_unix_millis=1738156800000,
            co2_ppm=404,
            temperature_celsius=25.0,
            humidity_percent=50.0,
        )
        with pytest.raises(Exception):
            repository.save(invalid_reading)

        valid_reading = AirReading(
            room="living_room",
            timestamp_unix_millis=1738156800000,
            co2_ppm=404,
            temperature_celsius=25.0,
            humidity_percent=50.0,
        )
        repository.save(valid_reading)

        with connection.cursor() as cursor:
            cursor.execute("SELECT room FROM air_measurements")
            rooms = [row[0] for row in cursor.fetchall()]

        assert rooms == ["living_room"]


def test_save_ignores_a_redelivered_reading_with_the_same_room_and_time():
    with PostgresContainer("timescale/timescaledb:latest-pg16", driver=None) as postgres:
        connection = psycopg2.connect(postgres.get_connection_url())
        _apply_sql_migrations(connection)

        repository = PostgresAirReadingRepository(connection)
        reading = AirReading(
            room="living_room",
            timestamp_unix_millis=1738156800000,
            co2_ppm=404,
            temperature_celsius=25.0,
            humidity_percent=50.0,
        )

        repository.save(reading)
        repository.save(reading)  # e.g. the air-node's own publish backlog redelivering it

        with connection.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM air_measurements")
            (count,) = cursor.fetchone()

        assert count == 1


def test_save_does_not_ignore_a_different_room_at_the_same_time():
    with PostgresContainer("timescale/timescaledb:latest-pg16", driver=None) as postgres:
        connection = psycopg2.connect(postgres.get_connection_url())
        _apply_sql_migrations(connection)

        repository = PostgresAirReadingRepository(connection)
        repository.save(
            AirReading(
                room="living_room",
                timestamp_unix_millis=1738156800000,
                co2_ppm=404,
                temperature_celsius=25.0,
                humidity_percent=50.0,
            )
        )
        repository.save(
            AirReading(
                room="bedroom",
                timestamp_unix_millis=1738156800000,
                co2_ppm=450,
                temperature_celsius=19.0,
                humidity_percent=55.0,
            )
        )

        with connection.cursor() as cursor:
            cursor.execute("SELECT room FROM air_measurements ORDER BY room")
            rooms = [row[0] for row in cursor.fetchall()]

        assert rooms == ["bedroom", "living_room"]
