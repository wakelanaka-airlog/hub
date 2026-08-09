DROP INDEX air_measurements_room_time_idx;
CREATE UNIQUE INDEX ON air_measurements (room, time DESC);
