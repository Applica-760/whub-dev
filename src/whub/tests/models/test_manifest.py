"""`whub.models.manifest`の仕様テスト。

検証するケース:
1. `project`は`name`だけで成立し、`resource`なしを許容する。
2. `symlink` resourceは相対`workspace_path`と絶対`source`を要求する。
3. `remote` resourceは相対`workspace_path`、絶対`path`、既知の`host`を要求する。
4. `project.name`の重複を拒否する。
5. `resource.workspace_path`の重複を拒否する。
6. legacy形式や未知フィールドを拒否する。
7. validation後、resourceの解決済み属性を設定する。
8. `load_manifest()`はmanifest欠落・YAML不正・schema不正を`ClickException`にする。

検証しないケース:
1. Pydanticの全エラーメッセージ本文の完全一致。
2. `workspace_path`の全パストラバーサル組み合わせ。
3. `version: 2`の数値coerce許容。
4. `project_names()`の補完挙動。
"""
from __future__ import annotations
import copy
import os
import tempfile
from pathlib import Path
from unittest.mock import patch
import click
import pytest
from pydantic import ValidationError
from whub.models import Manifest, RemoteResource, SymlinkResource, load_manifest
from whub.tests.helpers import manifest_data


class TestManifestSpec:
    def test_project_without_resource_is_valid(self) -> None:
        # ケース1
        manifest = Manifest.model_validate(manifest_data())

        project = manifest.resolve_project("no-resource")
        assert project is not None
        assert project.resource is None

    def test_symlink_resource_requires_safe_workspace_path_and_absolute_source(self) -> None:
        # ケース2
        data = manifest_data()
        assert isinstance(Manifest.model_validate(data).projects[0].resource, SymlinkResource)

        for field, value in (
            ("workspace_path", "/absolute"),
            ("workspace_path", "../outside"),
            ("source", "relative/source"),
            ("source", "~/source"),
        ):
            invalid = copy.deepcopy(data)
            invalid["projects"][0]["resource"][field] = value
            with pytest.raises(ValidationError):
                Manifest.model_validate(invalid)

    def test_remote_resource_requires_safe_workspace_path_absolute_path_and_known_host(self) -> None:
        # ケース3
        data = manifest_data()
        assert isinstance(Manifest.model_validate(data).projects[1].resource, RemoteResource)

        for field, value in (
            ("workspace_path", "/absolute"),
            ("workspace_path", "../outside"),
            ("path", "relative/path"),
            ("path", "~/path"),
            ("host", "missing"),
        ):
            invalid = copy.deepcopy(data)
            invalid["projects"][1]["resource"][field] = value
            with pytest.raises(ValidationError):
                Manifest.model_validate(invalid)

    def test_duplicate_project_names_are_rejected(self) -> None:
        # ケース4
        data = manifest_data()
        data["projects"][1]["name"] = "local"

        with pytest.raises(ValidationError, match="duplicate project names"):
            Manifest.model_validate(data)

    def test_duplicate_workspace_paths_are_rejected(self) -> None:
        # ケース5
        data = manifest_data()
        data["projects"][1]["resource"]["workspace_path"] = "projects/local"

        with pytest.raises(ValidationError, match="duplicate workspace_path"):
            Manifest.model_validate(data)

    def test_legacy_shape_and_unknown_fields_are_rejected(self) -> None:
        # ケース6
        legacy = {
            "version": "1",
            "resources": {
                "symlinks": [
                    {
                        "name": "legacy",
                        "workspace_path": "legacy",
                        "source": "/tmp/legacy",
                    },
                ],
            },
        }
        with pytest.raises(ValidationError):
            Manifest.model_validate(legacy)

        data = manifest_data()
        data["hosts"]["home"]["auto_mount"] = True
        with pytest.raises(ValidationError):
            Manifest.model_validate(data)

    def test_validation_sets_resolved_resource_attributes(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            # ケース7
            with patch.dict(os.environ, {"WHUB_ROOT": root}, clear=True):
                manifest = Manifest.model_validate(manifest_data())

        local = manifest.resolve_project("local").resource
        remote = manifest.resolve_project("remote").resource
        assert local._resolved_workspace_path == Path(root).resolve() / "projects/local"
        assert remote._resolved_workspace_path == Path(root).resolve() / "projects/remote"
        assert remote._resolved_host.hostname == "home.example.com"

    def test_load_manifest_reports_user_facing_errors(self) -> None:
        with tempfile.TemporaryDirectory() as data_dir:
            # ケース8
            with patch.dict(os.environ, {"WHUB_DATA_DIR": data_dir}, clear=True):
                with pytest.raises(click.ClickException, match="manifest.yaml not found"):
                    load_manifest()

            # ケース8
            Path(data_dir, "manifest.yaml").write_text("version: [")
            with patch.dict(os.environ, {"WHUB_DATA_DIR": data_dir}, clear=True):
                with pytest.raises(click.ClickException, match="invalid manifest YAML"):
                    load_manifest()

            # ケース8
            Path(data_dir, "manifest.yaml").write_text(
                "version: '2'\n"
                "projects:\n"
                "- name: broken\n"
                "  resource:\n"
                "    type: symlink\n"
                "    workspace_path: /absolute\n"
                "    source: relative\n"
            )
            with patch.dict(os.environ, {"WHUB_DATA_DIR": data_dir}, clear=True):
                with pytest.raises(click.ClickException, match="invalid manifest"):
                    load_manifest()
