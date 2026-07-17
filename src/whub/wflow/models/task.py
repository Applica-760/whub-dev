"""Pydantic models for task execution records."""
from __future__ import annotations

from collections import Counter
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


NonEmptyStr = Annotated[str, Field(min_length=1)]
StateName = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]*$")]
TASK_ID_PATTERN = r"^TASK-[0-9]+$"


class TaskModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class TaskHeader(TaskModel):
    id: str = Field(pattern=TASK_ID_PATTERN)
    state: StateName
    title: NonEmptyStr
    objective: NonEmptyStr
    approach: list[NonEmptyStr] = Field(default_factory=list)
    depends_on: list[Annotated[str, Field(pattern=TASK_ID_PATTERN)]] = Field(
        default_factory=list
    )
    interruption_task_id: Annotated[str, Field(pattern=TASK_ID_PATTERN)] | None = None
    interruption_reason: NonEmptyStr | None = None
    interruption_source_task_id: Annotated[str, Field(pattern=TASK_ID_PATTERN)] | None = None

    @model_validator(mode="after")
    def _validate_interruption_fields(self) -> TaskHeader:
        if (self.interruption_task_id is None) != (self.interruption_reason is None):
            raise ValueError("interruption_task_id and interruption_reason must be provided together")
        if self.id in {self.interruption_task_id, self.interruption_source_task_id}:
            raise ValueError("task cannot interrupt itself")
        return self


class AcceptanceCriterion(TaskModel):
    id: str = Field(pattern=r"^ACC-[0-9]+$")
    statement: NonEmptyStr


class PlanStep(TaskModel):
    description: NonEmptyStr
    state: StateName
    skip_reason: NonEmptyStr | None = None

    @model_validator(mode="after")
    def _validate_skip_reason(self) -> PlanStep:
        if self.state == "skipped" and self.skip_reason is None:
            raise ValueError("skipped step requires skip_reason")
        if self.state != "skipped" and self.skip_reason is not None:
            raise ValueError("skip_reason is only allowed for skipped steps")
        return self


class PlanPhase(TaskModel):
    title: NonEmptyStr
    acceptance: list[AcceptanceCriterion] = Field(default_factory=list)
    steps: list[PlanStep] = Field(min_length=1)
    log: list[NonEmptyStr] = Field(default_factory=list)


class TaskPlan(TaskModel):
    acceptance: list[AcceptanceCriterion] = Field(default_factory=list)
    phases: list[PlanPhase] = Field(min_length=1)


class PlanApproval(TaskModel):
    actor: NonEmptyStr


class AcceptanceResult(TaskModel):
    acceptance: str = Field(pattern=r"^ACC-[0-9]+$")
    status: StateName
    evidence: list[NonEmptyStr] = Field(default_factory=list)


class ChangeRequest(TaskModel):
    reason: NonEmptyStr


class TaskCancellation(TaskModel):
    reason: NonEmptyStr
    actor: NonEmptyStr


class TaskResult(TaskModel):
    summary: NonEmptyStr


class TaskSummary(TaskModel):
    """Derived read model for one Task discovered in a directory."""

    path: NonEmptyStr
    id: str | None = None
    title: str | None = None
    state: StateName | None = None
    depends_on: list[str] = Field(default_factory=list)
    interruption_task_id: str | None = None
    interruption_reason: str | None = None
    interruption_source_task_id: str | None = None
    resumable: bool = False
    blocked_by: list[NonEmptyStr] = Field(default_factory=list)
    ready: bool = False
    diagnostics: list[NonEmptyStr] = Field(default_factory=list)


class TaskDocument(TaskModel):
    schema_version: Literal[1]
    task: TaskHeader
    plan: TaskPlan | None = None
    approvals: list[PlanApproval] = Field(default_factory=list)
    acceptance_results: list[AcceptanceResult] = Field(default_factory=list)
    change_requests: list[ChangeRequest] = Field(default_factory=list)
    cancellation: TaskCancellation | None = None
    result: TaskResult | None = None

    @model_validator(mode="after")
    def _validate_acceptance_references(self) -> TaskDocument:
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

        acceptance_counts = Counter(item.acceptance for item in self.acceptance_results)
        duplicate_acceptance = sorted(
            item_id for item_id, count in acceptance_counts.items() if count > 1
        )
        if duplicate_acceptance:
            raise ValueError(
                "duplicate acceptance results: "
                f"{', '.join(duplicate_acceptance)}"
            )

        return self
