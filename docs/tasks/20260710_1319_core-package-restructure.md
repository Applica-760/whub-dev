# whubパッケージのcore再編

## 目的・前提・方針案
- 目的: whub直下に平置きされた低レイヤーモジュールを`core/`（名称は要検討）へ移設し、層構造を明確にする
- 前提: 層分離の方向はwhub app S2a（services/新設）で確定済み。移設候補は`paths.py`・`remote.py`・`target.py`・`health.py`・`tmux.py`
- 前提: import書き換えが全域に波及する純粋リファクタのため、機能追加と混ぜず単独で実施する
- 方針: CLI振る舞い不変・既存テスト全通過を受け入れ基準とし、`docs/whub-concepts.md`の層記述も同時更新する
- 経緯: `docs/tasks/20260708_2108_existing-features-html-view.md`のS2a検討時に分離を決定（2026-07-10）

## 計画

## 実行ログ

## 結果
