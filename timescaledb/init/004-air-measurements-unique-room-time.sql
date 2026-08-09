-- MQTT QoS 1 is at-least-once by design, and the air-node's own publish
-- backlog (SendingState/InMemoryMeasurementStore) can independently
-- redeliver a reading the broker already received, if the original
-- publish's ack was merely delayed rather than actually lost (see
-- hub/CLAUDE.md). Rather than trying to make delivery perfectly-once,
-- make the collector's insert idempotent against it: replace the plain
-- (room, time) index with a unique one, so a redelivered reading is a
-- silent no-op instead of a duplicate row.
DROP INDEX air_measurements_room_time_idx;
CREATE UNIQUE INDEX ON air_measurements (room, time DESC);
