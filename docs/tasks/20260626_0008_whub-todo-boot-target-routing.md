# 目的・前提・方針案

## 目的
`20260624_1629_whub-resource-target-routing.md`から残作業を分離し、`todo` / `boot`の改修を小さく完了させる。

## 前提
- 正本は`docs/whub-concepts.md`
- `cd` / `status`のTarget/Router適用は完了済み
- `todo`はresource操作ではなく、projectに紐づくタスク管理コマンド
- `boot`はworkspace-hub配布を例外として残す
- `target`は現時点では`TargetItem`整形と`local` / `remote`呼び分けを担う

## 方針案
- `todo`はTarget適用せず、manifest取得とproject存在確認の責務を整理する
- `boot`はworkspace-hub例外を維持しつつ、resource type分岐を`on_targets`へ寄せられる範囲だけ寄せる
- 複雑な配布処理そのものは`boot.py`側に残す
- 既存挙動を変えず、単体テストで回帰を確認する

# 計画

## Phase 1: `todo`改修
- [ ] `todo add`のmanifest取得とproject存在確認を確認し、必要な整理だけ行う
- [ ] `todo`のprojectなし/未知project/既知projectのテストを追加する

## Phase 2: `boot`改修
- [ ] workspace-hub例外とresource付きprojectの収集を分離する
- [ ] `boot`のlocal/remote呼び分けを`TargetItem` / `on_targets`へ寄せる
- [ ] `_apply_local_boot` / `_apply_remote_boot`の責務と引数を維持または最小整理する

## Phase 3: 検証
- [ ] `uv run python -m unittest discover -s src/whub/tests`を実行する
- [ ] `docs/whub-concepts.md`との乖離が残っていないか確認する

# 実行ログ

# 結果
