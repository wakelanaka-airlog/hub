import json

import pytest

from collector.errors import MeasurementParseError
from collector.air.parsing import parse_air_measurement
from collector.air.reading import AirReading


def test_parse_air_measurement_parses_valid_payload():
    payload = json.dumps(
        {
            "room": "living_room",
            "timestamp": 1738156800000,
            "co2Ppm": 404,
            "temperatureCelsius": 25.0,
            "humidityPercent": 50.0,
        }
    ).encode()

    reading = parse_air_measurement(payload)

    assert reading == AirReading(
        room="living_room",
        timestamp_unix_millis=1738156800000,
        co2_ppm=404,
        temperature_celsius=25.0,
        humidity_percent=50.0,
    )


def test_parse_air_measurement_raises_on_invalid_json():
    with pytest.raises(MeasurementParseError):
        parse_air_measurement(b"not valid json")


def test_parse_air_measurement_raises_on_missing_field():
    payload = json.dumps(
        {
            "room": "living_room",
            "timestamp": 1738156800000,
            "co2Ppm": 404,
            "temperatureCelsius": 25.0,
            # humidityPercent missing
        }
    ).encode()

    with pytest.raises(MeasurementParseError):
        parse_air_measurement(payload)
