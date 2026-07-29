CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE TABLE air_measurements (
    time TIMESTAMPTZ NOT NULL,
    room TEXT NOT NULL,
    co2_ppm INTEGER NOT NULL,
    temperature_celsius REAL NOT NULL,
    humidity_percent REAL NOT NULL
);

SELECT create_hypertable('air_measurements', 'time');

CREATE INDEX ON air_measurements (room, time DESC);
