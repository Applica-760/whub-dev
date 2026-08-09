"""S2b web API tests.

検証するケース:
1. todo一覧がserviceの表示順で返る。
2. todoの追加・完了・削除がserviceを呼び、仕様どおり応答する。
3. todo完了はdone=trueだけを受理する。
4. project一覧がmanifestの名前だけを返す。
5. backlogの読取・追記がserviceを呼ぶ。
6. 空白だけのbacklog memoを拒否する。
7. inbox投函が作成ファイル名を返す。
8. Daily追記が相対パスを返す。
9. ServiceError系とManifestErrorをHTTPエラーへ変換する。
10. resource statusがserviceの結果を返す。
11. vaultのツリー取得・ノート取得がserviceを呼ぶ。
"""

from __future__ import annotations

import asyncio
from datetime import date
from pathlib import Path, PurePosixPath
from types import SimpleNamespace
from unittest.mock import Mock, call, patch

import pytest
from fastapi import WebSocketDisconnect
from fastapi.testclient import TestClient

from whub.models import ManifestError
from whub.models.flow import TaskRuntime
from whub.models.todo import Todo
from whub.services.errors import NotFoundError, ServiceError
from whub.services.agent.codex.attention import ApprovalAttentionStore
from whub.models import ResourceStatus, WorktreeStatus
from whub.models.operator_terminal import OperatorTerminal, OperatorTerminals
from whub.services.task.project import ProjectTasks, TaskRecord, TaskSummary
from whub.services.vault import VaultNode
from whub.services.worktree.diff import ChangedFile, WorktreeDiff
from whub.tests.helpers import manifest
from whub.webapp.routers import agent_attention
from whub.webapp.server import create_app


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    (dist_dir / "index.html").write_text("<main>whub</main>")
    return TestClient(create_app(dist_dir))


def test_attention_stream_pushes_updates_and_releases_disconnected_clients() -> None:
    class WebSocket:
        headers = {"host": "localhost"}

        def __init__(self) -> None:
            self.messages: asyncio.Queue[object] = asyncio.Queue()
            self.sent: list[dict[str, str]] = []
            self.accepted = False

        async def accept(self) -> None:
            self.accepted = True

        async def receive(self) -> object:
            message = await self.messages.get()
            if isinstance(message, Exception):
                raise message
            return message

        async def send_json(self, message: dict[str, str]) -> None:
            self.sent.append(message)

    async def exercise() -> None:
        websocket = WebSocket()
        with patch("whub.webapp.routers.agent_attention._subscribers", set()):
            stream = asyncio.create_task(agent_attention.attention_stream(websocket))
            await asyncio.sleep(0)
            await agent_attention._publish("response_completed")
            assert websocket.accepted
            assert websocket.sent == [
                {"type": "attention_updated", "event": "response_completed"}
            ]
            await websocket.messages.put(WebSocketDisconnect())
            await stream

    asyncio.run(exercise())


def test_attention_publish_tolerates_subscriber_disconnect_during_send() -> None:
    class WebSocket:
        def __init__(self) -> None:
            self.sent: list[dict[str, str]] = []

        async def send_json(self, message: dict[str, str]) -> None:
            sending.append(self)
            started.set()
            await release.wait()
            self.sent.append(message)

    async def exercise() -> None:
        first = WebSocket()
        second = WebSocket()
        subscribers = {first, second}
        with patch("whub.webapp.routers.agent_attention._subscribers", subscribers):
            publishing = asyncio.create_task(agent_attention._publish())
            await started.wait()
            disconnected = next(
                subscriber for subscriber in subscribers if subscriber is not sending[0]
            )
            subscribers.discard(disconnected)
            release.set()
            await publishing

        assert first.sent == [{"type": "attention_updated"}]
        assert second.sent == [{"type": "attention_updated"}]

    started = asyncio.Event()
    release = asyncio.Event()
    sending: list[WebSocket] = []
    asyncio.run(exercise())


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


def test_agent_attention_has_no_external_event_producer(client: TestClient) -> None:
    store = ApprovalAttentionStore()
    store.request("whub-dev", "TASK-104", "Bash", "turn-1")

    with patch("whub.webapp.routers.agent_attention.attention", store):
        listed = client.get("/api/agent-attention")
        acknowledged = client.post("/api/agent-attention/whub-dev/TASK-104/acknowledge")

    assert client.post("/api/agent-attention", json={}).status_code == 405
    assert listed.json()["attention"][0]["acknowledged"] is False
    assert acknowledged.json()[0]["acknowledged"] is True


