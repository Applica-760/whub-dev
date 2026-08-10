"""Built-in Flow definitions."""

from importlib.resources import as_file, files

from whub.models.flow import WorkflowDefinition
from whub.services.flow.workflow import load_workflow


def task_workflow() -> WorkflowDefinition:
    """Load the built-in Task Flow definition."""
    with as_file(files(__name__).joinpath("task.yaml")) as path:
        return load_workflow(path)
