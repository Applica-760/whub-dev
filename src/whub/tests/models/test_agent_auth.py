import pytest
from pydantic import ValidationError

from whub.models.agent.auth import AgentAuth


def test_rejects_unknown_fields() -> None:
    data = {
        "name": "base",
        "type": "base",
        "variables": {},
        "grants": {
            "commands": {"prefixes": [], "exact": [], "templates": []},
            "filesystem": {"read": [], "write": []},
            "network": {"policy": "deny_all"},
            "extension_tools": [],
        },
        "unknown": True,
    }

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        AgentAuth.model_validate(data)
