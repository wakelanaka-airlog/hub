from pathlib import Path

import psycopg2
import pytest
from testcontainers.community.postgres import PostgresContainer

from collector.postgres_repository import PostgresReadingRepository
from collector.reading import Reading

INIT_SQL_PATH = Path(__file__).resolve().parents[2] / "timescaledb" / "init" / "001-measurements.sql"


def test_save_persists_reading():
    with PostgresContainer("timescale/timescaledb:latest-pg16", driver=None) as postgres:
        connection = psycopg2.connect(postgres.get_connection_url())
        with connection.cursor() as cursor:
            cursor.execute(INIT_SQL_PATH.read_text())
        connection.commit()

        repository = PostgresReadingRepository(connection)
        reading = Reading(
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
