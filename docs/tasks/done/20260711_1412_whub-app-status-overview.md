# whub app: Statusと統合ビュー

## 目的・前提・方針案

- 目的: statusの確認摩擦を下げ、Todo・Inbox・resource状態をWeb appの入口へ集約する。
- 前提: WebはFastAPI APIを介してPython serviceを呼び、CLIとserviceを直接接続しない。
- 方針: 汎用libや状態管理ライブラリは増やさず、feature別APIとhookで再利用する。
- 方針: mountはResource Statusのremote表示として扱い、Webからのmount操作は対象外とする。
- 方針: `PageFrame`はページ配置、Widgetは各機能の表示・操作を担い、専門ページとOverviewから同じWidgetを利用する。
- 方針: Widgetは配置先の幅へレスポンシブに適応し、グリッド寸法と並び順はOverviewが担う。
- 方針: Overviewは全幅の3等分列とし、各列へWidgetを上詰めで縦積みする。

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
- [x] TodoをレスポンシブなWidgetへ切り出し、Todoページから同じWidgetを利用する。
- [x] Statusを`ResourceStatusWidget`へ切り出し、既存hookを保ったまま専門ページから利用する。
- [x] InboxをWidgetへ切り出し、専門ページから利用してOverviewで再利用可能にする。
- [x] Backlog本文・追記機能をWidgetへ切り出し、Project選択を担う専門ページから利用する。
- [x] Overviewを全幅の3等分列とし、各列へWidgetを上詰めで縦積みする。
- [x] Todo WidgetをOverviewへ配置し、専門ページと同じWidgetを再利用する。
- [x] BacklogはOverview対象外とし、Widget化とOverviewへの配置可否を分離して既存専門ページへの導線を保つ。

### Phase 5: StatusのOverview導入
- [x] `ResourceStatusWidget`の固定最小幅を廃止し、6列テーブルを配置先の横幅へ追従させる。
- [x] `OverviewPage.tsx`の3列レイアウトへ既存の`ResourceStatusWidget`を配置する。
- [x] 単独ページとOverviewで横スクロールなしに判別できることを確認する。
- [x] `npm run typecheck`・`npm run build`で検証する。

### Phase 6: InboxのOverview導入
- [x] `OverviewPage.tsx`の右列にあるTodo仮配置を既存の`InboxWidget`へ置き換える。
- [x] `npm run typecheck`・`npm run build`で検証する。

### Phase 7: Widget表示の横断整理
- [x] Overview左列の先頭へ既存のTodo追加フォームを配置する。
- [x] Todoの文字縮小は実画面確認で撤回し、全Widgetの一括統一は行わず現行表示を採用する。
- [x] Todoリスト最終行の二重線を除去し、途中行の区切り線を左右対称にする。
- [x] `npm run typecheck`・`npm run build`とユーザー提供の実画面で検証する。

## 実行ログ

### 試行 1: remote git差分のserviceテスト
- 実施内容: git差分を期待するremote fixtureで収集結果を検証した。
- 結果: fixtureにgit設定がなく、仕様どおり`-`が返った。
- 判断: fixtureへgit設定を明示して継続。

### 試行 2: Status画面のブラウザ確認
- 実施内容: ローカル画面のブラウザ操作を試みた。
- 結果: 実行環境のブラウザ接続制約により開始できず、buildと実サーバーのAPI応答で代替検証した。
- 判断: 続行

### 試行 3: Widgetの依存構造
- 実施内容: Feature・Widget・Pageの責務と配置を整理した。
- 結果: Feature Widgetが共通`WidgetFrame`へ情報を注入し、専門PageとWhubPageが再利用する構成とした。
- 判断: builder層とBacklog左リストのWidget化は追加せず、独立配置する機能だけをWidget化して続行。

### 試行 4: WhubPageでのTodo Widget試作
- 実施内容: 共通`WidgetFrame`と12列Gridを追加し、`features/whub`へ未完了Todo表示を試作した。
- 結果: Desktopは8列、狭幅は全幅で表示でき、既存Todoページを維持したまま統合タブを追加できた。
- 判断: Todo Widgetを`features/todos`へ移して専門PageとWhubPageで共有する方針へ変更。

### 試行 5: TodoのWidget共通化
- 実施内容: Form・ListをWidget化し、状態と操作を`useTodoWidgets`へ集約して両Pageから利用した。
- 結果: 依存方向は整理できたが、`WidgetFrame`とList内部の`Paper`が二重ボックスになった。
- 判断: Listのセクション描画を分割して方針変更。

