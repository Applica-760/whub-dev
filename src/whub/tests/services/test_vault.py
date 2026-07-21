"""Vault service behavior tests.

検証するケース:
1. ツリーが.mdのみを含み、ディレクトリ優先・名前順で返る。
2. 隠しディレクトリと、mdを含まないディレクトリを除外する。
3. ノート本文を無加工で返す。
4. vault外へ出るパス・md以外・不在ノートをNotFoundErrorで拒否する。
5. vault projectの未定義・未linkを拒否する。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from whub.models import Manifest
from whub.services.errors import NotFoundError, ServiceError
from whub.services.vault import list_vault_tree, read_vault_note
from whub.tests.helpers import manifest, manifest_data


def _vault_manifest(tmp_path: Path) -> tuple[Manifest, Path]:
    source = tmp_path / "vault-source"
    source.mkdir()
    data = manifest_data()
    data["projects"].append(
        {
            "name": "vault",
            "resource": {
                "type": "symlink",
                "workspace_path": "vault",
                "source": str(source),
            },
        }
    )
    result = Manifest.model_validate(data)
    project = result.resolve_project("vault")
    assert project is not None
    assert project.resource is not None
    workspace_path = tmp_path / "vault"
    workspace_path.symlink_to(source, target_is_directory=True)
    project.resource._resolved_workspace_path = workspace_path
    return result, workspace_path


def test_list_vault_tree_returns_md_only_directories_first(tmp_path: Path) -> None:
    # ケース1
    vault_manifest, vault_path = _vault_manifest(tmp_path)
    (vault_path / "zeta.md").write_text("z")
    (vault_path / "core.md").write_text("c")
    (vault_path / "notes.txt").write_text("ignored")
    (vault_path / "mind").mkdir()
    (vault_path / "mind" / "idea.md").write_text("i")

    nodes = list_vault_tree(vault_manifest)

    assert [(node.type, node.name) for node in nodes] == [
        ("directory", "mind"),
        ("file", "core.md"),
        ("file", "zeta.md"),
    ]
    assert [child.path for child in nodes[0].children] == ["mind/idea.md"]


def test_list_vault_tree_skips_hidden_and_empty_directories(tmp_path: Path) -> None:
    # ケース2
    vault_manifest, vault_path = _vault_manifest(tmp_path)
    (vault_path / ".git").mkdir()
    (vault_path / ".git" / "config.md").write_text("hidden")
    (vault_path / "assets").mkdir()
    (vault_path / "assets" / "image.png").write_text("binary")
    (vault_path / "inbox").mkdir()
    (vault_path / "inbox" / "note.md").write_text("n")

    nodes = list_vault_tree(vault_manifest)

    assert [node.name for node in nodes] == ["inbox"]


def test_read_vault_note_returns_raw_content(tmp_path: Path) -> None:
    # ケース3
    vault_manifest, vault_path = _vault_manifest(tmp_path)
    (vault_path / "mind").mkdir()
    (vault_path / "mind" / "idea.md").write_text("# raw\nbody\n")

    assert read_vault_note(vault_manifest, "mind/idea.md") == "# raw\nbody\n"


@pytest.mark.parametrize(
    "path",
    [
        "../outside.md",
        "/etc/passwd",
        "notes.txt",
        "missing.md",
    ],
)
def test_read_vault_note_rejects_invalid_paths(tmp_path: Path, path: str) -> None:
    # ケース4
    vault_manifest, vault_path = _vault_manifest(tmp_path)
    (tmp_path / "outside.md").write_text("secret")
    (vault_path / "notes.txt").write_text("plain")

    with pytest.raises(NotFoundError, match="vault note not found"):
        read_vault_note(vault_manifest, path)


def test_vault_services_reject_missing_vault_project() -> None:
    # ケース5
    with pytest.raises(ServiceError, match="vault project is not defined"):
        list_vault_tree(manifest())


def test_vault_services_reject_unlinked_vault(tmp_path: Path) -> None:
    # ケース5
    vault_manifest, vault_path = _vault_manifest(tmp_path)
    vault_path.unlink()

    with pytest.raises(ServiceError, match="vault workspace path is not available"):
        read_vault_note(vault_manifest, "core.md")
