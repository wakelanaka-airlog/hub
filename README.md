# hub

The server side of wakelanaka-airlog: everything that runs on the NAS and
receives data from the sensor nodes (see the `node` repo). Deployed via
Docker Compose.

Currently just the MQTT broker (Mosquitto); the collector-App, REST API, and
PostgreSQL/TimescaleDB database will be added here as services once built.

## Setup

Generate the broker's password file (not committed - see `.gitignore`):

```sh
docker run --rm -v "$(pwd)/mosquitto/config:/mosquitto/config" \
  eclipse-mosquitto:2 mosquitto_passwd -c /mosquitto/config/password_file <username>
```

This prompts for a password and writes the hashed credentials. Add more
users the same way, without `-c` (which would overwrite the file).

## Running

```sh
docker compose up -d
```

The broker listens on port 1883. Nodes authenticate with the
username/password created above - anonymous connections are rejected.
