import os

import uvicorn
from psycopg2.pool import ThreadedConnectionPool

from restapi.air.postgres_repository import PostgresAirReadingRepository
from restapi.app import create_app

DEFAULT_PORT = 8000
MIN_POOL_CONNECTIONS = 1
MAX_POOL_CONNECTIONS = 5


def main() -> None:
    pool = ThreadedConnectionPool(
        MIN_POOL_CONNECTIONS,
        MAX_POOL_CONNECTIONS,
        host=os.environ["POSTGRES_HOST"],
        port=os.environ.get("POSTGRES_PORT", "5432"),
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        dbname=os.environ["POSTGRES_DB"],
    )
    repository = PostgresAirReadingRepository(pool)
    app = create_app(repository, api_key=os.environ["RESTAPI_API_KEY"])

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("RESTAPI_PORT", DEFAULT_PORT)))


if __name__ == "__main__":
    main()
