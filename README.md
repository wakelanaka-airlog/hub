# hub

The server side of wakelanaka-airlog: everything that runs on the NAS and
receives data from the sensor nodes (see the `air-node` repo). Deployed via
Docker Compose.

Currently the MQTT broker (Mosquitto), the PostgreSQL/TimescaleDB database,
the collector service and the REST API.

## Setup

Copy `.env.example` to `.env` and fill in real values (not committed - see
`.gitignore`). This holds the TimescaleDB credentials, the read-only
`restapi` database role's credentials, and the REST API's shared secret:

```sh
cp .env.example .env
```

Generate the broker's password file (not committed - see `.gitignore`).
All air-nodes share one `air-nodes` account (see `mosquitto/config/acl.conf` -
it's publish-only, restricted to the `wakelanaka-airlog/air-node/#` topic
prefix, so a compromised/misbehaving node still can't subscribe to
anything or publish outside its own topic tree):

```sh
docker run -it --rm -v "$(pwd)/mosquitto/config:/mosquitto/config" \
  eclipse-mosquitto:2 mosquitto_passwd -c /mosquitto/config/password_file air-nodes
```

This prompts for a password and writes the hashed credentials - set this
same username/password in every node's `menuconfig` (`MQTT_USERNAME`/
`MQTT_PASSWORD`). Add the `collector` account the same way, without `-c`
(which would overwrite the file) - it's read-only across all node types
(see `acl.conf`):

```sh
docker run -it --rm -v "$(pwd)/mosquitto/config:/mosquitto/config" \
  eclipse-mosquitto:2 mosquitto_passwd /mosquitto/config/password_file collector
```

Set this username/password in the collector's own `.env` (`MQTT_USERNAME`/
`MQTT_PASSWORD`).

Add a `dashboard` account the same way - it's read-only, scoped to
`wakelanaka-airlog/air-node/#` only (see `acl.conf`), for the Qt6 dashboard's
per-station "online" check (subscribes to see which rooms are actively
publishing; see `dashboard/CLAUDE.md`):

```sh
docker run -it --rm -v "$(pwd)/mosquitto/config:/mosquitto/config" \
  eclipse-mosquitto:2 mosquitto_passwd /mosquitto/config/password_file dashboard
```

Set this username/password in the dashboard's own `.env` (`MQTT_USERNAME`/
`MQTT_PASSWORD`).

`mosquitto_passwd` (run via a throwaway root container above) leaves
`password_file` owned by `root` with `600` permissions, which the broker's
internal unprivileged `mosquitto` user can't read - fix this after
(re)generating it, or the broker fails to start ("Unable to open pwfile"):

```sh
docker run --rm --entrypoint chown -v "$(pwd)/mosquitto/config:/mosquitto/config" \
  eclipse-mosquitto:2 mosquitto:mosquitto /mosquitto/config/password_file
docker run --rm --entrypoint chmod -v "$(pwd)/mosquitto/config:/mosquitto/config" \
  eclipse-mosquitto:2 0700 /mosquitto/config/password_file
```

`acl.conf` doesn't need this - Mosquitto only warns about its ownership/
permissions (not yet enforced as of 2.x), and it needs to stay normally
host-editable/git-committable, unlike the gitignored `password_file`.

## Running

```sh
docker compose up -d
```

The broker listens on port 1883. Clients authenticate with a username/
password from the password file above - anonymous connections are
rejected, and `acl.conf` further restricts what each account can do.

TimescaleDB listens on port 5432, with credentials from `.env`. The schema
(`air_measurements` hypertable) and the read-only `restapi` role (from
`RESTAPI_DB_USER`/`RESTAPI_DB_PASSWORD`) are created automatically on first
startup from `timescaledb/init/`. If the database volume already existed
before adding `002-restapi-role.sh` (init scripts only run once, against an
empty volume), apply it by hand instead of recreating the volume:

```sh
docker compose exec timescaledb bash /docker-entrypoint-initdb.d/002-restapi-role.sh
```

(`RESTAPI_DB_USER`/`RESTAPI_DB_PASSWORD` are already in the running
container's environment - set via `environment:` in `docker-compose.yml`
from `.env` - so no need to pass them again.)

Same story for `003-air-measurements-continuous-aggregate.sql` (compression
policy + the `air_measurements_15min` continuous aggregate) if your volume
predates it:

```sh
docker compose exec -T timescaledb psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -f /docker-entrypoint-initdb.d/003-air-measurements-continuous-aggregate.sql
```

Same for `004-air-measurements-unique-room-time.sql` (makes the collector's
insert idempotent against redelivered readings) - **note this one will fail
if `air_measurements` already has duplicate `(room, time)` rows**; resolve
those first (e.g. keep one row per duplicate set) before applying it:

```sh
docker compose exec -T timescaledb psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -f /docker-entrypoint-initdb.d/004-air-measurements-unique-room-time.sql
```

The REST API listens on port 8000 and serves the latest and historical
`air_measurements` readings to the Qt6 dashboard. Every route except
`/health` requires the `RESTAPI_API_KEY` value from `.env` as an `X-API-Key`
header:

```sh
curl -H "X-API-Key: $RESTAPI_API_KEY" http://localhost:8000/rooms/latest
```

See `restapi/` for the full route list.
