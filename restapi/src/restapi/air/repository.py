from datetime import datetime
from typing import Protocol

from restapi.air.reading import AirReading


class AirReadingRepository(Protocol):

    def list_rooms(self) -> list[str]: ...

    def latest(self) -> list[AirReading]: ...

    def latest_for_room(self, room: str) -> AirReading | None: ...

    def history(self, room: str, start: datetime, end: datetime, limit: int) -> list[AirReading]: ...
