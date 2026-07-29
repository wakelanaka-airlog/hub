import json

from collector.handler import handle_air_measurement
from collector.reading import Reading


class FakeReadingRepository:
    def __init__(self):
        self.saved = []

    def save(self, reading):
        self.saved.append(reading)


def test_handle_air_measurement_saves_valid_reading():
    repository = FakeReadingRepository()
    payload = json.dumps(
        {
            "room": "living_room",
            "timestamp": 1738156800000,
            "co2Ppm": 404,
            "temperatureCelsius": 25.0,
            "humidityPercent": 50.0,
        }
    ).encode()

    handle_air_measurement(payload, repository)

    assert repository.saved == [
        Reading(
            room="living_room",
            timestamp_unix_millis=1738156800000,
            co2_ppm=404,
            temperature_celsius=25.0,
            humidity_percent=50.0,
        )
    ]


def test_handle_air_measurement_ignores_invalid_payload():
    repository = FakeReadingRepository()

    handle_air_measurement(b"not valid json", repository)

    assert repository.saved == []
