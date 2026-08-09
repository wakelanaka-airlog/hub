import json
from dataclasses import dataclass
from unittest.mock import patch

import paho.mqtt.client as mqtt

import collector.main as main
from collector.air.reading import AirReading
from collector.main import AIR_NODE_MEASUREMENT_TOPIC, build_air_node_on_connect


class FakeAirReadingRepository:
    def __init__(self):
        self.saved = []

    def save(self, reading):
        self.saved.append(reading)


class FakeClient:
    def __init__(self):
        self.subscribed_topics = []
        self.message_callbacks = {}

    def subscribe(self, topic, qos=0):
        self.subscribed_topics.append((topic, qos))

    def message_callback_add(self, topic, callback):
        self.message_callbacks[topic] = callback


@dataclass
class FakeMessage:
    topic: str
    payload: bytes


def _measurement_payload() -> bytes:
    return json.dumps(
        {
            "timestamp": 1738156800000,
            "co2Ppm": 404,
            "temperatureCelsius": 25.0,
            "humidityPercent": 50.0,
        }
    ).encode()


def test_air_node_on_connect_subscribes_to_the_measurement_wildcard():
    on_connect = build_air_node_on_connect(FakeAirReadingRepository())
    client = FakeClient()

    on_connect(client, userdata=None, connect_flags=None, reason_code=0)

    assert client.subscribed_topics == [(AIR_NODE_MEASUREMENT_TOPIC, 1)]


def test_air_node_on_connect_registers_a_message_callback_for_the_wildcard():
    on_connect = build_air_node_on_connect(FakeAirReadingRepository())
    client = FakeClient()

    on_connect(client, userdata=None, connect_flags=None, reason_code=0)

    assert AIR_NODE_MEASUREMENT_TOPIC in client.message_callbacks


def test_air_message_callback_handles_any_room_matching_the_wildcard():
    repository = FakeAirReadingRepository()
    client = FakeClient()
    on_connect = build_air_node_on_connect(repository)
    on_connect(client, userdata=None, connect_flags=None, reason_code=0)
    on_air_message = client.message_callbacks[AIR_NODE_MEASUREMENT_TOPIC]

    on_air_message(
        client=None,
        userdata=None,
        message=FakeMessage(
            topic="wakelanaka-airlog/air-node/living_room/measurement",
            payload=_measurement_payload(),
        ),
    )
    on_air_message(
        client=None,
        userdata=None,
        message=FakeMessage(
            topic="wakelanaka-airlog/air-node/bedroom/measurement",
            payload=_measurement_payload(),
        ),
    )

    assert repository.saved == [
        AirReading(
            room="living_room",
            timestamp_unix_millis=1738156800000,
            co2_ppm=404,
            temperature_celsius=25.0,
            humidity_percent=50.0,
        ),
        AirReading(
            room="bedroom",
            timestamp_unix_millis=1738156800000,
            co2_ppm=404,
            temperature_celsius=25.0,
            humidity_percent=50.0,
        ),
    ]


def test_air_message_callback_ignores_invalid_payload():
    repository = FakeAirReadingRepository()
    client = FakeClient()
    on_connect = build_air_node_on_connect(repository)
    on_connect(client, userdata=None, connect_flags=None, reason_code=0)
    on_air_message = client.message_callbacks[AIR_NODE_MEASUREMENT_TOPIC]

    on_air_message(
        client=None,
        userdata=None,
        message=FakeMessage(
            topic="wakelanaka-airlog/air-node/kitchen/measurement",
            payload=b"not valid json",
        ),
    )

    assert repository.saved == []


def test_main_connects_with_a_persistent_mqtt_session(monkeypatch):
    monkeypatch.setenv("POSTGRES_HOST", "db-host")
    monkeypatch.setenv("POSTGRES_USER", "user")
    monkeypatch.setenv("POSTGRES_PASSWORD", "pass")
    monkeypatch.setenv("POSTGRES_DB", "airlog")
    monkeypatch.setenv("MQTT_BROKER_HOST", "broker-host")
    monkeypatch.setenv("MQTT_BROKER_PORT", "1883")
    monkeypatch.setenv("MQTT_USERNAME", "collector")
    monkeypatch.setenv("MQTT_PASSWORD", "pass")

    with patch("collector.main.psycopg2.connect"), patch("collector.main.mqtt.Client") as mock_client_cls:
        main.main()

    mock_client_cls.assert_called_once_with(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id=main.MQTT_CLIENT_ID,
        clean_session=False,
    )
