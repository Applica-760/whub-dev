"""S2b web API tests.

検証するケース:
1. todo一覧がserviceの表示順で返る。
2. todoの追加・完了・削除がserviceを呼び、仕様どおり応答する。
3. todo完了はdone=trueだけを受理する。
4. project一覧がmanifestの名前だけを返す。
5. backlogの読取・追記がserviceを呼ぶ。
6. 空白だけのbacklog memoを拒否する。
7. inbox投函が作成ファイル名を返す。
8. ServiceError系とManifestErrorをHTTPエラーへ変換する。
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from whub.models import ManifestError
from whub.models.todo import Todo
from whub.services.errors import NotFoundError, ServiceError
from whub.tests.helpers import manifest
from whub.webapp.server import create_app


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    (dist_dir / "index.html").write_text("<main>whub</main>")
    return TestClient(create_app(dist_dir))


def _todo(
    todo_id: int,
    *,
    done: bool = False,
    done_at: date | None = None,
) -> Todo:
    return Todo(
        id=todo_id,
        title=f"todo-{todo_id}",
        priority="red",
        created_at=date(2026, 7, 10),
        done=done,
        done_at=done_at,
    )


def test_get_todos_returns_service_display_order(client: TestClient) -> None:
    # ケース1
    pending = [_todo(2), _todo(1)]
    completed = [_todo(3, done=True, done_at=date(2026, 7, 9))]
    with (
        patch("whub.webapp.routers.todos.list_pending", return_value=pending),
        patch("whub.webapp.routers.todos.list_completed", return_value=completed),
    ):
        response = client.get("/api/todos")

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["pending"]] == [2, 1]
    assert [item["id"] for item in response.json()["completed"]] == [3]


def test_todo_mutations_use_services(client: TestClient) -> None:
    # ケース2
    item = _todo(1)
    completed = _todo(1, done=True, done_at=date(2026, 7, 10))
    m = manifest()
    with (
        patch("whub.webapp.routers.todos.load_manifest", return_value=m),
        patch("whub.webapp.routers.todos.add_todo", return_value=item) as mock_add,
        patch(
            "whub.webapp.routers.todos.complete_todo",
            return_value=completed,
        ) as mock_complete,
        patch("whub.webapp.routers.todos.remove_todo") as mock_remove,
    ):
        create_response = client.post(
            "/api/todos",
            json={
                "title": "new task",
                "project": "local",
                "priority": "red",
                "due_date": "2026-07-20",
            },
        )
        complete_response = client.patch("/api/todos/1", json={"done": True})
        delete_response = client.delete("/api/todos/1")

    assert create_response.status_code == 201
    assert create_response.json()["id"] == 1
    mock_add.assert_called_once_with(
        m,
        "new task",
        "local",
        "red",
        date(2026, 7, 20),
    )
    assert complete_response.status_code == 200
    assert complete_response.json()["done"] is True
    mock_complete.assert_called_once_with(1)
    assert delete_response.status_code == 204
    assert delete_response.content == b""
    mock_remove.assert_called_once_with(1)


def test_todo_completion_only_accepts_done_true(client: TestClient) -> None:
    # ケース3
    response = client.patch("/api/todos/1", json={"done": False})

    assert response.status_code == 422


def test_get_projects_returns_manifest_names(client: TestClient) -> None:
    # ケース4
    with patch("whub.webapp.routers.projects.load_manifest", return_value=manifest()):
        response = client.get("/api/projects")

    assert response.status_code == 200
    assert response.json() == {"projects": ["local", "remote", "nested", "no-resource"]}


def test_backlog_endpoints_use_services(client: TestClient) -> None:
    # ケース5
    m = manifest()
    with (
        patch("whub.webapp.routers.backlog.load_manifest", return_value=m),
        patch(
            "whub.webapp.routers.backlog.read_backlog",
            return_value="existing memo\n",
        ) as mock_read,
        patch("whub.webapp.routers.backlog.append_backlog") as mock_append,
    ):
        get_response = client.get("/api/backlog/local")
        post_response = client.post("/api/backlog/local", json={"memo": "  new memo  "})

    assert get_response.status_code == 200
    assert get_response.json() == {"project": "local", "content": "existing memo\n"}
    mock_read.assert_called_once_with(m, "local")
    assert post_response.status_code == 201
    assert post_response.content == b""
    mock_append.assert_called_once_with(m, "local", "new memo")


def test_backlog_rejects_blank_memo(client: TestClient) -> None:
    # ケース6
    response = client.post("/api/backlog/local", json={"memo": " \n"})

    assert response.status_code == 422


def test_create_inbox_returns_created_filename(client: TestClient) -> None:
    # ケース7
    m = manifest()
    path = Path("/tmp/inbox/20260710_1630_note.md")
    with (
        patch("whub.webapp.routers.inbox.load_manifest", return_value=m),
        patch(
            "whub.webapp.routers.inbox.create_inbox_note",
            return_value=path,
        ) as mock_create,
    ):
        response = client.post("/api/inbox", json={"title": "note", "body": "body"})

    assert response.status_code == 201
    assert response.json() == {"filename": "20260710_1630_note.md"}
    mock_create.assert_called_once_with(m, "note", "body")


def test_service_errors_are_mapped_to_http_responses(client: TestClient) -> None:
    # ケース8
    with patch(
        "whub.webapp.routers.todos.list_pending",
        side_effect=ServiceError("invalid operation"),
    ):
        service_response = client.get("/api/todos")
    with patch(
        "whub.webapp.routers.todos.complete_todo",
        side_effect=NotFoundError("todo not found: 99"),
    ):
        not_found_response = client.patch("/api/todos/99", json={"done": True})
    with patch(
        "whub.webapp.routers.projects.load_manifest",
        side_effect=ManifestError("invalid manifest"),
    ):
        manifest_response = client.get("/api/projects")

    assert service_response.status_code == 400
    assert service_response.json() == {"detail": "invalid operation"}
    assert not_found_response.status_code == 404
    assert not_found_response.json() == {"detail": "todo not found: 99"}
    assert manifest_response.status_code == 500
    assert manifest_response.json() == {"detail": "invalid manifest"}
