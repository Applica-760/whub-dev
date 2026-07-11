# 実行仕様書: whub app S4b — BacklogビューとInboxページ

## 目的
- project別backlogの閲覧・追記と、inbox投函の独立ページを実装し、Web app初期スコープ（todo＋backlog＋inbox投函）を完成させる

## 背景・前提
- UI決定（2026-07-11 相談）: Backlogは左paneのproject切替＋本文markdownレンダリング＋下部追記フォーム。Inboxは独立ページ`/inbox`（ナビ3タブ目）
- API契約は`docs/specs/20260710_1853_whub-app-s2b-resource-api.md`を正とする: GET `/api/projects`、GET/POST `/api/backlog/{project}`（未作成projectは空文字200・POSTは`memo`追記）、POST `/api/inbox`（title・body必須、`filename`返却）
- inboxの役割定義（S1.5 `docs/specs/20260710_1630_whub-app-s1.5-inbox-service.md`）: 対話抜きで思いつきを書き殴る摩擦ゼロの投函口。project非紐付け
- S4aのgrouped list部品・エラー表示パターンを再利用する（**S4a完了後に着手**）
- backlog表示はmount前提でSSHしない（remote未mount時はAPIがエラーを返す）

## 対象範囲
- `app/src/features/backlog/`: Backlogビュー実装（プレースホルダ置換）
- `app/src/features/inbox/`: 投函ページ新設、`/inbox`ルートとナビ項目の追加
- markdownレンダリング用の依存追加（1ライブラリ）

## 非対象範囲
- backlog本文の編集・削除（追記のみ。CLI `whub backlog`と同経路）
- inboxの一覧・閲覧・整理（投函のみ。整理はrefile Skillの領分）
- todoビューの変更（S4a）、FOCUSビュー、S5 Agent連携

## 変更要件
- Backlogビュー
    - 左pane: GET `/api/projects`のproject一覧を表示し、選択状態を持つ（初期選択は先頭project）
    - 選択でGET `/api/backlog/{project}`を取得し、右paneに本文をmarkdownレンダリング表示
    - contentが空文字のprojectは空状態表示（エラー扱いにしない）
    - 下部の追記フォーム: 1行メモを入力しPOST→再取得で本文に反映される
    - remote未mount等のAPIエラーはdetailメッセージを右paneに表示し、project切替は操作可能なまま残す
- Inboxページ
    - `/inbox`ルートを追加し、ナビゲーションにTodo・Backlogと並べて表示する
    - title入力（必須）とbody複数行入力（必須）のフォーム
    - 投函成功でフォームをクリアし、生成された`filename`をフィードバック表示（通知等）。連続投函できる
    - 失敗時は入力内容を保持したままエラー表示する
- markdownレンダリング
    - 見出し・リスト・リンク・コードブロックがiOS風テーマに馴染むスタイルで表示される
    - 本文中のraw HTMLは描画しない（レンダラの安全な既定を維持）

## 実装方針
- markdown描画はreact-markdown（remark系）を既定候補とし、プラグイン追加は最小限に留める
- 左paneのproject一覧はS4aのgrouped list部品を再利用する
- 選択projectのURL反映（`/backlog/:project`等のdeep link）は任意。実装コストが小さければ入れてよい
- フォーム送信後の反映は再取得で行う（S4a同様、楽観更新は必須でない）

## 受け入れ基準
- [ ] project選択→backlog表示→追記→表示更新の一連が動く
- [ ] backlog未作成のprojectで空状態が表示され、エラーにならない
- [ ] markdown（見出し・リスト・リンク・コード）が整形表示され、raw HTMLは描画されない
- [ ] `/inbox`で投函するとvault/inbox/に日時プレフィックス付きファイルが生成される
- [ ] 投函成功でフォームがクリアされfilenameが通知される。失敗時は入力が保持される
- [ ] `npm run typecheck`・`npm run build`が通り、`uv run pytest`が全件通過する（whub側非変更の確認）

## 検証条件
- 自動: `npm run typecheck`・`npm run build`・`uv run pytest`
- 手動: devサーバまたは`whub app`でbacklog閲覧・追記後にファイル実体（またはCLI）で追記結果を確認。inbox投函後に`vault/inbox/`の生成ファイルの中身（title・body）を確認

## リスク・注意点
- react-markdown系の依存追加によるバンドルサイズ増はlocalhost用途のため許容する
- 表示するのは自分のvault/backlogの内容だが、raw HTML非描画の既定は崩さない
- POST `/api/backlog/{project}`はCLIと同経路（remote対応）のため、remote projectへの追記は接続状態に依存する。エラー表示で気づける形にする

## 不明点・確認事項
- Backlogの左paneに表示するprojectの並び順はAPI返却順のままでよいか（現状はmanifest定義順）
