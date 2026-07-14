"""Pydantic models for task execution records."""
from __future__ import annotations

from collections import Counter
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


NonEmptyStr = Annotated[str, Field(min_length=1)]
StateName = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]*$")]


class TaskModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class TaskHeader(TaskModel):
    id: str = Field(pattern=r"^TASK-[0-9]+$")
    workflow: str = Field(pattern=r"^WF-[0-9]+$")
    state: StateName
    title: NonEmptyStr
    objective: NonEmptyStr
    assumptions: list[NonEmptyStr] = Field(default_factory=list)
    approach: list[NonEmptyStr] = Field(default_factory=list)
    depends_on: list[Annotated[str, Field(pattern=r"^TASK-[0-9]+$")]] = Field(
        default_factory=list
    )


class AcceptanceCriterion(TaskModel):
    id: str = Field(pattern=r"^ACC-[0-9]+$")
    statement: NonEmptyStr


class PlanStep(TaskModel):
    id: str = Field(pattern=r"^STP-[0-9]+-[0-9]+$")
    description: NonEmptyStr
    state: StateName


class PlanPhase(TaskModel):
    id: str = Field(pattern=r"^PHA-[0-9]+$")
    title: NonEmptyStr
    acceptance: list[AcceptanceCriterion] = Field(default_factory=list)
    steps: list[PlanStep] = Field(min_length=1)


class TaskPlan(TaskModel):
    revision: int = Field(gt=0)
    acceptance: list[AcceptanceCriterion] = Field(default_factory=list)
    phases: list[PlanPhase] = Field(min_length=1)


class PlanApproval(TaskModel):
    plan_revision: int = Field(gt=0)
    actor: NonEmptyStr


class AcceptanceResult(TaskModel):
    acceptance: str = Field(pattern=r"^ACC-[0-9]+$")
    status: StateName
    evidence: list[NonEmptyStr] = Field(min_length=1)


class ChangeRequest(TaskModel):
    plan_revision: int = Field(gt=0)
    reason: NonEmptyStr
    resolved_by_plan_revision: int | None = Field(default=None, gt=0)


class TaskCancellation(TaskModel):
    reason: NonEmptyStr
    actor: NonEmptyStr


class TaskResult(TaskModel):
    summary: NonEmptyStr


class TaskDocument(TaskModel):
    schema_version: Literal[1]
    task: TaskHeader
    open_questions: list[NonEmptyStr] = Field(default_factory=list)
    decisions: list[NonEmptyStr] = Field(default_factory=list)
    plan: TaskPlan | None = None
    approvals: list[PlanApproval] = Field(default_factory=list)
    acceptance_results: list[AcceptanceResult] = Field(default_factory=list)
    change_requests: list[ChangeRequest] = Field(default_factory=list)
    cancellation: TaskCancellation | None = None
    result: TaskResult | None = None

    @model_validator(mode="after")
    def _validate_ids_and_references(self) -> TaskDocument:
        if self.plan is None:
            if self.approvals or self.acceptance_results or self.change_requests:
                raise ValueError("plan records require a plan")
            return self

        criteria = [
            *self.plan.acceptance,
            *(
                criterion
                for phase in self.plan.phases
                for criterion in phase.acceptance
            ),
        ]
        phases = self.plan.phases
        steps = [step for phase in phases for step in phase.steps]
        ids = [
            *(criterion.id for criterion in criteria),
            *(phase.id for phase in phases),
            *(step.id for step in steps),
        ]
        counts = Counter(ids)
        duplicates = sorted(item_id for item_id, count in counts.items() if count > 1)
        if duplicates:
            raise ValueError(f"duplicate task-planning ids: {', '.join(duplicates)}")

        for phase in phases:
            phase_number = phase.id.removeprefix("PHA-")
            expected_prefix = f"STP-{phase_number}-"
            for step in phase.steps:
                if not step.id.startswith(expected_prefix):
                    raise ValueError(
                        f"step '{step.id}' does not belong to phase '{phase.id}'"
                    )

        known_acceptance_ids = {criterion.id for criterion in criteria}
        unknown_acceptance_ids = sorted(
            {
                item.acceptance
                for item in self.acceptance_results
                if item.acceptance not in known_acceptance_ids
            }
        )
        if unknown_acceptance_ids:
            raise ValueError(
                f"unknown acceptance ids: {', '.join(unknown_acceptance_ids)}"
            )

        referenced_revisions = [
            *(approval.plan_revision for approval in self.approvals),
            *(request.plan_revision for request in self.change_requests),
            *(
                request.resolved_by_plan_revision
                for request in self.change_requests
                if request.resolved_by_plan_revision is not None
            ),
        ]
        future_revisions = sorted(
            {revision for revision in referenced_revisions if revision > self.plan.revision}
        )
        if future_revisions:
            raise ValueError(
                "future plan revisions: "
                f"{', '.join(map(str, future_revisions))}"
            )
        return self
