import logging
import os

import paho.mqtt.client as mqtt
import psycopg2

from collector.handler import handle_air_measurement
from collector.postgres_repository import PostgresReadingRepository

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

AIR_NODE_MEASUREMENT_TOPIC = "wakelanaka-airlog/air-node/+/measurement"


def main() -> None:
    connection = psycopg2.connect(
        host=os.environ["POSTGRES_HOST"],
        port=os.environ.get("POSTGRES_PORT", "5432"),
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        dbname=os.environ["POSTGRES_DB"],
    )
    repository = PostgresReadingRepository(connection)

    def on_connect(client, userdata, connect_flags, reason_code, properties=None):
        logger.info("Connected to broker (%s), subscribing to %s", reason_code, AIR_NODE_MEASUREMENT_TOPIC)
        client.subscribe(AIR_NODE_MEASUREMENT_TOPIC)

    def on_message(client, userdata, message):
        handle_air_measurement(message.payload, repository)

    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    client.username_pw_set(os.environ["MQTT_USERNAME"], os.environ["MQTT_PASSWORD"])
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(os.environ["MQTT_BROKER_HOST"], int(os.environ["MQTT_BROKER_PORT"]))
    client.loop_forever()


if __name__ == "__main__":
    main()
