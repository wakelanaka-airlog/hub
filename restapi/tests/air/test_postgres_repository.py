from datetime import datetime, timezone
from pathlib import Path

import psycopg2
import pytest
from psycopg2.pool import ThreadedConnectionPool
from testcontainers.community.postgres import PostgresContainer

from restapi.air.postgres_repository import PostgresAirReadingRepository

INIT_SQL_PATH = Path(__file__).resolve().parents[3] / "timescaledb" / "init" / "001-measurements.sql"


def _seed(connection, room: str, time: datetime, co2_ppm: int, temperature_celsius: float, humidity_percent: float) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO air_measurements (time, room, co2_ppm, temperature_celsius, humidity_percent) "
            "VALUES (%s, %s, %s, %s, %s)",
            (time, room, co2_ppm, temperature_celsius, humidity_percent),
        )
    connection.commit()


@pytest.fixture
def repository():
    with PostgresContainer("timescale/timescaledb:latest-pg16", driver=None) as postgres:
        setup_connection = psycopg2.connect(postgres.get_connection_url())
        with setup_connection.cursor() as cursor:
            cursor.execute(INIT_SQL_PATH.read_text())
        setup_connection.commit()

        _seed(setup_connection, "living_room", datetime(2026, 1, 1, 8, 0, tzinfo=timezone.utc), 500, 21.0, 45.0)
        _seed(setup_connection, "living_room", datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc), 600, 21.5, 46.0)
        _seed(setup_connection, "bedroom", datetime(2026, 1, 1, 8, 30, tzinfo=timezone.utc), 450, 19.0, 50.0)
        setup_connection.close()

        pool = ThreadedConnectionPool(1, 5, postgres.get_connection_url())
        try:
            yield PostgresAirReadingRepository(pool)
        finally:
            pool.closeall()


def test_list_rooms_returns_distinct_rooms_sorted(repository):
    assert repository.list_rooms() == ["bedroom", "living_room"]


def test_latest_returns_the_most_recent_reading_per_room(repository):
    readings = repository.latest()

    assert [(reading.room, reading.co2_ppm) for reading in readings] == [
        ("bedroom", 450),
        ("living_room", 600),
    ]


def test_latest_for_room_returns_the_most_recent_reading(repository):
    reading = repository.latest_for_room("living_room")

    assert reading.co2_ppm == 600
    assert reading.time == datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc)


def test_latest_for_room_returns_none_for_unknown_room(repository):
    assert repository.latest_for_room("attic") is None


def test_history_returns_readings_within_range_ordered_ascending(repository):
    readings = repository.history(
        "living_room",
        start=datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc),
        end=datetime(2026, 1, 1, 23, 59, tzinfo=timezone.utc),
        limit=1000,
    )

    assert [reading.co2_ppm for reading in readings] == [500, 600]


def test_history_respects_the_limit(repository):
    readings = repository.history(
        "living_room",
        start=datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc),
        end=datetime(2026, 1, 1, 23, 59, tzinfo=timezone.utc),
        limit=1,
    )

    assert len(readings) == 1
    assert readings[0].co2_ppm == 500


def test_history_excludes_readings_outside_the_range(repository):
    readings = repository.history(
        "living_room",
        start=datetime(2026, 1, 1, 8, 30, tzinfo=timezone.utc),
        end=datetime(2026, 1, 1, 23, 59, tzinfo=timezone.utc),
        limit=1000,
    )

    assert [reading.co2_ppm for reading in readings] == [600]
