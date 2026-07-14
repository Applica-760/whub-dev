"""Loader for declarative Workflow definitions."""
from pathlib import Path

import yaml
from pydantic import ValidationError

from whub.wflow.workflow.models import WorkflowDefinition


class WorkflowError(Exception):
    """Raised when Workflow YAML cannot be loaded or validated."""


def load_workflow(path: Path) -> WorkflowDefinition:
    try:
        data = yaml.safe_load(path.read_text())
        return WorkflowDefinition.model_validate(data)
    except (OSError, yaml.YAMLError, ValidationError) as error:
        raise WorkflowError(f"failed to load Workflow YAML: {path}: {error}") from error
