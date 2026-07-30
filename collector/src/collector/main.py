import logging
import os

import paho.mqtt.client as mqtt
import psycopg2

from collector.air.handler import handle_air_measurement
from collector.air.postgres_repository import PostgresAirReadingRepository

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

AIR_NODE_MEASUREMENT_TOPIC = "wakelanaka-airlog/air-node/+/measurement"


def build_air_node_on_connect(repository):
    def on_air_message(client, userdata, message):
        handle_air_measurement(message.payload, repository)

    def on_connect(client, userdata, connect_flags, reason_code, properties=None):
        logger.info("Subscribing to %s", AIR_NODE_MEASUREMENT_TOPIC)
        client.subscribe(AIR_NODE_MEASUREMENT_TOPIC)
        client.message_callback_add(AIR_NODE_MEASUREMENT_TOPIC, on_air_message)

    return on_connect


def main() -> None:
    connection = psycopg2.connect(
        host=os.environ["POSTGRES_HOST"],
        port=os.environ.get("POSTGRES_PORT", "5432"),
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        dbname=os.environ["POSTGRES_DB"],
    )
    air_repository = PostgresAirReadingRepository(connection)

    node_family_on_connects = [
        build_air_node_on_connect(air_repository),
    ]

    def on_connect(client, userdata, connect_flags, reason_code, properties=None):
        logger.info("Connected to broker (%s)", reason_code)
        for node_family_on_connect in node_family_on_connects:
            node_family_on_connect(client, userdata, connect_flags, reason_code, properties)

    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    client.username_pw_set(os.environ["MQTT_USERNAME"], os.environ["MQTT_PASSWORD"])
    client.on_connect = on_connect

    client.connect(os.environ["MQTT_BROKER_HOST"], int(os.environ["MQTT_BROKER_PORT"]))
    client.loop_forever()


if __name__ == "__main__":
    main()
