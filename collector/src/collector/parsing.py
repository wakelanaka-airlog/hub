import json
from collector.reading import Reading
from collector.errors import MeasurementParseError


def parse_air_measurement(payload: bytes) -> Reading:
    try:
        json_payload = json.loads(payload)
        return Reading(
            room=json_payload["room"],
            timestamp_unix_millis=json_payload["timestamp"],
            co2_ppm=json_payload["co2Ppm"],
            temperature_celsius=json_payload["temperatureCelsius"],
            humidity_percent=json_payload["humidityPercent"])
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        raise MeasurementParseError(f"invalid measurement payload: {payload!r}") from e

