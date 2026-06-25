from __future__ import annotations

import importlib
import json
import subprocess
import tempfile
import unittest
from importlib.resources import as_file, files
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from whub.models import Manifest, SymlinkResource


boot_module = importlib.import_module("whub.commands.boot")


class BootTest(unittest.TestCase):
    def _manifest(
        self,
        root: Path,
        *,
        locals: tuple[str, ...] = (),
        remotes: tuple[str, ...] = (),
    ) -> Manifest:
        manifest = Manifest.model_validate({
            "version": "2",
            "hosts": {
                "server": {
                    "hostname": "example.com",
                    "user": "user",
                    "identity_file": "/tmp/key",
                },
            },
            "projects": [
                {
                    "name": name,
                    "resource": {
                        "type": "symlink",
                        "workspace_path": name,
                        "source": f"/tmp/{name}",
                        "boot": True,
                    },
                }
                for name in locals
            ] + [
                {
                    "name": name,
                    "resource": {
                        "type": "remote",
                        "host": "server",
                        "path": f"/srv/{name}",
                        "boot": True,
                    },
                }
                for name in remotes
            ],
        })
        for project in manifest.projects:
            resource = project.resource
            if isinstance(resource, SymlinkResource):
                resource._resolved_workspace_path = root / resource.workspace_path
        return manifest

    def test_local_apply_is_idempotent_and_preserves_project_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            (target / ".claude/skills/project-only").mkdir(parents=True)
            (target / ".claude/skills/project-only/SKILL.md").write_text("project\n")
            (target / ".claude/CLAUDE.md").write_text("# Project instructions\n")
            (target / "AGENTS.md").write_text(
                "<!-- hub:managed:start -->\nold\n<!-- hub:managed:end -->\n"
                "# Project agents\n",
            )
            (target / ".gitignore").write_text("project-only/\n")
            (target / ".claude/settings.json").write_text(json.dumps({
                "permissions": {"allow": ["ProjectTool"]},
                "hooks": {"Custom": ["keep"], "Stop": ["replace"]},
                "projectSetting": True,
            }))

            with as_file(files("whub").joinpath("boot")) as source:
                boot_module._apply_local_boot(
                    source,
                    [("target", target)],
                    codegraph=None,
                )
                first = {
                    path.relative_to(target): path.read_bytes()
                    for path in target.rglob("*") if path.is_file()
                }
                boot_module._apply_local_boot(
                    source,
                    [("target", target)],
                    codegraph=None,
                )
                second = {
                    path.relative_to(target): path.read_bytes()
                    for path in target.rglob("*") if path.is_file()
                }

            self.assertEqual(first, second)
            self.assertIn(
                "# Project instructions",
                (target / ".claude/CLAUDE.md").read_text(),
            )
            self.assertIn("# Project agents", (target / "AGENTS.md").read_text())
            self.assertIn("project-only/", (target / ".gitignore").read_text())
            self.assertTrue(
                (target / ".claude/skills/project-only/SKILL.md").is_file(),
            )

            settings = json.loads(
                (target / ".claude/settings.json").read_text(),
            )
            self.assertIn("ProjectTool", settings["permissions"]["allow"])
            self.assertEqual(settings["hooks"]["Custom"], ["keep"])
            self.assertTrue(settings["projectSetting"])

            common_skills = {
                path.relative_to(target / ".agents/skills"): path.read_bytes()
                for path in (target / ".agents/skills").rglob("*")
                if path.is_file()
            }
            claude_skills = {
                relative: (target / ".claude/skills" / relative).read_bytes()
                for relative in common_skills
            }
            self.assertEqual(claude_skills, common_skills)
            self.assertTrue((target / ".mcp.json").is_file())
            self.assertTrue((target / ".codex/config.toml").is_file())

    def test_local_codegraph_failure_does_not_stop_later_targets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "first").mkdir()
            (root / "second").mkdir()
            manifest = self._manifest(root, locals=("first", "second"))

            with (
                patch.object(boot_module, "_merged_files", side_effect=lambda *_: iter(())),
                patch.object(boot_module.shutil, "copytree"),
                patch.object(boot_module.shutil, "which", return_value="/bin/codegraph"),
                patch.object(
                    boot_module.subprocess,
                    "run",
                    side_effect=[
                        subprocess.CompletedProcess([], 0),
                        subprocess.CalledProcessError(1, [], stderr="failed"),
                        subprocess.CompletedProcess([], 0),
                    ],
                ) as execute,
            ):
                result = CliRunner().invoke(
                    boot_module.boot,
                    obj={"manifest": manifest},
                )

            self.assertEqual(result.exit_code, 0)
            self.assertEqual(execute.call_count, 3)
            self.assertIn("first: CodeGraph init failed: failed", result.output)
            self.assertIn("second (CodeGraph)", result.output)

    def test_missing_codegraph_warns_once_and_keeps_deploying(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "project").mkdir()
            manifest = self._manifest(root, locals=("project",))

            with (
                patch.object(boot_module, "_merged_files", side_effect=lambda *_: iter(())),
                patch.object(boot_module.shutil, "copytree") as copytree,
                patch.object(boot_module.shutil, "which", return_value=None),
            ):
                result = CliRunner().invoke(
                    boot_module.boot,
                    obj={"manifest": manifest},
                )

            self.assertEqual(result.exit_code, 0)
            self.assertEqual(copytree.call_count, 4)
            self.assertEqual(result.output.count("codegraph not found"), 1)

    def test_remote_codegraph_failure_does_not_stop_later_targets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manifest = self._manifest(
                Path(directory),
                remotes=("first", "second"),
            )
            completed = subprocess.CompletedProcess([], 0, "", "")

            with (
                patch.object(boot_module, "_apply_local_boot"),
                patch.object(boot_module, "_merged_files", side_effect=lambda *_: iter(())),
                patch.object(
                    boot_module,
                    "run_rsync_command",
                    return_value=completed,
                ) as rsync,
                patch.object(
                    boot_module,
                    "run_ssh_command",
                    side_effect=[
                        subprocess.CalledProcessError(1, [], stderr="failed"),
                        completed,
                    ],
                ) as ssh,
            ):
                result = CliRunner().invoke(
                    boot_module.boot,
                    obj={"manifest": manifest},
                )

            self.assertEqual(result.exit_code, 0)
            self.assertEqual(rsync.call_count, 4)
            self.assertEqual(ssh.call_count, 2)
            self.assertIn("first: CodeGraph init failed: failed", result.output)
            self.assertIn("second (CodeGraph)", result.output)

    def test_rejects_invalid_managed_markers(self) -> None:
        markers = ("<!-- hub:managed:start -->", "<!-- hub:managed:end -->")
        existing = "<!-- hub:managed:start -->\nmissing end\n"
        new = "<!-- hub:managed:start -->\nnew\n<!-- hub:managed:end -->\n"
        with self.assertRaisesRegex(ValueError, "duplicate or unpaired"):
            boot_module._merge_section(new, existing, markers)


if __name__ == "__main__":
    unittest.main()
