# hub

The server side of wakelanaka-airlog: everything that runs on the NAS and
receives data from the sensor nodes (see the `air-node` repo). Deployed via
Docker Compose.

Currently the MQTT broker (Mosquitto) and the PostgreSQL/TimescaleDB
database; the collector-App and REST API will be added here as services
once built.

## Setup

Copy `.env.example` to `.env` and fill in real values (not committed - see
`.gitignore`). This holds the TimescaleDB credentials:

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
(`air_measurements` hypertable) is created automatically on first startup
from `timescaledb/init/`.
