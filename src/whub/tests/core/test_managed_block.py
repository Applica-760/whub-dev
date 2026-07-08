"""`whub.utils.managed_block`の仕様テスト。"""
from __future__ import annotations

import pytest

from whub.utils.managed_block import format_block, replace_or_prepend_block


class TestManagedBlockSpec:
    _MARKERS = ("<!-- start -->", "<!-- end -->")

    def test_format_block(self):
        assert format_block(self._MARKERS, "hello\n") == (
            "<!-- start -->\nhello\n<!-- end -->\n"
        )

    def test_new_file(self):
        source = "<!-- start -->\nhello\n<!-- end -->\n"
        result = replace_or_prepend_block(source, None, self._MARKERS)

        assert result == source

    def test_existing_without_markers_prepends(self):
        source = "<!-- start -->\nhello\n<!-- end -->\n"
        existing = "old content\n"
        result = replace_or_prepend_block(source, existing, self._MARKERS)

        assert result.startswith("<!-- start -->")
        assert "old content" in result

    def test_existing_with_markers_replaces(self):
        source = "<!-- start -->\nnew\n<!-- end -->\n"
        existing = "before\n<!-- start -->\nold\n<!-- end -->\nafter\n"
        result = replace_or_prepend_block(source, existing, self._MARKERS)

        assert "new" in result
        assert "old" not in result
        assert "before" in result
        assert "after" in result

    def test_rejects_unpaired_markers(self):
        source = "<!-- start -->\nnew\n<!-- end -->\n"
        existing = "<!-- start -->\nmissing end\n"
        with pytest.raises(ValueError, match="duplicate or unpaired"):
            replace_or_prepend_block(source, existing, self._MARKERS)
