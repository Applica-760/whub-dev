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
9. resource statusがserviceの結果を返す。
10. vaultのツリー取得・ノート取得がserviceを呼ぶ。
11. Knowledge取得がserviceを呼び、未配置を404へ変換する。
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
from whub.services.status import ResourceStatus
from whub.services.vault import VaultNode
from whub.tests.helpers import knowledge, manifest
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


def test_get_resource_status_returns_service_results(client: TestClient) -> None:
    # ケース9
    m = manifest()
    statuses = [
        ResourceStatus("local", "ok", "symlink", git="2 files"),
        ResourceStatus("remote", "unreachable", "remote", mount="stale"),
    ]
    with (
        patch("whub.webapp.routers.status.load_manifest", return_value=m),
        patch(
            "whub.webapp.routers.status.collect_resource_status",
            return_value=statuses,
        ) as mock_collect,
    ):
        response = client.get("/api/resources/status")

    assert response.status_code == 200
    assert response.json() == {
        "resources": [
            {
                "project": "local",
                "state": "ok",
                "type": "symlink",
                "mount": "-",
                "tmux": "-",
                "git": "2 files",
            },
            {
                "project": "remote",
                "state": "unreachable",
                "type": "remote",
                "mount": "stale",
                "tmux": "-",
                "git": "-",
            },
        ],
    }
    mock_collect.assert_called_once_with(m)


def test_vault_endpoints_use_services(client: TestClient) -> None:
    # ケース10
    m = manifest()
    tree = [
        VaultNode(
            name="mind",
            path="mind",
            type="directory",
            children=[VaultNode(name="idea.md", path="mind/idea.md", type="file")],
        ),
    ]
    with (
        patch("whub.webapp.routers.vault.load_manifest", return_value=m),
        patch(
            "whub.webapp.routers.vault.list_vault_tree",
            return_value=tree,
        ) as mock_tree,
        patch(
            "whub.webapp.routers.vault.read_vault_note",
            return_value="# idea\n",
        ) as mock_read,
    ):
        tree_response = client.get("/api/vault/tree")
        note_response = client.get("/api/vault/note", params={"path": "mind/idea.md"})

    assert tree_response.status_code == 200
    assert tree_response.json() == {
        "nodes": [
            {
                "name": "mind",
                "path": "mind",
                "type": "directory",
                "children": [
                    {
                        "name": "idea.md",
                        "path": "mind/idea.md",
                        "type": "file",
                        "children": [],
                    },
                ],
            },
        ],
    }
    mock_tree.assert_called_once_with(m)
    assert note_response.status_code == 200
    assert note_response.json() == {"path": "mind/idea.md", "content": "# idea\n"}
    mock_read.assert_called_once_with(m, "mind/idea.md")


def test_get_knowledge_uses_service_and_maps_missing_to_404(
    client: TestClient,
) -> None:
    # ケース11
    m = manifest()
    with (
        patch("whub.webapp.routers.knowledge.load_manifest", return_value=m),
        patch(
            "whub.webapp.routers.knowledge.load_project_knowledge",
            return_value=knowledge(),
        ) as mock_load,
    ):
        response = client.get("/api/knowledge/local")

    assert response.status_code == 200
    assert response.json()["definitions"][0]["id"] == "DEF-001"
    assert response.json()["relation_types"][0]["name"] == "manages"
    assert response.json()["constraints"][0]["id"] == "CON-001"
    mock_load.assert_called_once_with(m, "local")

    with patch(
        "whub.webapp.routers.knowledge.load_project_knowledge",
        side_effect=NotFoundError("knowledge file not found"),
    ):
        missing_response = client.get("/api/knowledge/local")

    assert missing_response.status_code == 404
    assert missing_response.json() == {"detail": "knowledge file not found"}


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
