from __future__ import annotations

import pytest

from whub.core.context import WhubContext, reset_context


@pytest.fixture(autouse=True)
def isolate_whub_context(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = WhubContext(tmp_path)
    monkeypatch.setattr("whub.models.manifest.current_context", lambda: context)
    reset_context()
    yield
    reset_context()
