from __future__ import annotations

import pytest

from whub.core.context import reset_context


@pytest.fixture(autouse=True)
def isolate_whub_context() -> None:
    reset_context()
    yield
    reset_context()
