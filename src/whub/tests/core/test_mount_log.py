"""Mount diagnostic log tests."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from whub.core.mount_log import safe_option_names, write_mount_log


def test_safe_option_names_excludes_secret_values() -> None:
    command = [
        "sshfs",
        "user@secret:/private/path",
        "/mnt/project",
        "-s",
        "-o",
        "IdentityFile=/Users/secret/.ssh/id_rsa",
        "-o",
        "reconnect",
        "-o",
        "port=22",
    ]

    assert safe_option_names(command) == ["-s", "reconnect", "port"]


def test_mount_log_rotates_to_bounded_jsonl(tmp_path: Path) -> None:
    with (
        patch(
            "whub.core.mount_log.current_context",
            return_value=SimpleNamespace(directory=tmp_path),
        ),
        patch(
            "whub.core.mount_log.current_release",
            return_value=SimpleNamespace(release_id="0.1.0+gtest"),
        ),
    ):
        for index in range(105):
            write_mount_log(
                project=f"project-{index}",
                mountpoint=Path("/mnt/project"),
                stage="precheck",
                result="ok",
            )

    path = tmp_path / "runtime" / "logs" / "mount.jsonl"
    records = [json.loads(line) for line in path.read_text().splitlines()]
    assert len(records) == 100
    assert records[0]["project"] == "project-5"
    assert records[-1]["version"] == "0.1.0+gtest"
