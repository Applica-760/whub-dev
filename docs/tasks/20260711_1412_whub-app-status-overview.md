# whub app: Statusと統合ビュー

## 目的・前提・方針案

- 目的: statusの確認摩擦を下げ、Todo・Inbox・resource状態をWeb appの入口へ集約する。
- 前提: WebはFastAPI APIを介してPython serviceを呼び、CLIとserviceを直接接続しない。
- 方針: 汎用libや状態管理ライブラリは増やさず、feature別APIとhookで再利用する。
- 方針: mountはResource Statusのremote表示として扱い、Webからのmount操作は対象外とする。
- 方針: `PageFrame`はページ配置、Widgetは各機能の表示・操作を担い、専門ページとOverviewから同じWidgetを利用する。
- 方針: Widgetは配置先の幅へレスポンシブに適応し、グリッド寸法と並び順はOverviewが担う。

## 計画

### Phase 1: フロント基盤の整理
- [x] Todo・Projectのfeature別API、`useProjects`、`useTodos`、Todo追加フォームを分離し、統合ビューで再利用可能にする。
- [x] 重複するAPIエラー文言変換を共有し、`npm run typecheck`と`npm run build`で検証する。

### Phase 2: Status収集のservice/API化
- [x] `services/status.py`へresource状態収集を移し、CLIは描画と終了コード判定だけにする。
- [x] `GET /api/resources/status`でCLIと同じstate/type/mount/tmux/gitを返し、OpenAPI型とservice・CLI・APIのテストを更新する。
- [x] `uv run pytest`と型生成で契約を検証する。

### Phase 3: Statusビューの追加
- [x] Resource Status画面をCLI対応の6列テーブルで追加し、手動更新・最終成功時刻・取得中・失敗状態を実装する。
- [x] remote resourceのmount状態をBadgeで示し、直前の成功データを保持する同じ表示モデルで扱う。
- [x] 型検査・ビルド・API接続の手動確認を行う。

### Phase 4: 統合ビューの追加
- [ ] TodoをレスポンシブなWidgetへ切り出し、Todoページから同じWidgetを利用する。
- [ ] Inbox・Statusを配置先の幅へ適応するWidgetへ切り出し、各専門ページから同じWidgetを利用する。
- [ ] `/`をTodo・Inbox・Status Widgetを可変グリッドで配置するOverviewへ変更する。
- [ ] Backlog要約、FOCUS、CPU・メモリ表示を対象外として、既存専門ページへの導線を保つ。
- [ ] 型検査・ビルド・pytest・手動確認でCLI/Webの状態一致を検証する。

## 実行ログ

### 試行 1: remote git差分のserviceテスト
- 実施内容: git差分を期待するremote fixtureで収集結果を検証した。
- 結果: fixtureにgit設定がなく、仕様どおり`-`が返った。
- 判断: fixtureへgit設定を明示して継続。

### 試行 2: Status画面のブラウザ確認
- 実施内容: ローカル画面のブラウザ操作を試みた。
- 結果: 実行環境のブラウザ接続制約により開始できず、buildと実サーバーのAPI応答で代替検証した。
- 判断: 続行

## 結果
