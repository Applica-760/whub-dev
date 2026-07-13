# 目的・前提・方針案

- whub web appをダークテーマ対応し、既存のライトテーマも維持する。
- Mantineのcolor schemeを利用し、初期値はOS設定へ追従、ヘッダーで手動切替して選択を保存する。
- 数値カラーはprimitive tokenへ一元化し、用途別カラーをlight/darkのペアで管理する。
- 固定色をsemantic colorへ置換し、Python/APIは変更しない。

# 計画

## Phase 1: 現行実装の確認
- [x] CodeGraphと実装を確認し、light固定設定と固定色の影響範囲を特定する。

## Phase 2: テーマ対応
- [x] MantineProviderのcolor schemeをautoへ変更し、テーマ選択を永続化する。
- [] ヘッダーへlight/dark切替を追加し、アクセシブルな操作名を設定する。
- [x] 現行の数値色8個とlight/darkペアのsemantic colorをテーマ配下の単一定義源へ集約する。
- [x] App背景、共通CSS、GroupedList、Vaultの色適用をCSSへ集約する。

## Phase 3: 検証
- [] テーマ切替と永続化をテストで確認する。
- [x] `npm test`と`npm run build`を実行する。
- [] light/dark双方で主要ルートと狭幅表示を目視確認する。

# 実行ログ

### 試行 1: 自動生成リンク向けignoreをリポジトリ直下へ限定する
- 実施内容: `.gitignore`の`projects`と`vault`を`/projects`と`/vault`へ変更した。
- 結果: `app/src/features/projects/`と`app/src/features/vault/`が追跡候補になった。
- 判断: 続行

### 試行 2: 現行カラーだけを単一定義源へ集約する
- 実施内容: 現行の数値色8個だけをprimitive化し、実使用する10個のlight/darkペアをCSS変数として生成した。
- 結果: TSXの固定色とCSS変数参照を除去し、型検査・4テスト・本番ビルドが成功した。
- 判断: 続行

# 結果

- 未着手
