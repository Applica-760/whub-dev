# whub app vaultエクスプローラービュー追加

## 目的・前提・方針案

- 目的: whub appからvault内ノートをツリー閲覧・Markdown表示できるようにし、inboxとの連携性を高める
- 前提: vaultは`vault/`配下のMarkdown群（inbox / mind / literature / daily / whub / recruit 等）
- 前提: appはFastAPI（`src/whub/webapp/routers/`）+ React（`app/src/features/`）構成。BacklogPageにreact-markdownの遅延読込レンダリング実績あり
- 前提: backlogの「HTMLビュー/Markdownレンダラー導入」「vaultエクスプローラーがあればinboxとの連携性高まりそう」を具体化するもの
- 方針案: `/api/vault`にツリー取得・ノート内容取得のread-only APIを追加し、フロントに`features/vault`（ディレクトリツリー + Markdownビューア）を新タブとして追加。編集・refile操作は初期スコープ外
- 方針確定: Markdown描画はBacklogWidget同様react-markdown（skipHtml）を共通コンポーネント化して使い回す。portfolioのレンダラーは移植しない
- 方針確定: エクスプローラーUIはMantine標準の`Tree`（`@mantine/core` 8.x, `useTree`）を流用し、`PageFrame`の`aside`スロットに置く
- 決定: 表示範囲はvault全体（`recruit/`含む）。対象は`.md`のみ。完了時にbacklogの「HTMLビュー/Markdownレンダラー導入」「vaultエクスプローラー」を消し込む

## 計画

### Phase 1: バックエンド `/api/vault`（read-only）
- [x] `src/whub/services/vault.py` 新規: `_resolve_vault_path`を`services/inbox.py`から移設して共用（inbox側はimportに変更）
- [x] 同ファイルに `list_vault_tree(manifest)` を実装: vault配下の`.md`をネストJSONツリーで一括返却（`.git`等の隠しディレクトリ除外。vaultは約80mdと小規模なため遅延取得より一括が単純）
- [x] 同ファイルに `read_vault_note(manifest, relative_path)` を実装: resolve後にvault配下であることを検証（パストラバーサル防止）し本文を返却
- [x] `src/whub/webapp/routers/vault.py` 新規: `GET /api/vault/tree` と `GET /api/vault/note?path=...`（既存routerの構成踏襲）
- [x] `src/whub/webapp/server.py` にvault router登録
- [x] `src/whub/tests/test_vault_service.py` 追加（ツリー生成・トラバーサル拒否・不在パス）、`test_webapp_api.py` にAPIテスト追記
- 設計調整: ツリーの形は`services/vault.py`の`VaultNode`（pydantic）をSSoTとし、routerはそれをresponseに使う（`ResourceStatus`と同配置）。読取エラーは理由を返し分けず単一のNotFoundErrorに統一

### Phase 2: 共通Markdownビュー
- [x] `app/src/components/MarkdownView.tsx` 新規: react-markdown（skipHtml）+ 汎用CSSクラスの薄いラッパー
- [x] `app/src/features/backlog/BacklogWidget.tsx` のReactMarkdown直書きをMarkdownViewへ置換
- [x] `app/src/theme/global.css` の`backlog-markdown`スタイルを`md-view`へ改名し共用（`backlog-appended`はBacklog固有のため据え置き）

### Phase 3: Vaultページ
- [x] `app/src/features/vault/useVaultTree.ts` 新規: `/api/vault/tree`取得hook（`useProjects`の形式踏襲）。`api.ts`にfetch関数、`client.ts`に生成schema由来の型aliasを追加
- [x] `app/src/features/vault/VaultPage.tsx` 新規: `PageFrame`のasideにMantine `Tree`、mainに選択ノートの`MarkdownView`
- [x] `app/src/App.tsx` にnavタブ`Vault`とlazy route `/vault` 追加（react-markdown依存のためBacklog同様遅延読込）
- [x] `app/` で `npm run generate:types` を実行し生成型を更新
- 設計調整: asideの幅指定クラス`backlog-project-list`を`page-aside-list`へ改名しBacklog/Vaultで共用

### Phase 4: 検証
- [x] `npm run typecheck` / `npm run build` / `uv run pytest`（全200件pass）
- [x] ビルド済みdistを`whub app`で配信し、実vaultのツリー表示・ノート描画・Backlog回帰を目視確認

## 実行ログ

### 試行 1: Vaultタブが「取得できませんでした」
- 実施内容: 起動中サーバへ`curl /api/vault/tree`
- 結果: 404。router追加前に起動した旧プロセスが原因（healthは200）
- 判断: `whub app`再起動で解消。コード変更なし

### 試行 2: ツリーが見にくい・インデント不発・アイコンサイズ不揃い
- 実施内容: `@tabler/icons-react`導入、renderNodeを装飾強化
- 結果: Groupの`px`がMantine Treeの階層オフセットをinline styleで上書きしていた。アイコンはflex-shrinkで潰れていた
- 判断: `level`から左パディングを明示計算（8px/段）、アイコンに`flex-shrink: 0`で解消

### 試行 3: frontmatter付きノートのレンダリング崩れ
- 実施内容: 原因分析。CommonMarkでは閉じ`---`が直前段落をsetext見出し化するため、空行挿入では直らない
- 結果: `remark-frontmatter`をMarkdownViewへ追加し表示から除外（vaultデータは無変更）
- 判断: レンダラー側で根本解決

## 結果

- `/api/vault`（tree/note、read-only、`VaultNode`はservice層がSSoT）とVaultタブ（Mantine Treeエクスプローラー + MarkdownView）を追加
- Markdown描画は`components/MarkdownView.tsx`へ共通化しBacklogと共用。frontmatterは非表示
- 追加依存: `@tabler/icons-react`, `remark-frontmatter`
- 検証: pytest全200件pass、typecheck/build通過、実vaultで目視確認済み（2026-07-13）