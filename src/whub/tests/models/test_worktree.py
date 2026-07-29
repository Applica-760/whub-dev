import pytest
from pydantic import ValidationError

from whub.models import WorktreeDefinition


def definition_data() -> dict:
    return {
        "schema_version": 1,
        "task_id": "TASK-072",
        "parent_project": "whub-dev",
        "branch": "tasks/072",
        "workspace_path": "projects/worktrees/whub-dev-072",
    }


def test_worktree_definition_accepts_conventional_identity() -> None:
    definition = WorktreeDefinition.model_validate(definition_data())
    assert definition.task_id == "TASK-072"


@pytest.mark.parametrize("task_id", ["TASK-72", "task-072"])
def test_worktree_definition_rejects_invalid_task_id(task_id: str) -> None:
    data = definition_data()
    data["task_id"] = task_id
    with pytest.raises(ValidationError):
        WorktreeDefinition.model_validate(data)


def test_worktree_definition_accepts_wflow_task_id_with_four_digits() -> None:
    data = definition_data()
    data.update(
        task_id="TASK-1000",
        branch="tasks/1000",
        workspace_path="projects/worktrees/whub-dev-1000",
    )
    definition = WorktreeDefinition.model_validate(data)
    assert definition.task_id == "TASK-1000"


def test_worktree_definition_rejects_unconventional_branch() -> None:
    data = definition_data()
    data["branch"] = "tasks/073"
    with pytest.raises(ValidationError, match="branch must be tasks/072"):
        WorktreeDefinition.model_validate(data)


def test_worktree_definition_rejects_unconventional_workspace_path() -> None:
    data = definition_data()
    data["workspace_path"] = "projects/worktrees/whub-dev-073"
    with pytest.raises(
        ValidationError,
        match="workspace_path must be projects/worktrees/whub-dev-072",
    ):
        WorktreeDefinition.model_validate(data)


def test_worktree_definition_rejects_unknown_fields() -> None:
    data = definition_data()
    data["unknown"] = True
    with pytest.raises(ValidationError):
        WorktreeDefinition.model_validate(data)
