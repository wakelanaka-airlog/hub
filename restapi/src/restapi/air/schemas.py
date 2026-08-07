from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AirReadingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    room: str
    time: datetime
    co2_ppm: int
    temperature_celsius: float
    humidity_percent: float
