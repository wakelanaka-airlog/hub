#!/bin/bash
set -euo pipefail

: "${RESTAPI_DB_USER:?RESTAPI_DB_USER must be set}"
: "${RESTAPI_DB_PASSWORD:?RESTAPI_DB_PASSWORD must be set}"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    DO \$\$
    BEGIN
       IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '${RESTAPI_DB_USER}') THEN
          CREATE ROLE "${RESTAPI_DB_USER}" WITH LOGIN PASSWORD '${RESTAPI_DB_PASSWORD}';
       END IF;
    END
    \$\$;

    GRANT CONNECT ON DATABASE "${POSTGRES_DB}" TO "${RESTAPI_DB_USER}";
    GRANT USAGE ON SCHEMA public TO "${RESTAPI_DB_USER}";
    GRANT SELECT ON air_measurements TO "${RESTAPI_DB_USER}";
EOSQL
