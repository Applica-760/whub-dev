# 目的・前提・方針案

- `render.py` の `render_table` をリッチ化し、列の意味を示すヘッダ行を出せるようにする。
- 現在は幅揃えした行を `click.echo` するだけなので、見た目をより詳細に操作できる余地を作る。
- ヘッダは今後あらゆるテーブルに加えたいので `render.py` が責務を持つ。
- `render_table` はヘッダ文字列リストをオプショナル引数として受け取れるようにする。
- `todo` の可読性改善は `todo.py` が責務を持ち、必要ならpriority別にテーブル分割して呼び出す。
- 空白・改行・区切り線などの表示調整は `render_table` の引数で制御できる余地を作る。
- Markdown風の `|` / `-` を使ったテーブル表示も候補に含める。
- `status` はまずヘッダ追加を優先する。

# 計画

## Phase 1: render_table 拡張
- [x] `headers: Sequence[object] | None` を追加し、指定時にヘッダ行を表示する。
- [x] ヘッダ指定時は常に区切り線を表示する。
- [x] 既存呼び出しはヘッダ未指定なら現状表示を維持する。

## Phase 2: status ヘッダ追加
- [x] `status` の `render_table` 呼び出しに `project/state/type/git` 相当のヘッダを渡す。

## Phase 3: todo 表示改善
- [x] `todo` 側で列定義を見直し、ヘッダを渡す。
- [ ] priority別テーブル分割による可読性改善を検証する。
- [x] priority境界の空行挿入は `todo` 側で担う。

## Phase 4: 検証
- [ ] `render_table` のヘッダ・区切り・既存互換テストを追加する。
- [ ] `todo` / `status` の表示差分をCLI実行で確認する。

# 実行ログ

- `render_table(headers=...)` を追加し、`status` から `project/state/type/git` ヘッダを渡すようにした。
- `todo` の固定 `due` 列を削除し、ヘッダ追加とpriority境界の空行挿入を実装。
- ヘッダ指定時に列幅へ合わせた区切り線を常に表示するようにした。

# 結果

- 未実施。
