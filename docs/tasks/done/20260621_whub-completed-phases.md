# whub 完了済みフェーズ記録

## ロードマップ Phase 1-6（基盤構築〜Agent配布）

元タスク: `20260619_0430_workspace-hub-roadmap.md`

- Phase 1: 基盤構築（uv + Click + Pydantic、manifest schema、CLI スタブ）
- Phase 2: symlink管理（`whub link` + .gitignore自動追記）
- Phase 3: リモートマウント（sshfs mount/unmount）
- Phase 4: hub cd + shell-init + Tab補完
- Phase 5: 状態確認（`whub status` 表示）
- Phase 6: Agentルール配布（`whub boot deploy`）

## リファクタリング Phase 1-2

元タスク: `20260621_1509_whub-refactoring.md`

### Phase 1: パス・設定解決の統一
- manifest を `.whub/manifest.yaml` に固定
- `--manifest` と Click context の manifest パス受け渡しを削除
- `get_manifest` で遅延ロード + context内キャッシュ
- state を `.whub/state.yaml` に固定
- 補完処理を通常処理と同じ読み込み経路へ統一

### Phase 2: リソースモデルと状態判定の統一
- Resource を判別Union（Symlink/Mount）に分割、種別固有フィールド必須化
- `health.py` に共通生存確認 + 種別検証を実装
- `link`・`mount/unmount`・`status` を共通Health判定へ接続
- `status --check` で SSH深度確認
- 到達不能分岐を型による網羅処理へ置換
- `host_names` を mount/unmount 補完へ接続

## リファクタリング Phase 3（部分完了）

- managed block更新を汎用関数へ統一（Markdown/.gitignoreでマーカー切替）
- managed blockの片側欠落・重複・順序逆転を検出しエラー中止
- `.gitignore` に共通ignoreをmanaged blockとして挿入・更新
- ディレクトリ全置換を廃止、ファイル単位上書きへ変更

## status-dashboard Phase 1-2

元タスク: `20260621_1700_whub-status-dashboard.md`

- models/ パッケージ整理（manifest.py 移動、state.py 新設）
- `.whub/` ディレクトリ導入 + manifest 移動
