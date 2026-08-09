import json
from collector.air.reading import AirReading
from collector.errors import MeasurementParseError


def parse_air_measurement(topic: str, payload: bytes) -> AirReading:
    room = _room_from_topic(topic)
    try:
        json_payload = json.loads(payload)
        return AirReading(
            room=room,
            timestamp_unix_millis=json_payload["timestamp"],
            co2_ppm=json_payload["co2Ppm"],
            temperature_celsius=json_payload["temperatureCelsius"],
            humidity_percent=json_payload["humidityPercent"])
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        raise MeasurementParseError(f"invalid measurement payload: {payload!r}") from e


def _room_from_topic(topic: str) -> str:
    # Expected shape: wakelanaka-airlog/air-node/<room>/measurement - room is
    # the wildcard segment the collector's subscription (air-node/+/measurement)
    # matches on, not part of the JSON payload.
    parts = topic.split("/")
    if len(parts) != 4:
        raise MeasurementParseError(f"unexpected topic shape: {topic!r}")
    return parts[2]
