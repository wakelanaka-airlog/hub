from unittest.mock import patch

import restapi.main as main


def test_main_wires_the_connection_pool_and_serves_the_app(monkeypatch):
    monkeypatch.setenv("POSTGRES_HOST", "db-host")
    monkeypatch.setenv("POSTGRES_USER", "restapi")
    monkeypatch.setenv("POSTGRES_PASSWORD", "pass")
    monkeypatch.setenv("POSTGRES_DB", "airlog")
    monkeypatch.setenv("RESTAPI_API_KEY", "secret")
    monkeypatch.delenv("POSTGRES_PORT", raising=False)
    monkeypatch.delenv("RESTAPI_PORT", raising=False)

    with (
        patch("restapi.main.ThreadedConnectionPool") as mock_pool_cls,
        patch("restapi.main.uvicorn.run") as mock_run,
    ):
        main.main()

    mock_pool_cls.assert_called_once_with(
        1,
        5,
        host="db-host",
        port="5432",
        user="restapi",
        password="pass",
        dbname="airlog",
    )
    mock_run.assert_called_once()
    _, kwargs = mock_run.call_args
    assert kwargs["host"] == "0.0.0.0"
    assert kwargs["port"] == 8000


def test_main_uses_restapi_port_override(monkeypatch):
    monkeypatch.setenv("POSTGRES_HOST", "db-host")
    monkeypatch.setenv("POSTGRES_USER", "restapi")
    monkeypatch.setenv("POSTGRES_PASSWORD", "pass")
    monkeypatch.setenv("POSTGRES_DB", "airlog")
    monkeypatch.setenv("RESTAPI_API_KEY", "secret")
    monkeypatch.setenv("RESTAPI_PORT", "9000")

    with (
        patch("restapi.main.ThreadedConnectionPool"),
        patch("restapi.main.uvicorn.run") as mock_run,
    ):
        main.main()

    _, kwargs = mock_run.call_args
    assert kwargs["port"] == 9000
