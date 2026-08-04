from __future__ import annotations

import pytest

from whub.core.context import WhubContext, reset_context


@pytest.fixture(autouse=True)
def isolate_whub_context(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context_dir = tmp_path / "context"
    context_dir.mkdir()
    context_dir.joinpath("config.toml").write_text(f'workspace_root = "{tmp_path}"\n')
    context = WhubContext(context_dir)
    monkeypatch.setattr("whub.services.manifest.current_context", lambda: context)
    reset_context()
    yield
    reset_context()
