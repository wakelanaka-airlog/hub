from fastapi import APIRouter, Depends, FastAPI

from restapi.air.repository import AirReadingRepository
from restapi.air.routes import build_rooms_router
from restapi.auth import build_require_api_key

health_router = APIRouter()


@health_router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def create_app(repository: AirReadingRepository, api_key: str) -> FastAPI:
    app = FastAPI(title="wakelanaka-airlog REST API")
    require_api_key = build_require_api_key(api_key)

    app.include_router(health_router)
    app.include_router(
        build_rooms_router(repository),
        dependencies=[Depends(require_api_key)],
    )

    return app
