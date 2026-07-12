"""OpenAPI schema export tests."""
from __future__ import annotations

import json

from whub.webapp.openapi import main, openapi_schema


def test_openapi_schema_contains_all_resource_endpoints() -> None:
    schema = openapi_schema()

    assert set(schema["paths"]) >= {
        "/api/todos",
        "/api/todos/{todo_id}",
        "/api/projects",
        "/api/backlog/{project}",
        "/api/inbox",
        "/api/resources/status",
    }


def test_main_writes_valid_json(capsys) -> None:
    main()

    assert json.loads(capsys.readouterr().out)["openapi"]
