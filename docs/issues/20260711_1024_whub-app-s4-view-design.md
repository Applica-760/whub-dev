# whub app S4 ビュー設計の決定記録

## 結論
S4は2本の実行仕様書に分割し、UI方針4点を確定した。

- [S4a: grouped list部品＋Todoビュー](../specs/20260711_1020_whub-app-s4a-grouped-list-todo-view.md)
- [S4b: Backlogビュー＋Inboxページ](../specs/20260711_1021_whub-app-s4b-backlog-inbox-view.md)（S4aの部品を再利用するため直列で着手）

## 前提・目的
- S1〜S3完了により、API契約（`app/openapi.json`）・フロント基盤（`app/`: Vite+React+Mantine・iOS風テーマ・生成型）が確定済み。S4はMVP初期スコープの最後のピース
- S1.5の申し送りにより、inbox投函UIフォームもS4に組み込む（Todo・Backlogに加えて3つ目の作業対象）
- 仕様書は関数単位まで詳細化して他Agentへ委譲する方針（ロードマップ: `../tasks/20260708_2108_existing-features-html-view.md`）のため、1本では大きすぎると判断し2分割した

## 調査結果

### 現状確認（2026-07-11）
- フロントは`App.tsx`のヘッダーナビ＋プレースホルダーページのみ。grouped list部品は未実装（S3で「S4で作る」と申し送り済み）
- APIの制約: PATCH `/api/todos/{id}`は`done`化のみで**titleやpriorityの編集はできない** → todo編集はS4非対象と明記
- `priority`は`red|yellow|blue|none`の4値enum。日付はISO date形式（CLIのMMDD入力とは別）
- backlogのcontentはmarkdown生文字列。未作成projectは空文字200

### UI決定（ユーザー相談・2026-07-11）
| 論点 | 決定 | 補足 |
|---|---|---|
| Todoリスト構成 | iOSリマインダー風1本リスト | ただし**後から別パターン（project別・テーブル等）を試せる構造**が条件 → container/presentational分離で対応 |
| Todo追加UI | クイック追加バー＋展開式詳細 | title＋Enterで即追加、project/priority/dueは展開時のみ |
| Backlogビュー | 左paneのproject切替＋markdown描画 | react-markdown系の依存を1つ追加 |
| Inbox投函 | 独立ページ`/inbox` | ヘッダーモーダル案は不採用。ナビ3タブ目 |

### 仕様策定時の判断
- UIテスト基盤（vitest）はS4aでも導入見送り（手動＋型検証で足る規模。シンプルさ優先）
- 状態管理ライブラリは追加せず、変更系操作後は再取得で整合（localhost・小データ・last-write-wins方針）
- 完了取り消し（done→pending）はAPI契約が未確認のためUIを作らない（S4aリスク欄に記載）

### 未解決（仕様書の不明点欄に記載）
- 完了済みtodoの一括削除・自動整理の要否（S4a）
- Backlog左paneのproject並び順はmanifest定義順のままでよいか（S4b）
