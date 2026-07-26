"""Project-scoped Task service tests.

検証するケース:
1. local Projectのtask一覧・詳細と、task不在・resource未整備の区別
2. remote Projectがmountを参照せず、ssh 1往復で得たtarの展開結果から一覧・詳細を返す
3. 同一内容ならlocalとremoteでTaskSummary・TaskDocumentが一致する
4. remoteのdocs/tasks不在は一覧が空になり、詳細はNotFoundErrorになる
5. ssh失敗とtar展開失敗のServiceErrorが、Project単位で隔離される
6. local task rootがdirectoryでない場合のServiceError
7. resourceを持たないProjectのServiceError
8. 同一hostの接続失敗は1回だけ試行し、同じhostの残りProjectは再接続せず同じ理由で失敗する
"""

from __future__ import annotations

import io
from pathlib import Path
from subprocess import CompletedProcess
import tarfile
from unittest.mock import patch

import pytest
import yaml

from whub.models import Manifest
from whub.services.errors import NotFoundError, ServiceError
from whub.services.task import (
    list_all_project_tasks,
    list_project_tasks,
    load_project_task,
    render_project_task_flow,
    resolve_project_task_root,
)
from whub.tests.helpers import manifest_data


def _write_task(root: Path, task_id: str, title: str) -> None:
    task_root = root / "docs" / "tasks"
    task_root.mkdir(parents=True, exist_ok=True)
    (task_root / f"{task_id.lower()}.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "task": {
                    "id": task_id,
                    "state": "draft",
                    "title": title,
                    "objective": f"Complete {title}",
                },
            },
            allow_unicode=True,
            sort_keys=False,
        ),
    )


def _tar_bytes(root: Path) -> bytes:
    """root/docs/tasksを、remote hostのtar出力と同じ相対path構成で固める。"""
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as archive:
        archive.add(root / "docs" / "tasks", arcname="docs/tasks")
    return buffer.getvalue()


def _ssh_result(
    stdout: bytes = b"",
    returncode: int = 0,
    stderr: bytes = b"",
) -> CompletedProcess[bytes]:
    return CompletedProcess([], returncode, stdout=stdout, stderr=stderr)


def test_lists_tasks_from_local_and_remote_projects(tmp_path: Path) -> None:
    # ケース1, ケース2
    data = manifest_data()
    local_root = tmp_path / "local-source"
    data["projects"][0]["resource"]["source"] = str(local_root)
    _write_task(local_root, "TASK-001", "Local")
    remote_source = tmp_path / "remote-source"
    _write_task(remote_source, "TASK-001", "Remote")
    loaded_manifest = Manifest.model_validate(data)

    assert list_project_tasks(loaded_manifest, "local")[0].title == "Local"

    # remoteのmount pathが存在しなくても読める＝mountを参照していない
    assert not (tmp_path / "projects" / "remote").exists()
    with patch(
        "whub.services.task.run_ssh_command_bytes",
        return_value=_ssh_result(stdout=_tar_bytes(remote_source)),
    ) as mock_ssh:
        assert list_project_tasks(loaded_manifest, "remote")[0].title == "Remote"

    assert mock_ssh.call_count == 1
    command = mock_ssh.call_args.args[1]
    assert "tar cf - -- docs/tasks" in command


def test_local_and_remote_return_the_same_task_records(tmp_path: Path) -> None:
    # ケース3
    data = manifest_data()
    local_root = tmp_path / "local-source"
    data["projects"][0]["resource"]["source"] = str(local_root)
    _write_task(local_root, "TASK-001", "Shared")
    loaded_manifest = Manifest.model_validate(data)

    with patch(
        "whub.services.task.run_ssh_command_bytes",
        return_value=_ssh_result(stdout=_tar_bytes(local_root)),
    ):
        assert list_project_tasks(loaded_manifest, "remote") == list_project_tasks(
            loaded_manifest,
            "local",
        )
        assert load_project_task(
            loaded_manifest,
            "remote",
            "TASK-001",
        ) == load_project_task(loaded_manifest, "local", "TASK-001")


def test_missing_remote_task_directory_yields_empty_result(tmp_path: Path) -> None:
    # ケース4
    loaded_manifest = Manifest.model_validate(manifest_data())

    with patch(
        "whub.services.task.run_ssh_command_bytes",
        return_value=_ssh_result(),
    ):
        assert list_project_tasks(loaded_manifest, "remote") == ()
        with pytest.raises(NotFoundError, match="task not found: remote/TASK-001"):
            load_project_task(loaded_manifest, "remote", "TASK-001")


