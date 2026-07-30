from dataclasses import dataclass

@dataclass
class AirReading:
    room: str
    timestamp_unix_millis: int
    co2_ppm: int
    temperature_celsius: float
    humidity_percent: float
