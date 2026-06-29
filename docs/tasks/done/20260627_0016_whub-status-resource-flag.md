# 目的・前提・方針案

- `whub status` で重い remote resource をデフォルト対象から外せるようにする。
- `boot` と同様に resource 側へフラグを持たせ、デフォルトは有効にする。
- supercomputer host の resource だけ manifest で無効化する方針を第一候補にする。

# 計画

## Phase 1: 方針確認
- [ ] `docs/whub-concepts.md` の status 全件対象ポリシーとの整合を確認する。
- [x] フラグ名を `status` に確定する。

## Phase 2: 実装方針
- [x] `BaseResource` にデフォルト有効の `status: bool` を追加する。
- [x] `whub status` の対象収集後に status 無効 resource を除外する。
- [x] `.whub/manifest.yaml` の supercomputer resource だけ `status: false` を設定する。

## Phase 3: 検証方針
- [x] manifest model の status デフォルト有効・明示無効テストを追加する。
- [ ] status 対象除外の単体テストを追加する。
- [ ] 既存テストで manifest 互換性と remote git 差分処理を確認する。

# 実行ログ

- `BaseResource.status` と `esn-lab-run` の `status: false` を追加し、manifest model テストを追加。
- `status.py` に status 無効 resource のフィルタ関数を追加し、`collect_targets()` 後に適用。

# 結果

- `whub status` は `status: false` resource をデフォルト対象から除外する。
- 検証: `python -B -m unittest src/whub/tests/test_manifest.py src/whub/tests/test_status.py` 成功。