def test_hook_events_require_localhost_and_an_exact_registered_worktree(
    client: TestClient, tmp_path: Path
) -> None:
    body = {
        "hook_event_name": "PermissionRequest",
        "session_id": "session-1",
        "cwd": "/workspace/projects/worktrees/whub-dev-104",
        "turn_id": "turn-1",
        "tool_name": "Bash",
    }
    assert client.post("/api/agent-attention/events", json=body).status_code == 403

    store = ApprovalAttentionStore()
    local_client = TestClient(client.app, client=("127.0.0.1", 50000))
    context = Mock(workspace_root=Path("/workspace"))
    inspection = SimpleNamespace(
        definition=SimpleNamespace(
            parent_project="whub-dev",
            task_id="TASK-104",
            workspace_path="projects/worktrees/whub-dev-104",
        ),
        diagnostics=(),
    )
    with (
        patch(
            "whub.webapp.routers.agent_attention.current_context",
            return_value=context,
        ),
        patch("whub.webapp.routers.agent_attention.load_manifest"),
        patch(
            "whub.webapp.routers.agent_attention.inspect_worktrees",
            return_value=[inspection],
        ),
        patch("whub.webapp.routers.agent_attention.attention", store),
    ):
        assert (
            local_client.post("/api/agent-attention/events", json=body).status_code
            == 204
        )
        assert len(store.list()) == 1
        body["hook_event_name"] = "Stop"
        body.pop("tool_name")
        assert (
            local_client.post("/api/agent-attention/events", json=body).status_code
            == 204
        )
        assert len(store.list()) == 2
        body["hook_event_name"] = "PostToolUse"
        body["tool_name"] = "Bash"
        assert (
            local_client.post("/api/agent-attention/events", json=body).status_code
            == 204
        )
        assert [item.event for item in store.list()] == ["response_completed"]
        body["cwd"] = "/workspace/projects/worktrees/not-registered"
        assert (
            local_client.post("/api/agent-attention/events", json=body).status_code
            == 404
        )
        body.pop("tool_name")
        assert (
            local_client.post("/api/agent-attention/events", json=body).status_code
            == 422
        )

    assert [item.event for item in store.list()] == ["response_completed"]


def test_hook_events_identify_an_active_operator_by_immutable_id(
    client: TestClient,
) -> None:
    body = {
        "hook_event_name": "PermissionRequest",
        "session_id": "session-1",
        "cwd": "/workspace",
        "turn_id": "turn-1",
        "tool_name": "Bash",
        "operator_id": "operator-3",
    }
    store = ApprovalAttentionStore()
    local_client = TestClient(client.app, client=("127.0.0.1", 50000))
    with (
        patch("whub.webapp.routers.agent_attention.attention", store),
        patch("whub.webapp.routers.agent_attention.operator_terminal.resolve"),
    ):
        assert (
            local_client.post("/api/agent-attention/events", json=body).status_code
            == 204
        )
        body["hook_event_name"] = "Stop"
        body.pop("tool_name")
        assert (
            local_client.post("/api/agent-attention/events", json=body).status_code
            == 204
        )
        acknowledged = local_client.post(
            "/api/agent-attention/operator/operator-3/acknowledge"
        )

    assert {item["event"] for item in acknowledged.json()} == {
        "permission_request",
        "response_completed",
    }
    assert all(item["operator_id"] == "operator-3" for item in acknowledged.json())


def test_agent_codex_session_is_owned_by_the_local_web_backend(
    client: TestClient, tmp_path: Path
) -> None:
    assert client.post("/api/agent-codex/whub-dev/TASK-104/session").status_code == 403

    dist_dir = tmp_path / "local-dist"
    dist_dir.mkdir()
    (dist_dir / "index.html").write_text("<main>whub</main>")
    local_client = TestClient(create_app(dist_dir), client=("127.0.0.1", 50000))
    context = Mock(workspace_root=tmp_path)
    registered = SimpleNamespace(destination=Path("/workspace/worktree"))
    with (
        patch(
            "whub.webapp.routers.agent_codex.current_context",
            return_value=context,
        ),
        patch(
            "whub.webapp.routers.agent_codex.load_manifest",
            return_value=manifest(),
        ),
        patch(
            "whub.webapp.routers.agent_codex.resolve_project_worktree",
            return_value=registered,
        ),
        patch("whub.webapp.routers.agent_codex.app_servers.open") as open_server,
        patch("whub.webapp.routers.agent_codex.app_servers.close") as close_server,
    ):
        assert (
            local_client.post("/api/agent-codex/whub-dev/TASK-104/session").status_code
            == 204
        )
        assert (
            local_client.delete(
                "/api/agent-codex/whub-dev/TASK-104/session"
            ).status_code
            == 204
        )

    open_server.assert_called_once_with(
        "whub-dev", "TASK-104", Path("/workspace/worktree")
    )
    close_server.assert_called_once_with("whub-dev", "TASK-104")


