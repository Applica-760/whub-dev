"""Workflow definition loading and semantic checks."""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import yaml
from pydantic import ValidationError

from whub.wflow.models.workflow import WorkflowDefinition
from whub.wflow.services.errors import Diagnostic, WflowError


def load_workflow(path: Path) -> WorkflowDefinition:
    """Load one Workflow definition from YAML."""
    try:
        return WorkflowDefinition.model_validate(yaml.safe_load(path.read_text()))
    except (OSError, yaml.YAMLError, ValidationError) as error:
        raise WflowError(f"failed to load Workflow YAML: {path}: {error}") from error


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

    # ケース1: 遷移グラフとtriggerの組合せを収集する。
    for transition in workflow.transitions:
        for source in transition.source_states:
            adjacency[source].add(transition.to)
            reverse_adjacency[transition.to].add(source)
            key = (source, transition.trigger)
            # ケース2: 同一状態とtriggerの遷移は一意である。
            if key in transition_keys:
                diagnostics.append(
                    Diagnostic(
                        "ambiguous_trigger",
                        f"state '{source}' has multiple '{transition.trigger}' transitions",
                    )
                )
            transition_keys.add(key)
            # ケース3: 終端状態は遷移元にしない。
            if source in terminal_states:
                diagnostics.append(
                    Diagnostic(
                        "terminal_state_has_transition",
                        f"terminal state '{source}' has an outgoing transition",
                    )
                )

    # ケース4: 全状態は初期状態から到達できる。
    reachable = _reachable_states({workflow.workflow.initial_state}, adjacency)
    for state in workflow.states:
        if state not in reachable:
            diagnostics.append(
                Diagnostic(
                    "unreachable_state",
                    f"state '{state}' is unreachable from the initial state",
                )
            )

    # ケース5: 非終端状態は少なくとも一つの終端状態へ到達できる。
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
