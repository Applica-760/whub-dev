# whubパッケージのcore再編

## 目的・前提・方針案
- 目的: whub直下に平置きされた低レイヤーモジュールを`core/`（名称は要検討）へ移設し、層構造を明確にする
- 前提: 層分離の方向はwhub app S2a（services/新設）で確定済み。移設候補は`paths.py`・`remote.py`・`target.py`・`health.py`・`tmux.py`
- 前提: import書き換えが全域に波及する純粋リファクタのため、機能追加と混ぜず単独で実施する
- 方針: CLI振る舞い不変・既存テスト全通過を受け入れ基準とし、`docs/whub-concepts.md`の層記述も同時更新する
- 経緯: `docs/tasks/20260708_2108_existing-features-html-view.md`のS2a検討時に分離を決定（2026-07-10）

## 計画
- 決定: 新パッケージ名は`core/`（tests/core/と対応）。utils/は現状維持。target.py含む5モジュール全てをcoreへ（core=CLI/Web非依存の下位層と定義し、models依存の混在は許容）
- 計画時からの差分: webapp/openapi.py・commands/app.pyが参照元に追加。tests/core/は既存のためテスト移動は不要（utils系テスト2件の不整合解消のみ）

### Phase 1: core/新設と移設
- [x] `src/whub/core/__init__.py`を作成し、`paths.py`・`remote.py`・`target.py`・`health.py`・`tmux.py`を`git mv`で移設（履歴保持のためgit mv）

### Phase 2: import書き換え
- [x] 非テストコード26箇所（commands 11・models 2・services 1・webapp 1ファイル）を`whub.X`→`whub.core.X`へ書き換え
- [x] tests配下のimportを同様に書き換え（`import whub.X as`形式・docstring内言及も含め計42箇所を一括置換）

### Phase 3: テスト整合・ドキュメント・検証
- [x] `tests/core/test_managed_block.py`・`test_render.py`を`tests/utils/`へ移動（utilsのテストなので配置を実装と揃える）
- [x] `docs/whub-concepts.md`の層記述を更新（core層の定義追記、target/remote/health/tmux/pathsの`core/`パス表記）
- [x] `uv run pytest`全通過とCLI起動（`uv run whub --help`）で振る舞い不変を確認

## 実行ログ
- 想定外の事象なし。全Phase計画通り

## 結果
- `paths`/`remote`/`target`/`health`/`tmux`を`src/whub/core/`へ移設し、参照42箇所を`whub.core.X`へ書き換え（git mvで履歴保持）
- utils系テスト2件を`tests/utils/`へ移動し実装と配置を一致。`docs/whub-concepts.md`にcore層定義を追記
- 検証: 184テスト全通過、`whub --help`正常起動（CLI振る舞い不変）
