# whub app: ルート単位コード分割

## 目的・前提・方針案

- 目的: 初回JavaScriptを削減し、Viteのチャンク超過警告を解消する。
- 前提: 現在の初回チャンクは556 kB（gzip 173 kB）であり、機能障害はない。
- 方針: ページを`React.lazy`で遅延読込し、依存追加や警告閾値の変更は行わない。

## 計画

調査所見: 初回チャンク562 kBの分割可能な主要因は`react-markdown`ツリーで、使用箇所は`BacklogWidget`のみ。Overview(`/`)がTodo/Inbox/Statusのウィジェットを直接importするため、Backlog以外のルート分割は初回JS削減に寄与しない。→ Backlogのみ分割（最小変更）に決定。

### Phase 1: Backlogルート分割
- [x] `App.tsx`で`BacklogPage`を`React.lazy`化し、`Suspense`フォールバックを追加する（react-markdownツリーを別チャンク化するため）。
- [x] `npm run typecheck`・`npm run build`でチャンク超過警告の解消を確認し、`/backlog`直接表示と既存導線を検証する。

## 実行ログ

## 結果

- 初回チャンク 562 kB (gzip 175 kB) → 442 kB (gzip 139 kB)。BacklogPageは121 kB (gzip 38 kB) の別チャンクに分離し、Viteのチャンク超過警告は解消。
- ヘッドレスChromiumで検証: `/backlog`直接表示でレンダリング成功、`/`は初回チャンクのみ読込、タブ遷移時にBacklogチャンクを遅延読込。依存追加・閾値変更なし。
