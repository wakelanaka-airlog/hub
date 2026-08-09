from datetime import datetime, timedelta, timezone
from pathlib import Path

import psycopg2
import pytest
from psycopg2.pool import ThreadedConnectionPool
from testcontainers.community.postgres import PostgresContainer

from restapi.air.postgres_repository import PostgresAirReadingRepository

TIMESCALEDB_INIT_DIR = Path(__file__).resolve().parents[3] / "timescaledb" / "init"


def _apply_sql_migrations(connection) -> None:
    connection.autocommit = True
    with connection.cursor() as cursor:
        for sql_file in ("001-measurements.sql", "003-air-measurements-continuous-aggregate.sql"):
            for statement in (TIMESCALEDB_INIT_DIR / sql_file).read_text().split(";"):
                if statement.strip():
                    cursor.execute(statement)
    connection.autocommit = False


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
        _apply_sql_migrations(setup_connection)

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


def test_history_averages_readings_that_land_in_the_same_bucket():
    with PostgresContainer("timescale/timescaledb:latest-pg16", driver=None) as postgres:
        connection = psycopg2.connect(postgres.get_connection_url())
        _apply_sql_migrations(connection)
        first = datetime(2026, 1, 1, 8, 0, tzinfo=timezone.utc)
        second = first + timedelta(minutes=5)
        _seed(connection, "living_room", first, 500, 20.0, 40.0)
        _seed(connection, "living_room", second, 540, 21.0, 42.0)

        pool = ThreadedConnectionPool(1, 5, postgres.get_connection_url())
        try:
            repository = PostgresAirReadingRepository(pool)
            readings = repository.history(
                "living_room", start=first - timedelta(days=10), end=first + timedelta(days=10), limit=1000
            )
        finally:
            pool.closeall()

        assert len(readings) == 1
        assert readings[0].co2_ppm == 520
        assert readings[0].temperature_celsius == pytest.approx(20.5)
        assert readings[0].humidity_percent == pytest.approx(41.0)


def test_history_respects_the_limit_across_buckets():
    with PostgresContainer("timescale/timescaledb:latest-pg16", driver=None) as postgres:
        connection = psycopg2.connect(postgres.get_connection_url())
        _apply_sql_migrations(connection)
        first_bucket = datetime(2026, 1, 1, 8, 0, tzinfo=timezone.utc)
        second_bucket = first_bucket + timedelta(hours=1)
        _seed(connection, "living_room", first_bucket, 500, 20.0, 40.0)
        _seed(connection, "living_room", second_bucket, 600, 22.0, 44.0)

        pool = ThreadedConnectionPool(1, 5, postgres.get_connection_url())
        try:
            repository = PostgresAirReadingRepository(pool)
            readings = repository.history(
                "living_room",
                start=first_bucket - timedelta(hours=24),
                end=first_bucket + timedelta(hours=24),
                limit=1,
            )
        finally:
            pool.closeall()

        assert len(readings) == 1
        assert readings[0].co2_ppm == 500
