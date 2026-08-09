from datetime import datetime, timezone
from pathlib import Path

import psycopg2
from testcontainers.community.postgres import PostgresContainer

from collector.air.postgres_repository import PostgresAirReadingRepository
from collector.air.reading import AirReading

TIMESCALEDB_INIT_DIR = Path(__file__).resolve().parents[3] / "timescaledb" / "init"


def _apply_sql_migrations(connection) -> None:
    # timescaledb.continuous DDL can't run as part of a multi-statement
    # transaction block: Postgres implicitly wraps every statement in a
    # single multi-statement query string into one transaction, regardless
    # of the client's autocommit setting, so each statement needs its own
    # execute() call (this is what psql -f does under the hood too).
    connection.autocommit = True
    with connection.cursor() as cursor:
        for sql_file in (
            "001-measurements.sql",
            "003-air-measurements-continuous-aggregate.sql",
            "004-air-measurements-unique-room-time.sql",
        ):
            for statement in (TIMESCALEDB_INIT_DIR / sql_file).read_text().split(";"):
                if statement.strip():
                    cursor.execute(statement)
    connection.autocommit = False


def test_raw_readings_saved_by_the_collector_are_averaged_into_the_15_minute_bucket():
    with PostgresContainer("timescale/timescaledb:latest-pg16", driver=None) as postgres:
        connection = psycopg2.connect(postgres.get_connection_url())
        _apply_sql_migrations(connection)

        repository = PostgresAirReadingRepository(connection)
        bucket_start = datetime(2026, 1, 1, 8, 0, tzinfo=timezone.utc)
        repository.save(
            AirReading(
                room="living_room",
                timestamp_unix_millis=int(bucket_start.timestamp() * 1000),
                co2_ppm=500,
                temperature_celsius=20.0,
                humidity_percent=40.0,
            )
        )
        repository.save(
            AirReading(
                room="living_room",
                timestamp_unix_millis=int((bucket_start.timestamp() + 5 * 60) * 1000),
                co2_ppm=540,
                temperature_celsius=21.0,
                humidity_percent=42.0,
            )
        )

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT co2_ppm, temperature_celsius, humidity_percent FROM air_measurements_15min "
                "WHERE room = %s AND bucket = %s",
                ("living_room", bucket_start),
            )
            co2_ppm, temperature_celsius, humidity_percent = cursor.fetchone()

        assert co2_ppm == 520
        assert temperature_celsius == 20.5
        assert humidity_percent == 41.0


def test_readings_saved_a_bucket_apart_are_not_averaged_together():
    with PostgresContainer("timescale/timescaledb:latest-pg16", driver=None) as postgres:
        connection = psycopg2.connect(postgres.get_connection_url())
        _apply_sql_migrations(connection)

        repository = PostgresAirReadingRepository(connection)
        first_bucket = datetime(2026, 1, 1, 8, 0, tzinfo=timezone.utc)
        second_bucket = datetime(2026, 1, 1, 8, 15, tzinfo=timezone.utc)
        repository.save(
            AirReading(
                room="living_room",
                timestamp_unix_millis=int(first_bucket.timestamp() * 1000),
                co2_ppm=500,
                temperature_celsius=20.0,
                humidity_percent=40.0,
            )
        )
        repository.save(
            AirReading(
                room="living_room",
                timestamp_unix_millis=int(second_bucket.timestamp() * 1000),
                co2_ppm=600,
                temperature_celsius=22.0,
                humidity_percent=44.0,
            )
        )

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT bucket, co2_ppm FROM air_measurements_15min WHERE room = %s ORDER BY bucket",
                ("living_room",),
            )
            rows = cursor.fetchall()

        assert rows == [(first_bucket, 500), (second_bucket, 600)]
