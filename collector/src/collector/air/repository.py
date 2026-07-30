from typing import Protocol

from collector.air.reading import AirReading


class AirReadingRepository(Protocol):

    def save(self, reading: AirReading) -> None: ...
