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
        "/api/daily",
        "/api/inbox",
        "/api/resources/status",
        "/api/worktrees",
        "/api/tasks",
        "/api/tasks/all",
        "/api/tasks/{task_id}",
        "/api/tasks/{task_id}/graph",
    }
    # 集約エンドポイントはProject指定を取らない
    assert "parameters" not in schema["paths"]["/api/tasks/all"]["get"]
    for path in (
        "/api/tasks",
        "/api/tasks/{task_id}",
        "/api/tasks/{task_id}/graph",
    ):
        project = next(
            parameter
            for parameter in schema["paths"][path]["get"]["parameters"]
            if parameter["name"] == "project"
        )
        assert project["required"] is False
        assert project["schema"]["default"] == "whub-dev"


def test_main_writes_valid_json(capsys) -> None:
    main()

    assert json.loads(capsys.readouterr().out)["openapi"]
