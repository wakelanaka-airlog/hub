import logging

from collector.errors import MeasurementParseError
from collector.parsing import parse_air_measurement
from collector.repository import ReadingRepository

logger = logging.getLogger(__name__)


def handle_air_measurement(payload: bytes, repository: ReadingRepository) -> None:
    try:
        reading = parse_air_measurement(payload)
    except MeasurementParseError:
        logger.exception("Discarding unparseable air-node measurement")
        return
    repository.save(reading)
