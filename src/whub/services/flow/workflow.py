"""Flow definition loading and semantic checks."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from whub.models.flow import TransitionRequirement, WorkflowDefinition
from whub.services.flow.errors import Diagnostic, FlowError


RequirementEvaluator = Callable[
    [TransitionRequirement, dict[str, Any], dict[str, Any]], str | None
]


def load_workflow(path: Path) -> WorkflowDefinition:
    """Load one Flow definition from YAML."""
    try:
        return WorkflowDefinition.model_validate(yaml.safe_load(path.read_text()))
    except (OSError, yaml.YAMLError, ValidationError) as error:
        raise FlowError(f"failed to load Workflow YAML: {path}: {error}") from error


def _reachable_states(
    starts: set[str],
    adjacency: dict[str, set[str]],
) -> set[str]:
    visited = set(starts)
    pending = list(starts)
    while pending:
        state = pending.pop()
        for target in adjacency[state] - visited:
            visited.add(target)
            pending.append(target)
    return visited


def check_workflow(workflow: WorkflowDefinition) -> tuple[Diagnostic, ...]:
    """Return semantic errors that are not expressible by the Pydantic model."""
    adjacency: dict[str, set[str]] = defaultdict(set)
    reverse_adjacency: dict[str, set[str]] = defaultdict(set)
    diagnostics: list[Diagnostic] = []
    transition_keys: set[tuple[str, str]] = set()
    terminal_states = set(workflow.workflow.terminal_states)

    for transition in workflow.transitions:
        for source in transition.source_states:
            adjacency[source].add(transition.to)
            reverse_adjacency[transition.to].add(source)
            key = (source, transition.trigger)
            if key in transition_keys:
                diagnostics.append(
                    Diagnostic(
                        "ambiguous_trigger",
                        f"state '{source}' has multiple '{transition.trigger}' transitions",
                    )
                )
            transition_keys.add(key)
            if source in terminal_states:
                diagnostics.append(
                    Diagnostic(
                        "terminal_state_has_transition",
                        f"terminal state '{source}' has an outgoing transition",
                    )
                )

    reachable = _reachable_states({workflow.workflow.initial_state}, adjacency)
    for state in workflow.states:
        if state not in reachable:
            diagnostics.append(
                Diagnostic(
                    "unreachable_state",
                    f"state '{state}' is unreachable from the initial state",
                )
            )

    terminal_reachable = _reachable_states(terminal_states, reverse_adjacency)
    for state in workflow.states:
        if state not in terminal_states and state not in terminal_reachable:
            diagnostics.append(
                Diagnostic(
                    "no_terminal_path",
                    f"state '{state}' cannot reach a terminal state",
                )
            )

    return tuple(diagnostics)


def values_at(data: Any, field: str, input_data: dict[str, Any]) -> list[Any]:
    if field.startswith("$input."):
        current: list[Any] = [input_data]
        parts = field.removeprefix("$input.").split(".")
    else:
        current = [data]
        parts = field.removeprefix("$").split(".")

    for part in parts:
        next_values: list[Any] = []
        for value in current:
            if part == "*" and isinstance(value, list):
                next_values.extend(value)
            elif isinstance(value, dict) and part in value:
                next_values.append(value[part])
        current = next_values
    return current


def _resolve_value(value: Any, data: dict[str, Any], input_data: dict[str, Any]) -> Any:
    if isinstance(value, str) and value.startswith("$"):
        values = values_at(data, value, input_data)
        if len(values) != 1:
            raise FlowError(f"record value '{value}' does not resolve to one value")
        return values[0]
    if isinstance(value, list):
        return [_resolve_value(item, data, input_data) for item in value]
    if isinstance(value, dict):
        return {
            key: _resolve_value(item, data, input_data) for key, item in value.items()
        }
    return value


def _requirement_error(
    requirement: TransitionRequirement,
    data: dict[str, Any],
    input_data: dict[str, Any],
    evaluators: Mapping[str, RequirementEvaluator],
) -> str | None:
    values = values_at(data, requirement.field, input_data)
    if requirement.operator == "exists":
        if any(value is not None for value in values):
            return None
    elif requirement.operator == "all_in":
        if values and all(value in requirement.value for value in values):
            return None
    elif evaluator := evaluators.get(requirement.operator):
        return evaluator(requirement, data, input_data)
    else:
        return f"unsupported requirement operator: {requirement.operator}"
    return f"requirement not satisfied: {requirement.field} ({requirement.operator})"


def _transition_for(workflow: WorkflowDefinition, state: str, trigger: str) -> Any:
    candidates = [
        transition
        for transition in workflow.transitions
        if transition.trigger == trigger and state in transition.source_states
    ]
    if not candidates:
        raise FlowError(f"trigger '{trigger}' is not allowed from state '{state}'")
    return candidates[0]


def available_transitions(
    workflow: WorkflowDefinition,
    state: str,
    data: dict[str, Any],
    input_data: dict[str, Any] | None = None,
    evaluators: Mapping[str, RequirementEvaluator] | None = None,
) -> tuple[str, ...]:
    """Return triggers whose declared requirements are satisfied."""
    inputs = input_data or {}
    requirement_evaluators = evaluators or {}
    return tuple(
        transition.trigger
        for transition in workflow.transitions
        if state in transition.source_states
        and not any(
            _requirement_error(requirement, data, inputs, requirement_evaluators)
            for requirement in transition.requires
        )
    )


def apply_transition(
    workflow: WorkflowDefinition,
    state: str,
    data: dict[str, Any],
    trigger: str,
    input_data: dict[str, Any] | None = None,
    evaluators: Mapping[str, RequirementEvaluator] | None = None,
) -> tuple[str, dict[str, Any]]:
    """Apply one declared transition and return its next state and records."""
    transition = _transition_for(workflow, state, trigger)

    inputs = input_data or {}
    requirement_evaluators = evaluators or {}
    errors = [
        error
        for requirement in transition.requires
        if (
            error := _requirement_error(
                requirement, data, inputs, requirement_evaluators
            )
        )
        is not None
    ]
    if errors:
        raise FlowError("; ".join(errors))

    for record in transition.records:
        value = _resolve_value(record.value, data, inputs)
        current = data.get(record.field)
        if isinstance(current, list):
            current.append(value)
        else:
            data[record.field] = value
    return transition.to, data
