"""Task Mermaid views."""
from __future__ import annotations

import re
from collections.abc import Sequence

from whub.wflow.models.task import TaskDocument, TaskSummary


def render_task_dependency_graph(tasks: Sequence[TaskSummary]) -> str:
    """Render valid Task summaries and their dependencies as Mermaid."""
    valid_tasks = [item for item in tasks if item.id is not None and not item.diagnostics]
    lines = ["flowchart TD"]
    for item in valid_tasks:
        lines.append(f'  {_mermaid_id(item.id)}["{_mermaid_label(item.id, item.title)}"]')
    for item in valid_tasks:
        for dependency in item.depends_on:
            lines.append(f"  {_mermaid_id(dependency)} --> {_mermaid_id(item.id)}")
    return "\n".join(lines)


def render_task_flow(task: TaskDocument) -> str:
    """Render one Task's Phase order and Phase acceptance criteria as Mermaid."""
    lines = ["flowchart TD"]
    if task.plan is None:
        return "\n".join(lines)

    phase_ids: list[str] = []
    for phase_number, phase in enumerate(task.plan.phases, start=1):
        phase_id = f"phase_{phase_number:03}"
        phase_ids.append(phase_id)
        lines.append(
            f'  {phase_id}["{_mermaid_label(f"Phase {phase_number}", phase.title)}"]'
        )
        for criterion in phase.acceptance:
            acceptance_id = f"{phase_id}_{_mermaid_id(criterion.id)}"
            lines.append(
                f'  {acceptance_id}["{_mermaid_label(criterion.id, criterion.statement)}"]'
            )
            lines.append(f"  {phase_id} --> {acceptance_id}")
    lines.extend(
        f"  {source} --> {target}" for source, target in zip(phase_ids, phase_ids[1:])
    )
    if phase_ids:
        for criterion in task.plan.acceptance:
            acceptance_id = f"task_{_mermaid_id(criterion.id)}"
            lines.append(
                f'  {acceptance_id}["{_mermaid_label(criterion.id, criterion.statement)}"]'
            )
            lines.append(f"  {phase_ids[-1]} --> {acceptance_id}")
    return "\n".join(lines)


def _mermaid_id(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", value)


def _mermaid_label(identifier: str, text: str | None) -> str:
    label = identifier if text is None else f"{identifier}: {text}"
    return label.replace('"', "&quot;").replace("\n", " ")
