CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE TABLE air_measurements (
    time TIMESTAMPTZ NOT NULL,
    room TEXT NOT NULL,
    co2_ppm INTEGER NOT NULL CHECK (co2_ppm BETWEEN 0 AND 40000),
    temperature_celsius REAL NOT NULL CHECK (temperature_celsius BETWEEN -10 AND 60),
    humidity_percent REAL NOT NULL CHECK (humidity_percent BETWEEN 0 AND 100)
);

SELECT create_hypertable('air_measurements', 'time');

CREATE UNIQUE INDEX ON air_measurements (room, time DESC);

ALTER TABLE air_measurements SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'room',
    timescaledb.compress_orderby = 'time DESC'
);

SELECT add_compression_policy('air_measurements', compress_after => INTERVAL '2 days');
