import json

from collector.air.handler import handle_air_measurement
from collector.air.reading import AirReading

TOPIC = "wakelanaka-airlog/air-node/living_room/measurement"


class FakeAirReadingRepository:
    def __init__(self):
        self.saved = []

    def save(self, reading):
        self.saved.append(reading)


class FailingAirReadingRepository:
    def save(self, reading):
        raise RuntimeError("simulated repository failure")


def test_handle_air_measurement_saves_valid_reading():
    repository = FakeAirReadingRepository()
    payload = json.dumps(
        {
            "timestamp": 1738156800000,
            "co2Ppm": 404,
            "temperatureCelsius": 25.0,
            "humidityPercent": 50.0,
        }
    ).encode()

    handle_air_measurement(TOPIC, payload, repository)

    assert repository.saved == [
        AirReading(
            room="living_room",
            timestamp_unix_millis=1738156800000,
            co2_ppm=404,
            temperature_celsius=25.0,
            humidity_percent=50.0,
        )
    ]


def test_handle_air_measurement_ignores_invalid_payload():
    repository = FakeAirReadingRepository()

    handle_air_measurement(TOPIC, b"not valid json", repository)

    assert repository.saved == []


def test_handle_air_measurement_does_not_propagate_repository_errors():
    payload = json.dumps(
        {
            "timestamp": 1738156800000,
            "co2Ppm": 404,
            "temperatureCelsius": 25.0,
            "humidityPercent": 50.0,
        }
    ).encode()

    handle_air_measurement(TOPIC, payload, FailingAirReadingRepository())
