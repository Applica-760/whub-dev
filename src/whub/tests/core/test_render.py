"""`whub.render`の仕様テスト。

検証するケース:
1. 行もheaderもなければ何も出力しない。
2. headerありなら見出し・separator・行を出力する。
3. `right_align`指定列だけ右寄せする。
4. 全角文字の表示幅を考慮して列を揃える。
5. `TableCell`は値を表示し、Click styleを適用する。

検証しないケース:
1. すべてのUnicode幅分類。
2. Click styleの内部ANSI仕様詳細。
3. 各コマンド固有の表内容。
"""
from __future__ import annotations

import io
from contextlib import redirect_stdout
from unittest.mock import patch

import whub.render as render_module
from whub.render import TableCell, render_table


def _render(*args, **kwargs) -> str:
    output = io.StringIO()
    with redirect_stdout(output):
        render_table(*args, **kwargs)
    return output.getvalue()


class TestRenderSpec:
    def test_empty_table_outputs_nothing(self) -> None:
        # ケース1
        assert _render([]) == ""

    def test_headers_emit_separator_and_rows(self) -> None:
        # ケース2
        output = _render([("ok", "local")], headers=("state", "project"))

        assert "state  project" in output
        assert "--------------" in output
        assert "ok     local" in output

    def test_right_align_applies_to_selected_columns(self) -> None:
        # ケース3
        output = _render([(1, "a"), (20, "b")], headers=("id", "name"), right_align={0})

        assert "  1  a" in output
        assert "  20  b" in output

    def test_east_asian_width_is_used_for_padding(self) -> None:
        # ケース4
        output = _render([("状態", "ok"), ("x", "ng")])

        assert "状態  ok" in output
        assert "x     ng" in output

    def test_table_cell_displays_value_and_applies_style(self) -> None:
        # ケース5
        with patch.object(
            render_module.click,
            "style",
            side_effect=lambda text, **_: text,
        ) as style:
            output = _render([(TableCell("warn", fg="yellow"),)])

        assert "warn" in output
        style.assert_called_with("warn", fg="yellow", bold=False)
