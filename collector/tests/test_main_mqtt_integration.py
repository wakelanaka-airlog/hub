import json
import threading

import paho.mqtt.client as mqtt
from testcontainers.community.mqtt import MosquittoContainer

from collector.air.reading import AirReading
from collector.main import build_air_node_on_connect


class FakeAirReadingRepository:
    def __init__(self):
        self.saved = []
        self._reading_added = threading.Event()

    def save(self, reading):
        self.saved.append(reading)
        self._reading_added.set()

    def wait_for_a_reading(self, timeout):
        return self._reading_added.wait(timeout)


def _measurement_payload(room: str) -> str:
    return json.dumps(
        {
            "room": room,
            "timestamp": 1738156800000,
            "co2Ppm": 404,
            "temperatureCelsius": 25.0,
            "humidityPercent": 50.0,
        }
    )


def test_air_node_wiring_only_processes_messages_matching_the_measurement_wildcard():
    repository = FakeAirReadingRepository()
    subscribed = threading.Event()

    with MosquittoContainer() as mosquitto:
        collector_client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
        collector_client.on_connect = build_air_node_on_connect(repository)
        collector_client.on_subscribe = lambda *args, **kwargs: subscribed.set()

        collector_client.connect(
            mosquitto.get_container_host_ip(),
            int(mosquitto.get_exposed_port(mosquitto.MQTT_PORT)),
        )
        collector_client.loop_start()

        try:
            assert subscribed.wait(timeout=5), "collector never subscribed"

            mosquitto.publish_message(
                "wakelanaka-airlog/invalid/measurement",
                _measurement_payload("should_not_be_saved"),
            )
            mosquitto.publish_message(
                "wakelanaka-airlog/air-node/living_room/measurement",
                _measurement_payload("living_room"),
            )

            assert repository.wait_for_a_reading(timeout=5), "no reading was saved"
        finally:
            collector_client.loop_stop()
            collector_client.disconnect()

    assert repository.saved == [
        AirReading(
            room="living_room",
            timestamp_unix_millis=1738156800000,
            co2_ppm=404,
            temperature_celsius=25.0,
            humidity_percent=50.0,
        )
    ]
