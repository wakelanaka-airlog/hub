ALTER TABLE air_measurements SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'room',
    timescaledb.compress_orderby = 'time DESC'
);

SELECT add_compression_policy('air_measurements', compress_after => INTERVAL '2 days');

CREATE MATERIALIZED VIEW air_measurements_15min
WITH (timescaledb.continuous) AS
SELECT
    room,
    time_bucket('15 minutes', time) AS bucket,
    avg(co2_ppm)::real AS co2_ppm,
    avg(temperature_celsius)::real AS temperature_celsius,
    avg(humidity_percent)::real AS humidity_percent
FROM air_measurements
GROUP BY room, bucket;

ALTER MATERIALIZED VIEW air_measurements_15min SET (timescaledb.materialized_only = false);

SELECT add_continuous_aggregate_policy('air_measurements_15min',
    start_offset => INTERVAL '1 hour',
    end_offset => INTERVAL '15 minutes',
    schedule_interval => INTERVAL '15 minutes');
