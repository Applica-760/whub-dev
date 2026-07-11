# 実行仕様書: whub app S4a — grouped list部品とTodoビュー

## 目的
- iOS設定画面風のgrouped list共通部品を確立し、Todoの閲覧・追加・完了・削除ができるビューを実装する

## 背景・前提
- UI決定（2026-07-11 相談、実装後更新）: リストはiOSリマインダー風1本リストを基本とするが、**後から別のビューパターン（project別・テーブル等）を追加・切替できる構造**にする。追加UIはクイック追加バーと常時表示の詳細入力
- API契約は`docs/specs/20260710_1853_whub-app-s2b-resource-api.md`を正とする: GET/POST `/api/todos`、PATCH `/api/todos/{id}`（done化のみ）、DELETE `/api/todos/{id}`（204）、GET `/api/projects`
- `TodoResponse`: id・title・project(null可)・priority(`red|yellow|blue|none`)・done・created_at・due_date(null可)・done_at(null可)。日付はISO date形式（`app/openapi.json`より）
- GET `/api/todos`は`pending`/`completed`を同梱で返す
- S3基盤（`docs/specs/20260710_2153_whub-app-s3-frontend-foundation.md`）: `theme/`・`components/`・`features/`・`api/`分離、生成型＋fetchラッパ、iOS風テーマトークン定義済み
- 開発時はVite devサーバの`/api`プロキシで`127.0.0.1:8710`へ転送

## 対象範囲
- `app/src/components/`: grouped list汎用部品（セクション・行・ヘッダ）の新設
- `app/src/features/todos/`: Todoビュー実装（プレースホルダ置換）
- `app/src/api/`: 変更系リクエスト（POST/PATCH/DELETE）に必要ならfetchラッパ拡張

## 非対象範囲
- Backlogビュー・Inboxページ（S4b）
- todoの編集（title・priority・due等の変更）: APIが未対応（PATCHはdoneのみ）のため対象外
- ビューパターン切替UIと2つ目のパターン実装（切替可能な**構造**にするのみ）
- UIテスト基盤（vitest等）の導入（手動＋型検証で足る規模のため今回は見送り）
- whub側（Python）の変更

## 変更要件
- grouped list部品（ドメイン非依存・`components/`配置）
    - 白サーフェス・角丸・行間区切り線のセクションカード、セクションヘッダ（タイトル・右アクセサリ）、行（左アクセサリ／本文＋サブテキスト／右アクセサリ）
    - todo固有の知識を持たず、props経由で内容を受け取る
- Todoビュー
    - GET `/api/todos`で取得し、pendingを1本のgrouped listで表示
    - pending行: チェックサークル、title、サブテキスト（project・due_date）、priorityの視覚区別（red/yellow/blue/noneをテーマ色で）
    - チェック操作でPATCH（done化）し、リストを更新（completedセクションへ移動）
    - completedは件数付きセクションとして常時表示し、done_atを表示
    - 削除操作を提供する（誤操作しにくい形。hover表示・確認等は実装者判断）。DELETE成功でリストから消える
    - クイック追加バー: リスト上部に常設。title入力＋Enterで追加でき、project（GET `/api/projects`の選択肢）・priority・due_dateも常時指定可能
    - ロード中・空状態・APIエラー（`ApiError`のdetail）の表示を持ち、エラーで白画面にならない
- ビュー切替可能な構造
    - データ取得・更新（container/hooks層）とリスト描画（presentational層）を分離し、同一のprops契約で別レイアウトを差し込める形にする

## 実装方針
- 状態管理ライブラリは追加しない（React標準のstate＋再取得）。変更系操作後はGETし直して整合を取る（localhost・小データ・last-write-wins方針のため楽観更新は必須でない）
- 部品はMantineの上に薄く被せ、Apple感はテーマ層で寄せる方針（S3）を踏襲。コンポーネント個別のスタイル上書きを増やさない
- due_dateの入力はAPIのISO date形式へ変換して送る（CLIのMMDD形式とは独立にWeb側で扱いやすい入力でよい）

## 受け入れ基準
- [x] `/todos`でpending/completedが表示され、追加・完了・削除が画面に反映される
- [x] クイック追加（title＋Enter）と詳細指定追加（project/priority/due）の両方が動く
- [x] completedセクションに件数とdone_atが表示される
- [x] APIエラー時にdetailメッセージが表示され、アプリが操作可能なまま残る
- [x] grouped list部品がtodoに依存しない（他featureから再利用可能なprops設計）
- [x] `npm run typecheck`・`npm run build`が通り、`uv run pytest`が全件通過する（whub側非変更の確認）

## 検証条件
- 自動: `npm run typecheck`・`npm run build`・`uv run pytest`
- 手動: devサーバまたは`whub app`で追加→詳細指定追加→完了→completed確認→削除の一連を実施し、`whub todo list`（CLI）で同じ状態が見えることを確認する

## リスク・注意点
- PATCHはdone化のみでdoneの取り消しAPI契約が未確認。完了の取り消しUIは契約確認まで作らない
- todos.yamlのCLI・手編集との同時変更はlast-write-wins。再取得で画面整合を取る
- priorityの`red`とdue超過の強調が混同されない表示にする

## 不明点・確認事項
- 完了済みtodoの一括削除・自動整理は要件外でよいか（現状は1件ずつ削除）
