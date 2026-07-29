"""Read-only worktree status projection tests."""

from pathlib import Path
from unittest.mock import patch

from whub.models import WorktreeDefinition, WorktreeDefinitionRecord, WorktreeInspection
from whub.services.worktree.status import collect_worktree_status
from whub.tests.helpers import manifest


def _definition() -> WorktreeDefinition:
    return WorktreeDefinition(
        task_id="TASK-072",
        parent_project="local",
        branch="tasks/072",
        workspace_path="projects/worktrees/local-072",
    )


def _inspection(
    tmp_path: Path,
    definition: WorktreeDefinition | None,
    diagnostics: tuple[str, ...] = (),
) -> WorktreeInspection:
    return WorktreeInspection(
        WorktreeDefinitionRecord(tmp_path / "local-072.yaml", definition, diagnostics),
        diagnostics,
    )


def test_collect_worktree_status_projects_definition_and_diagnostics(
    tmp_path: Path,
) -> None:
    inspections = [
        _inspection(tmp_path, _definition()),
        _inspection(
            tmp_path,
            _definition(),
            ("git worktree is missing: projects/worktrees/local-072",),
        ),
        _inspection(
            tmp_path, None, ("invalid worktree definition YAML: invalid.yaml",)
        ),
    ]
    with patch(
        "whub.services.worktree.status.inspect_worktrees", return_value=inspections
    ) as inspect:
        statuses = collect_worktree_status(manifest(), tmp_path)

    inspect.assert_called_once_with(manifest(), tmp_path)
    assert statuses[0].parent_project == "local"
    assert statuses[0].task_id == "TASK-072"
    assert statuses[0].branch == "tasks/072"
    assert statuses[0].workspace_path == "projects/worktrees/local-072"
    assert statuses[0].diagnostics == ()
    assert statuses[1].diagnostics == (
        "git worktree is missing: projects/worktrees/local-072",
    )
    assert statuses[2].parent_project is None
    assert statuses[2].workspace_path is None
    assert statuses[2].diagnostics == (
        "invalid worktree definition YAML: invalid.yaml",
    )