def test_agent_codex_state_returns_app_server_errors(client: TestClient) -> None:
    session = Mock()
    session.snapshot.return_value = {
        "thread_id": None,
        "active_turn_id": None,
        "messages": [],
        "approvals": [],
        "error": "Codex App Server returned invalid JSON",
    }

    with patch("whub.webapp.routers.agent_codex.app_servers.get", return_value=session):
        response = client.get("/api/agent-codex/whub-dev/TASK-104")

    assert response.status_code == 200
    assert response.json()["error"] == "Codex App Server returned invalid JSON"


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


def test_operator_terminal_endpoints_delegate_to_its_lifecycle_service(
    client: TestClient, tmp_path: Path
) -> None:
    running = OperatorTerminal(operator_id="operator-1")
    listed = OperatorTerminals(terminals=[running])
    context = Mock(workspace_root=tmp_path)
    with (
        patch(
            "whub.webapp.routers.operator_terminal.operator_terminal.list",
            return_value=listed,
        ) as mock_list,
        patch(
            "whub.webapp.routers.operator_terminal.operator_terminal.start",
            return_value=running,
        ) as mock_start,
        patch(
            "whub.webapp.routers.operator_terminal.operator_terminal.stop",
            return_value=OperatorTerminals(terminals=[]),
        ) as mock_stop,
        patch(
            "whub.webapp.routers.operator_terminal.current_context",
            return_value=context,
        ),
    ):
        get_response = client.get("/api/operator-terminals")
        start_response = client.post("/api/operator-terminals")
        stop_response = client.delete("/api/operator-terminals/operator-1")

    assert get_response.json() == {"terminals": [{"operator_id": "operator-1"}]}
    assert start_response.status_code == 201
    assert start_response.json() == {"operator_id": "operator-1"}
    assert stop_response.status_code == 204
    mock_list.assert_called_once_with(context)
    mock_start.assert_called_once_with(context)
    mock_stop.assert_called_once_with(context, "operator-1")


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


def test_create_daily_entry_returns_relative_path(client: TestClient) -> None:
    m = manifest()
    path = Path("/tmp/vault/daily/2026-07-28.md")
    with (
        patch("whub.webapp.routers.daily.load_manifest", return_value=m),
        patch(
            "whub.webapp.routers.daily.append_daily_entry",
            return_value=path,
        ) as mock_append,
    ):
        response = client.post("/api/daily", json={"body": "body", "energy": 4})

    assert response.status_code == 201
    assert response.json() == {"path": "daily/2026-07-28.md"}
    mock_append.assert_called_once_with(m, "body", 4)


def test_create_daily_entry_rejects_out_of_range_energy(client: TestClient) -> None:
    response = client.post("/api/daily", json={"body": "body", "energy": 6})

    assert response.status_code == 422


def test_create_daily_entry_returns_service_error_for_blank_body(
    client: TestClient,
) -> None:
    with (
        patch("whub.webapp.routers.daily.load_manifest", return_value=manifest()),
        patch(
            "whub.webapp.routers.daily.append_daily_entry",
            side_effect=ServiceError("daily body is required"),
        ),
    ):
        response = client.post("/api/daily", json={"body": " \n"})

    assert response.status_code == 400
    assert response.json() == {"detail": "daily body is required"}


def test_task_endpoints_return_task_query_results(client: TestClient) -> None:
    summary = TaskSummary(
        path="20260715_task.yaml",
        id="TASK-003",
        title="Task view",
        state="draft",
        depends_on=[],
        blocked_by=[],
        ready=True,
    )
    document = TaskRecord(
        path="20260715_task.yaml",
        title="Task view",
        task=TaskRuntime(
            schema_version=2,
            id="TASK-003",
            workflow="WF-001",
            state="draft",
        ),
    )
    m = manifest()
    with (
        patch("whub.webapp.routers.tasks.load_manifest", return_value=m),
        patch(
            "whub.webapp.routers.tasks.list_project_tasks",
            return_value=(summary,),
        ) as mock_list,
        patch(
            "whub.webapp.routers.tasks.load_project_task",
            return_value=document,
        ) as mock_load,
    ):
        list_response = client.get("/api/tasks", params={"project": "local"})
        default_response = client.get("/api/tasks")
        detail_response = client.get(
            "/api/tasks/TASK-003",
            params={"project": "local"},
        )

    assert list_response.status_code == 200
    assert list_response.json() == {"tasks": [summary.model_dump()]}
    assert default_response.status_code == 200
    assert mock_list.call_args_list == [
        call(m, "local"),
        call(m, "whub-dev"),
    ]
    assert detail_response.status_code == 200
    assert detail_response.json() == document.model_dump()
    mock_load.assert_called_once_with(m, "local", "TASK-003")


