"""Shared CLI helper tests."""
from __future__ import annotations

from unittest.mock import patch

import click
from click.testing import CliRunner

from whub.commands import get_manifest
from whub.models import ManifestError


@click.command()
@click.pass_context
def _command(ctx: click.Context) -> None:
    get_manifest(ctx)


def test_get_manifest_converts_manifest_error_to_click_exception() -> None:
    with patch(
        "whub.commands.load_manifest",
        side_effect=ManifestError("manifest.yaml not found: /tmp/manifest.yaml"),
    ):
        result = CliRunner().invoke(_command)

    assert result.exit_code != 0
    assert "manifest.yaml not found: /tmp/manifest.yaml" in result.output
