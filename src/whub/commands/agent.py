"""Open prepared Agent worktree shells."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping

import click

from whub.core.context import current_context
from whub.services.errors import ServiceError
from whub.webapp.agent_attention_control import submit as submit_attention_hook


@click.group()
def agent() -> None:
    """Receive Agent lifecycle hooks."""


@agent.command(name="attention-hook")
def attention_hook() -> None:
    """Forward one Codex Hook event without affecting its approval flow."""
    try:
        event = json.load(click.get_text_stream("stdin"))
        if not isinstance(event, Mapping):
            return
        operator_id = os.environ.get("WHUB_OPERATOR_ID")
        if operator_id:
            event = {**event, "operator_id": operator_id}
        submit_attention_hook(current_context(), event)
    except (OSError, ServiceError, TypeError, json.JSONDecodeError):
        return