def test_all_tasks_endpoint_returns_per_project_results(client: TestClient) -> None:
    summary = TaskSummary(
        path="20260715_task.yaml",
        id="TASK-001",
        title="Task view",
        state="draft",
        depends_on=[],
        blocked_by=[],
        ready=True,
    )
    m = manifest()
    results = (
        ProjectTasks(project="local", tasks=(summary,)),
        ProjectTasks(project="empty", tasks=()),
        ProjectTasks(project="remote", error="project resource is not available"),
    )
    with (
        patch("whub.webapp.routers.tasks.load_manifest", return_value=m),
        patch(
            "whub.webapp.routers.tasks.list_all_project_tasks",
            return_value=results,
        ) as mock_list_all,
    ):
        response = client.get("/api/tasks/all")

    assert response.status_code == 200
    assert response.json() == {
        "projects": [
            {"project": "local", "tasks": [summary.model_dump()], "error": None},
            {"project": "empty", "tasks": [], "error": None},
            {
                "project": "remote",
                "tasks": [],
                "error": "project resource is not available",
            },
        ],
    }
    mock_list_all.assert_called_once_with(m)


def test_task_flow_graph_endpoint_returns_service_result(client: TestClient) -> None:
    m = manifest()
    with (
        patch("whub.webapp.routers.tasks.load_manifest", return_value=m),
        patch(
            "whub.webapp.routers.tasks.render_project_task_flow",
            return_value="flowchart TD\n  phase_001",
        ) as mock_flow_graph,
    ):
        flow_response = client.get(
            "/api/tasks/TASK-003/graph",
            params={"project": "local"},
        )

    assert flow_response.status_code == 200
    assert flow_response.json() == {"mermaid": "flowchart TD\n  phase_001"}
    mock_flow_graph.assert_called_once_with(m, "local", "TASK-003")


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


def test_get_worktrees_returns_worktree_status_entries(
    client: TestClient, tmp_path: Path
) -> None:
    m = manifest()
    worktree = WorktreeStatus(
        "local", "TASK-075", "tasks/075", "projects/worktrees/local-075"
    )
    with (
        patch("whub.webapp.routers.worktrees.load_manifest", return_value=m),
        patch(
            "whub.webapp.routers.worktrees.current_context",
            return_value=type("Context", (), {"workspace_root": tmp_path})(),
        ),
        patch(
            "whub.webapp.routers.worktrees.collect_worktree_status",
            return_value=[worktree],
        ) as mock_collect,
    ):
        response = client.get("/api/worktrees")

    assert response.status_code == 200
    assert response.json() == {
        "worktrees": [
            {
                "parent_project": "local",
                "task_id": "TASK-075",
                "branch": "tasks/075",
                "workspace_path": "projects/worktrees/local-075",
                "diagnostics": [],
            }
        ]
    }
    mock_collect.assert_called_once_with(m, tmp_path)


def test_worktree_diff_endpoints_use_registered_worktree_services(
    client: TestClient, tmp_path: Path
) -> None:
    m = manifest()
    files = [ChangedFile(path="src/main.py", status="M")]
    diff = WorktreeDiff(
        path="src/main.py",
        content="new\n",
        diff="@@ -1 +1 @@\n-old\n+new\n",
        state="text",
    )
    context = type("Context", (), {"workspace_root": tmp_path})()
    with (
        patch("whub.webapp.routers.worktree_diff.load_manifest", return_value=m),
        patch(
            "whub.webapp.routers.worktree_diff.current_context", return_value=context
        ),
        patch(
            "whub.webapp.routers.worktree_diff.list_changed_files", return_value=files
        ) as mock_files,
        patch(
            "whub.webapp.routers.worktree_diff.generated_paths",
            return_value={PurePosixPath("src/main.py")},
        ) as mock_generated,
        patch(
            "whub.webapp.routers.worktree_diff.read_changed_file_diff",
            return_value=diff,
        ) as mock_diff,
    ):
        files_response = client.get("/api/worktrees/local/TASK-072/changes")
        diff_response = client.get(
            "/api/worktrees/local/TASK-072/diff", params={"path": "src/main.py"}
        )

    assert files_response.json() == {
        "files": [
            {
                "path": "src/main.py",
                "status": "M",
                "previous_path": None,
                "agent_generated": True,
            }
        ]
    }
    assert diff_response.json() == {
        "path": "src/main.py",
        "content": diff.content,
        "diff": diff.diff,
        "state": diff.state,
    }
    mock_files.assert_called_once_with(m, tmp_path, "local", "TASK-072")
    mock_generated.assert_called_once_with(m, tmp_path, "local", "TASK-072")
    mock_diff.assert_called_once_with(m, tmp_path, "local", "TASK-072", "src/main.py")


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
