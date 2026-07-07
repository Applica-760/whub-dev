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
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import whub.render as render_module
from whub.render import TableCell, render_table


def _render(*args, **kwargs) -> str:
    output = io.StringIO()
    with redirect_stdout(output):
        render_table(*args, **kwargs)
    return output.getvalue()


class RenderSpecTest(unittest.TestCase):
    def test_empty_table_outputs_nothing(self) -> None:
        # ケース1
        self.assertEqual(_render([]), "")

    def test_headers_emit_separator_and_rows(self) -> None:
        # ケース2
        output = _render([("ok", "local")], headers=("state", "project"))

        self.assertIn("state  project", output)
        self.assertIn("--------------", output)
        self.assertIn("ok     local", output)

    def test_right_align_applies_to_selected_columns(self) -> None:
        # ケース3
        output = _render([(1, "a"), (20, "b")], headers=("id", "name"), right_align={0})

        self.assertIn("  1  a", output)
        self.assertIn("  20  b", output)

    def test_east_asian_width_is_used_for_padding(self) -> None:
        # ケース4
        output = _render([("状態", "ok"), ("x", "ng")])

        self.assertIn("状態  ok", output)
        self.assertIn("x     ng", output)

    def test_table_cell_displays_value_and_applies_style(self) -> None:
        # ケース5
        with patch.object(
            render_module.click,
            "style",
            side_effect=lambda text, **_: text,
        ) as style:
            output = _render([(TableCell("warn", fg="yellow"),)])

        self.assertIn("warn", output)
        style.assert_called_with("warn", fg="yellow", bold=False)


if __name__ == "__main__":
    unittest.main()
