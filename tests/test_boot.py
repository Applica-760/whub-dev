from __future__ import annotations

import importlib
import json
import tempfile
import unittest
from importlib.resources import files
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from click.testing import CliRunner


boot_module = importlib.import_module("whub.commands.boot")


class BootTest(unittest.TestCase):
    def _manifest(self, root: Path, *resources) -> SimpleNamespace:
        return SimpleNamespace(
            root=root,
            resources=list(resources),
            resolve_path=lambda relative: root / relative,
            hosts={},
        )

    def test_real_deploy_is_idempotent_and_preserves_project_content(self) -> None:
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

            source = files("whub").joinpath("boot")
            boot_module._deploy_local(source, target, codegraph=None)
            first = {
                path.relative_to(target): path.read_bytes()
                for path in target.rglob("*") if path.is_file()
            }
            boot_module._deploy_local(source, target, codegraph=None)
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

    def test_codegraph_failure_does_not_stop_later_targets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "project").mkdir()
            events = []
            manifest = self._manifest(
                root,
                SimpleNamespace(name="project", path="project", boot=True),
            )

            def deploy(_source, _target, codegraph=None):
                events.append(("deploy", _target))
                return None, "failed" if _target == root / "project" else None

            with (
                patch.object(boot_module.shutil, "which", return_value="/bin/codegraph"),
                patch.object(boot_module, "_deploy_local", side_effect=deploy),
            ):
                result = CliRunner().invoke(
                    boot_module.boot,
                    obj={"manifest": manifest},
                )

            self.assertEqual(result.exit_code, 0)
            self.assertEqual(events, [
                ("deploy", root),
                ("deploy", root / "project"),
            ])
            self.assertIn("CodeGraph init failed: failed", result.output)

    def test_missing_codegraph_warns_once_and_keeps_deploying(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "project").mkdir()
            manifest = self._manifest(
                root,
                SimpleNamespace(name="project", path="project", boot=True),
            )

            with (
                patch.object(boot_module.shutil, "which", return_value=None),
                patch.object(boot_module, "_deploy_local", return_value=(None, False)) as deploy,
            ):
                result = CliRunner().invoke(
                    boot_module.boot,
                    obj={"manifest": manifest},
                )

            self.assertEqual(result.exit_code, 0)
            self.assertEqual(deploy.call_count, 2)
            self.assertEqual(result.output.count("codegraph not found"), 1)

    def test_rejects_invalid_managed_markers(self) -> None:
        markers = ("<!-- hub:managed:start -->", "<!-- hub:managed:end -->")
        existing = "<!-- hub:managed:start -->\nmissing end\n"
        new = "<!-- hub:managed:start -->\nnew\n<!-- hub:managed:end -->\n"
        with self.assertRaisesRegex(ValueError, "duplicate or unpaired"):
            boot_module._merge_section(new, existing, markers)


if __name__ == "__main__":
    unittest.main()
