import secrets
from collections.abc import Callable

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def build_require_api_key(expected_api_key: str) -> Callable[..., None]:
    def require_api_key(provided: str | None = Security(api_key_header)) -> None:
        if provided is None or not secrets.compare_digest(provided, expected_api_key):
            raise HTTPException(status_code=401, detail="Invalid or missing API key")

    return require_api_key
