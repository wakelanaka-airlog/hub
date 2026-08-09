import logging

from collector.errors import MeasurementParseError
from collector.air.parsing import parse_air_measurement
from collector.air.repository import AirReadingRepository

logger = logging.getLogger(__name__)


def handle_air_measurement(topic: str, payload: bytes, repository: AirReadingRepository) -> None:
    try:
        reading = parse_air_measurement(topic, payload)
    except MeasurementParseError:
        logger.exception("Discarding unparseable air-node measurement")
        return

    try:
        repository.save(reading)
    except Exception:
        logger.exception("Discarding air-node measurement: repository save failed")
