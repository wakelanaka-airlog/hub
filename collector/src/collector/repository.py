from typing import Protocol

from collector.reading import Reading


class ReadingRepository(Protocol):

    def save(self, reading: Reading) -> None: ...