### 試行 6: Todo ListのWidget分割
- 実施内容: Listから内側の`Paper`を除き、未完了・完了済みを別Widgetへ分割して見出しをボックス外へ移した。
- 結果: 二重ボックスを解消し、WhubPageは未完了Widgetだけを利用し、不要なProject取得も停止した。
- 判断: 続行

### 試行 7: WidgetFrameの可変構成
- 実施内容: `title`を任意化し、見出し・actionがない場合は見出し行を省略する構成へ変更した。
- 結果: Widgetの縦横比は固定せずGrid側で占有範囲を決め、将来はContainer Queryで内容を追従させる方針とした。
- 判断: 続行

### 試行 8: app起動時のfrontend build
- 実施内容: `whub app`で毎回`npm run build`してから起動する案を検討した。
- 結果: 最新buildは保証できるがホットリロードにはならず、起動時間とNode依存が増える。
- 判断: 現状維持とし、必要時に`whub app --build`を追加する案を保留。

### 試行 9: 専門ページのWidgetFrame共通化
- 実施内容: Backlog・Inbox・StatusのWidget化とOverview掲載範囲を整理した。
- 結果: `PageFrame`はページ配置、`WidgetFrame`は主要機能の枠とし、Backlogは専門ページのみで利用する構成とした。
- 判断: Status、Inbox、Backlog、Overviewの順に実装して続行。

### 試行 10: 固定キャンバスによるOverview配置
- 実施内容: 16:9キャンバス内の12列×8行GridへWidgetを固定配置し、キャンバス全体を表示幅へ拡縮した。
- 結果: レイアウトが崩れ、拡大時に低解像度描画のようなぼやけが生じた。
- 判断: 棄却

### 試行 11: 3等分列と列内縦積みによるOverview配置
- 実施内容: Overviewを全幅の3等分列とし、各列へ専門ページと同じ自然寸法のTodo Widgetを上詰めで縦積みした。
- 結果: Widgetの見た目を維持したまま画面幅を活用でき、複数Widgetの縦積みも意図どおり表示できた。
- 判断: 固定キャンバス案を破棄し、3等分列と列内縦積みをOverviewの配置方針として続行。

### 試行 12: Status WidgetのOverview配置
- 実施内容: 720pxの固定最小幅を廃止してテーブルを親幅へ追従させ、Overviewの中央列へ配置した。
- 結果: 型検査とビルドは成功したが、実行環境のブラウザ接続制約により画面確認は未実施。
- 判断: 手動表示確認を残して続行。

### 試行 13: Status Widgetの実画面確認
- 実施内容: ユーザー提供の単独ページとOverviewのスクリーンショットで表示を確認した。
- 結果: 3分割列でも横スクロールなしに6列を判別できたが、Todoとの文字サイズ差が目立った。
- 判断: Status配置は採用し、全Feature移植後に表示を横断整理する。

### 試行 14: Inbox WidgetのOverview配置
- 実施内容: Overview右列のTodo仮配置を既存のInbox Widgetへ置き換えた。
- 結果: 型検査とビルドが成功し、追加の依存実装は不要だった。
- 判断: 投函を伴う手動確認を残して続行。

### 試行 15: Todoの表示密度調整と追加フォーム配置
- 実施内容: Todoだけのタイトル・補足文字を縮小し、Overview左列の先頭へ既存の追加フォームを配置した。
- 結果: Project取得を含む既存controllerを再利用でき、型検査とビルドが成功した。
- 判断: 実画面での表示確認を残して続行。

### 試行 16: Todo文字サイズの実画面確認
- 実施内容: 縮小したTodoリストを実画面で確認した。
- 結果: 他要素とのバランスに違和感が生じた。
- 判断: 文字サイズ変更だけを撤回し、フォーム配置は維持する。

### 試行 17: Todoリスト下端の二重線
- 実施内容: 最終行のDividerとPaper下枠の重複を確認し、最終行だけDividerを描画しないようにした。
- 結果: 行間の区切り線と外枠を維持したまま、ずれた下線の発生条件を除去し、型検査とビルドが成功した。
- 判断: 続行。

### 試行 18: Todoリスト区切り線の左右余白
- 実施内容: 最終行判定を維持し、途中行のDividerを左右とも`md`分だけ内側へ寄せた。
- 結果: 区切り線が左右対称になり、型検査が成功した。
- 判断: 続行。

## 結果

- Todo追加・未完了Todo・resource Status・Inboxを3列Overviewへ集約した。
- Statusを配置幅へ追従させ、Todoリストの下端と区切り線を整理した。
- `uv run pytest`、`npm run typecheck`、`npm run build`と実画面確認で検証した。
