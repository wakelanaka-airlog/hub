from datetime import datetime, timezone

from fastapi.testclient import TestClient

from restapi.air.reading import AirReading
from restapi.app import create_app

API_KEY = "test-api-key"

LIVING_ROOM_EARLIER = AirReading(
    room="living_room",
    time=datetime(2026, 1, 1, 8, 0, 0, tzinfo=timezone.utc),
    co2_ppm=500,
    temperature_celsius=21.0,
    humidity_percent=45.0,
)
LIVING_ROOM_LATEST = AirReading(
    room="living_room",
    time=datetime(2026, 1, 1, 9, 0, 0, tzinfo=timezone.utc),
    co2_ppm=600,
    temperature_celsius=21.5,
    humidity_percent=46.0,
)
BEDROOM_LATEST = AirReading(
    room="bedroom",
    time=datetime(2026, 1, 1, 8, 30, 0, tzinfo=timezone.utc),
    co2_ppm=450,
    temperature_celsius=19.0,
    humidity_percent=50.0,
)


class FakeAirReadingRepository:
    def __init__(self, readings_by_room: dict[str, list[AirReading]]):
        self._readings_by_room = readings_by_room

    def list_rooms(self) -> list[str]:
        return sorted(self._readings_by_room)

    def latest(self) -> list[AirReading]:
        return [
            readings[-1]
            for room, readings in sorted(self._readings_by_room.items())
            if readings
        ]

    def latest_for_room(self, room: str) -> AirReading | None:
        readings = self._readings_by_room.get(room, [])
        return readings[-1] if readings else None

    def history(self, room: str, start: datetime, end: datetime, limit: int) -> list[AirReading]:
        readings = self._readings_by_room.get(room, [])
        return [r for r in readings if start <= r.time <= end][:limit]


def _client() -> TestClient:
    repository = FakeAirReadingRepository(
        {
            "living_room": [LIVING_ROOM_EARLIER, LIVING_ROOM_LATEST],
            "bedroom": [BEDROOM_LATEST],
        }
    )
    return TestClient(create_app(repository, api_key=API_KEY))


def _auth_headers() -> dict[str, str]:
    return {"X-API-Key": API_KEY}


def test_health_is_public():
    response = _client().get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_rooms_endpoint_rejects_missing_api_key():
    response = _client().get("/rooms")

    assert response.status_code == 401


def test_rooms_endpoint_rejects_wrong_api_key():
    response = _client().get("/rooms", headers={"X-API-Key": "wrong-key"})

    assert response.status_code == 401


def test_list_rooms_returns_room_names():
    response = _client().get("/rooms", headers=_auth_headers())

    assert response.status_code == 200
    assert response.json() == ["bedroom", "living_room"]


def test_latest_returns_the_newest_reading_per_room():
    response = _client().get("/rooms/latest", headers=_auth_headers())

    assert response.status_code == 200
    body = response.json()
    assert [reading["room"] for reading in body] == ["bedroom", "living_room"]
    assert body[1]["co2_ppm"] == LIVING_ROOM_LATEST.co2_ppm


def test_latest_for_room_returns_the_newest_reading():
    response = _client().get("/rooms/living_room/latest", headers=_auth_headers())

    assert response.status_code == 200
    assert response.json()["co2_ppm"] == LIVING_ROOM_LATEST.co2_ppm


def test_latest_for_unknown_room_returns_404():
    response = _client().get("/rooms/attic/latest", headers=_auth_headers())

    assert response.status_code == 404


def test_history_returns_readings_within_the_time_range():
    response = _client().get(
        "/rooms/living_room/history",
        headers=_auth_headers(),
        params={
            "start": "2026-01-01T00:00:00Z",
            "end": "2026-01-01T23:59:59Z",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert [reading["co2_ppm"] for reading in body] == [
        LIVING_ROOM_EARLIER.co2_ppm,
        LIVING_ROOM_LATEST.co2_ppm,
    ]


def test_history_respects_the_limit_parameter():
    response = _client().get(
        "/rooms/living_room/history",
        headers=_auth_headers(),
        params={
            "start": "2026-01-01T00:00:00Z",
            "end": "2026-01-01T23:59:59Z",
            "limit": 1,
        },
    )

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_history_rejects_start_after_end():
    response = _client().get(
        "/rooms/living_room/history",
        headers=_auth_headers(),
        params={
            "start": "2026-01-01T23:59:59Z",
            "end": "2026-01-01T00:00:00Z",
        },
    )

    assert response.status_code == 400


def test_history_requires_start_and_end():
    response = _client().get(
        "/rooms/living_room/history",
        headers=_auth_headers(),
    )

    assert response.status_code == 422
