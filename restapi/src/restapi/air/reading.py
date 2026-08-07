from dataclasses import dataclass
from datetime import datetime


@dataclass
class AirReading:
    room: str
    time: datetime
    co2_ppm: int
    temperature_celsius: float
    humidity_percent: float
