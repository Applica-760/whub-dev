"""Task Mermaid views."""

from __future__ import annotations

import re

from whub.wflow.models.task import TaskDocument


def render_task_flow(task: TaskDocument) -> str:
    """Render one Task's Phase order and Phase acceptance criteria as Mermaid."""
    lines = [
        "flowchart TD",
        "  classDef completed fill:#d3f9d8,stroke:#2b8a3e,color:#1b4332",
        "  classDef incomplete fill:#e7f5ff,stroke:#228be6,color:#1864ab",
        "  classDef deleted fill:#f1f3f5,stroke:#adb5bd,color:#868e96,stroke-dasharray:5 5",
    ]
    if task.plan is None:
        return "\n".join(lines)

    phase_ids: list[str] = []
    for phase_number, phase in enumerate(task.plan.phases, start=1):
        phase_id = f"phase_{phase_number:03}"
        phase_ids.append(phase_id)
        lines.append(
            f'  {phase_id}["{_mermaid_label(f"Phase {phase_number}", phase.title)}"]'
        )
        active_steps = [step for step in phase.steps if not step.deleted]
        phase_class = (
            "deleted"
            if phase.deleted
            else "completed"
            if all(step.state in {"done", "skipped"} for step in active_steps)
            else "incomplete"
        )
        lines.append(f"  class {phase_id} {phase_class}")
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