def test_reports_remote_read_failures_and_isolates_projects(tmp_path: Path) -> None:
    # ケース5
    data = manifest_data()
    local_root = tmp_path / "local-source"
    data["projects"][0]["resource"]["source"] = str(local_root)
    _write_task(local_root, "TASK-001", "Local")
    loaded_manifest = Manifest.model_validate(data)

    with patch(
        "whub.services.task.run_ssh_command_bytes",
        return_value=_ssh_result(returncode=1, stderr=b"No such file or directory\n"),
    ) as mock_ssh:
        with pytest.raises(
            ServiceError,
            match="remote task read failed: remote: No such file or directory",
        ):
            list_project_tasks(loaded_manifest, "remote")

        results = {
            item.project: item for item in list_all_project_tasks(loaded_manifest)
        }

    # 接続失敗でないerrorは使い回さず、remoteとnestedの双方を試行する
    assert mock_ssh.call_count == 3

    # 1つのProjectが読めなくても他Projectの結果は失われない
    assert [task.title for task in results["local"].tasks] == ["Local"]
    assert results["local"].error is None
    assert results["remote"].tasks == ()
    assert "remote task read failed: remote" in (results["remote"].error or "")

    with patch(
        "whub.services.task.run_ssh_command_bytes",
        return_value=_ssh_result(stdout=b"not a tar archive"),
    ):
        with pytest.raises(ServiceError, match="remote task read failed: remote"):
            list_project_tasks(loaded_manifest, "remote")


def test_reuses_one_connection_failure_for_the_same_host(tmp_path: Path) -> None:
    # ケース8
    data = manifest_data()
    local_root = tmp_path / "local-source"
    data["projects"][0]["resource"]["source"] = str(local_root)
    _write_task(local_root, "TASK-001", "Local")
    loaded_manifest = Manifest.model_validate(data)
    unreachable = b"ssh: connect to host home.example.com port 2222: Host is down\n"

    with patch(
        "whub.services.task.run_ssh_command_bytes",
        return_value=_ssh_result(returncode=255, stderr=unreachable),
    ) as mock_ssh:
        results = {
            item.project: item for item in list_all_project_tasks(loaded_manifest)
        }

    # 同一hostのremote・nestedに対して接続試行は1回だけ
    assert mock_ssh.call_count == 1
    detail = unreachable.decode().strip()
    assert results["remote"].error == f"remote task read failed: remote: {detail}"
    assert results["nested"].error == f"remote task read failed: nested: {detail}"
    assert [task.title for task in results["local"].tasks] == ["Local"]


def test_resolves_task_root_and_rejects_non_directory(tmp_path: Path) -> None:
    # ケース6
    data = manifest_data()
    local_root = tmp_path / "local-source"
    local_root.mkdir()
    data["projects"][0]["resource"]["source"] = str(local_root)
    loaded_manifest = Manifest.model_validate(data)

    assert resolve_project_task_root(loaded_manifest, "local") == (
        local_root / "docs/tasks"
    )

    task_path = local_root / "docs/tasks"
    task_path.parent.mkdir()
    task_path.write_text("not a directory")
    with pytest.raises(
        ServiceError,
        match="project task path is not a directory: local",
    ):
        resolve_project_task_root(loaded_manifest, "local")


def test_distinguishes_missing_tasks_from_unavailable_resource(tmp_path: Path) -> None:
    # ケース1, ケース7
    data = manifest_data()
    local_root = tmp_path / "local-source"
    local_root.mkdir()
    data["projects"][0]["resource"]["source"] = str(local_root)
    loaded_manifest = Manifest.model_validate(data)

    assert list_project_tasks(loaded_manifest, "local") == ()
    with pytest.raises(ServiceError, match="project has no resource: no-resource"):
        list_project_tasks(loaded_manifest, "no-resource")


def test_loads_and_renders_one_project_task(tmp_path: Path) -> None:
    # ケース1
    data = manifest_data()
    local_root = tmp_path / "local-source"
    data["projects"][0]["resource"]["source"] = str(local_root)
    _write_task(local_root, "TASK-001", "Local")
    loaded_manifest = Manifest.model_validate(data)

    assert load_project_task(loaded_manifest, "local", "TASK-001").task.title == "Local"
    assert render_project_task_flow(
        loaded_manifest,
        "local",
        "TASK-001",
    ).startswith("flowchart TD")

    with pytest.raises(NotFoundError, match="task not found: local/TASK-999"):
        load_project_task(loaded_manifest, "local", "TASK-999")
