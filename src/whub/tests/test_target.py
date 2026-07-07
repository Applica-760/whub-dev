"""`whub.target`の仕様テスト。

検証するケース:
1. `resolve_project_resource()`は既知projectのresourceを返す。
2. `resolve_project_resource()`は未知projectを拒否する。
3. `resolve_project_resource()`はresourceなしprojectを拒否する。
4. `resolve_resource_by_workspace_path()`は相対パスからresourceとresource内相対パスを返す。
5. `resolve_resource_by_workspace_path()`はネストしたresourceでは最長一致を優先する。
6. `resolve_resource_by_workspace_path()`は絶対パス・`..`・未所属パスを拒否する。
7. `require_resource_type()`は期待型なら返し、不一致なら拒否する。
8. `collect_targets()`はresourceを持つprojectだけを集める。
9. `on_targets()`はsymlinkをlocal関数へ、remoteをremote関数へ振り分ける。

検証しないケース:
1. `assert_never`に到達する不正Resource型。
2. 各コマンド側のエラー表示。
3. 実ファイルや実SSHへの副作用。
"""
from __future__ import annotations

import unittest

from whub.models import RemoteResource, SymlinkResource
from whub.target import (
    TargetError,
    TargetItem,
    collect_targets,
    on_targets,
    require_resource_type,
    resolve_project_resource,
    resolve_resource_by_workspace_path,
)
from whub.tests.helpers import manifest


class TargetSpecTest(unittest.TestCase):
    def test_resolve_project_resource_returns_known_project_resource(self) -> None:
        # ケース1
        resource = resolve_project_resource(manifest(), "local")

        self.assertIsInstance(resource, SymlinkResource)
        self.assertEqual(resource.workspace_path, "projects/local")

    def test_resolve_project_resource_rejects_unknown_project(self) -> None:
        # ケース2
        with self.assertRaisesRegex(TargetError, "unknown project"):
            resolve_project_resource(manifest(), "missing")

    def test_resolve_project_resource_rejects_project_without_resource(self) -> None:
        # ケース3
        with self.assertRaisesRegex(TargetError, "project has no resource"):
            resolve_project_resource(manifest(), "no-resource")

    def test_resolve_resource_by_workspace_path_returns_resource_and_relative_path(self) -> None:
        # ケース4
        project, resource, relative_path = resolve_resource_by_workspace_path(
            manifest(),
            "projects/remote/data/out.nc",
        )

        self.assertEqual(project.name, "remote")
        self.assertIsInstance(resource, RemoteResource)
        self.assertEqual(relative_path, "data/out.nc")

    def test_resolve_resource_by_workspace_path_prefers_longest_match(self) -> None:
        # ケース5
        project, resource, relative_path = resolve_resource_by_workspace_path(
            manifest(),
            "projects/remote/nested/log.txt",
        )

        self.assertEqual(project.name, "nested")
        self.assertIsInstance(resource, RemoteResource)
        self.assertEqual(relative_path, "log.txt")

    def test_resolve_resource_by_workspace_path_rejects_invalid_or_uncontained_paths(self) -> None:
        # ケース6
        for path in (
            "/projects/remote/file.txt",
            "../outside",
            "projects/../outside",
            "unknown/file.txt",
        ):
            with self.subTest(path=path):
                with self.assertRaises(TargetError):
                    resolve_resource_by_workspace_path(manifest(), path)

    def test_require_resource_type_returns_expected_type_and_rejects_mismatch(self) -> None:
        # ケース7
        local = resolve_project_resource(manifest(), "local")
        remote = resolve_project_resource(manifest(), "remote")

        self.assertIs(require_resource_type(local, SymlinkResource, "local"), local)
        with self.assertRaisesRegex(TargetError, "not a remote resource"):
            require_resource_type(local, RemoteResource, "local")
        self.assertIs(require_resource_type(remote, RemoteResource, "remote"), remote)

    def test_collect_targets_includes_only_projects_with_resources(self) -> None:
        # ケース8
        targets = collect_targets(manifest())

        self.assertEqual([target.data.name for target in targets], ["local", "remote", "nested"])

    def test_on_targets_dispatches_by_resource_type(self) -> None:
        # ケース9
        m = manifest()
        local = resolve_project_resource(m, "local")
        remote = resolve_project_resource(m, "remote")
        calls: list[tuple[str, str]] = []

        def handle_local(resource: SymlinkResource, label: str) -> str:
            calls.append(("local", resource.workspace_path))
            return f"local:{label}"

        def handle_remote(resource: RemoteResource, label: str) -> str:
            calls.append(("remote", resource.workspace_path))
            return f"remote:{label}"

        results = on_targets(
            [
                TargetItem(local, "a"),
                TargetItem(remote, "b"),
            ],
            local=handle_local,
            remote=handle_remote,
        )

        self.assertEqual(results, ["local:a", "remote:b"])
        self.assertEqual(calls, [("local", "projects/local"), ("remote", "projects/remote")])


if __name__ == "__main__":
    unittest.main()
