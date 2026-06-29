# 目的・前提・方針案

- `whub status` で重い remote resource をデフォルト対象から外せるようにする。
- `boot` と同様に resource 側へフラグを持たせ、デフォルトは有効にする。
- supercomputer host の resource だけ manifest で無効化する方針を第一候補にする。

# 計画

## Phase 1: 方針確認
- [ ] `docs/whub-concepts.md` の status 全件対象ポリシーとの整合を確認する。
- [ ] フラグ名を `status` または `status_check` から選ぶ。

## Phase 2: 実装方針
- [ ] `BaseResource` にデフォルト有効の status 用 bool を追加する。
- [ ] `whub status` の対象収集後に status 無効 resource を除外する。
- [ ] `.whub/manifest.yaml` の supercomputer resource だけ status 無効を設定する。

## Phase 3: 検証方針
- [ ] status 対象除外の単体テストを追加する。
- [ ] 既存テストで manifest 互換性と remote git 差分処理を確認する。

# 実行ログ

- 未着手。

# 結果

- 未実施。
