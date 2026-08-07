from datetime import datetime

from fastapi import APIRouter, HTTPException, Query

from restapi.air.reading import AirReading
from restapi.air.repository import AirReadingRepository
from restapi.air.schemas import AirReadingResponse


def build_rooms_router(repository: AirReadingRepository) -> APIRouter:
    router = APIRouter(prefix="/rooms", tags=["rooms"])

    @router.get("", response_model=list[str])
    def list_rooms() -> list[str]:
        return repository.list_rooms()

    @router.get("/latest", response_model=list[AirReadingResponse])
    def latest() -> list[AirReading]:
        return repository.latest()

    @router.get("/{room}/latest", response_model=AirReadingResponse)
    def latest_for_room(room: str) -> AirReading:
        reading = repository.latest_for_room(room)
        if reading is None:
            raise HTTPException(status_code=404, detail=f"No readings for room '{room}'")
        return reading

    @router.get("/{room}/history", response_model=list[AirReadingResponse])
    def history(
        room: str,
        start: datetime,
        end: datetime,
        limit: int = Query(default=1000, ge=1, le=10000),
    ) -> list[AirReading]:
        if start >= end:
            raise HTTPException(status_code=400, detail="'start' must be before 'end'")
        return repository.history(room, start, end, limit)

    return router
