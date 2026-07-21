from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from whub.models import SessionDescriptor


def descriptor_data() -> dict:
    now = datetime.now(timezone.utc)
    return {
        "schema_version": 1,
        "protocol_version": 1,
        "project": "remote",
        "task": "TASK-030",
        "run_id": "TASK-030-r001",
        "state": "pending",
        "created_at": now,
        "updated_at": now,
        "tmux": None,
        "panes": [],
    }


def test_session_descriptor_accepts_protocol_v1() -> None:
    descriptor = SessionDescriptor.model_validate(descriptor_data())
    assert descriptor.run_id == "TASK-030-r001"


def test_session_descriptor_rejects_unknown_fields() -> None:
    data = descriptor_data()
    data["unknown"] = True
    with pytest.raises(ValidationError):
        SessionDescriptor.model_validate(data)


def test_session_descriptor_rejects_unsafe_run_id() -> None:
    data = descriptor_data()
    data["run_id"] = "../escape"
    with pytest.raises(ValidationError):
        SessionDescriptor.model_validate(data)
