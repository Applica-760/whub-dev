# whub リファクタリング

## 目的・前提・方針案

### 目的
- `src/whub` のパス・設定・状態判定を一元化し、重複実装と暗黙の依存を減らす
- ファイル更新やパス解決によるデータ損失・誤操作を防止する
- 未接続のモデルを予定機能へ接続し、実質無効な実装を残さない

⭐️ コードをできるだけ短く、シンプルにする


### 前提
- 対象は `src/whub` 以下と対応するテスト
- whubコマンドはworkspace-hubルートから実行する
- manifestとstateは`.whub/manifest.yaml`・`.whub/state.yaml`に固定する
- `State` と `GitInfo` は削除せず、進行中のstatus拡張へ接続する
- 挙動変更を伴う箇所はcharacterization testで現状と期待仕様を明確にしてから変更する
- 各Phaseは変更対象と検証を共有できる処理単位でまとめる

### 改善すべき要素

| グループ | 改善要素 |
|---|---|
| パス・設定解決 | 任意manifest対応による分岐、既定パスの重複、補完時のmanifest不一致、stateパスの重複 |
| リソースモデル・判定 | mount/symlink固有値のOptional化、symlink判定の不一致、到達不能分岐、未使用host補完 |
| boot・managed file | `.gitignore`更新の競合、終了マーカー欠落、`.codex`全置換、配置名・対象名の散在 |
| shell・外部コマンド | SSH終了コードの二重管理、zsh固定の不要分岐、sshfs探索の重複、OS依存コマンド |
| 未接続・未実装機能 | State/GitInfoの未接続、version未検証、doctor未実装 |
| テスト | パス解決、ファイル非破壊性、状態判定、CLI連携の回帰テスト不在 |

### 方針案
- 共通化は同じ仕様を表す処理に限定し、表示やコマンド固有のポリシーは分離する
- ファイル更新は前後のユーザー記述を保存し、破壊的な置換を呼出側で明示する
- パス解決とresource種別の規則はモデル層を唯一の定義元とする
- State/GitInfoはstatus拡張と同時に接続し、単独の先行APIとして残さない

## 計画

### Phase 1: パス・設定解決の統一
- [x] manifestを`.whub/manifest.yaml`、workspace rootをカレントディレクトリに固定する
- [x] `--manifest`とClick contextのmanifestパス受け渡しを削除する
- [x] manifestを`get_manifest`で遅延ロードし、同一Click context内でキャッシュする
- [x] stateを`.whub/state.yaml`に固定し、load/saveのパス引数を削除する
- [x] 補完処理を通常処理と同じ固定manifestの読み込み経路へ統一する

### Phase 2: リソースモデルと状態判定の統一
- [x] mount/symlinkを判別Unionへ分割し、種別固有フィールドを必須化する
- [x] `health.py`にresource共通の生存確認と種別ごとの検証を実装する
- [x] `link`・`mount/unmount`・`status`を共通Health判定へ接続する
- [x] `status --check`でmountのSSH深度確認を実行できるようにする
- [x] resource typeの到達不能分岐を型による網羅的処理へ置き換える
- [x] `host_names`をmount/unmount補完へ接続する


### Phase 3: boot配布とmanaged file更新の整理
- [ ] 現行boot配布のcharacterization testを追加し、マーカー外記述・JSON固有設定・配布先固有ファイルの保持条件を固定する
- [x] managed block更新を一つの汎用関数へ統一し、Markdownと`.gitignore`で開始・終了マーカーだけを切り替える
- [x] managed blockの片側欠落・重複・順序逆転を更新前に検出し、対象ファイルを含む明示的エラーで書き込みを中止する
- [x] `.gitignore`へ共通ignoreをmanaged blockとして挿入・更新し、マーカー外の既存記述と既存の重複行を変更しない
- [x] ディレクトリ全置換を廃止し、ファイル単位の上書きへ変更してプロジェクト固有Skill・設定を保持する
- [ ] `source`・`destination`・更新戦略を配布仕様テーブルへ集約し、`AGENTS.md`・`.claude`・`.codex`・`.mcp.json`の分岐を単純化する
- [ ] `_copy`・`_deploy_file`・個別定数群を配布仕様と少数の更新関数へ整理し、`boot.py`を短縮する
- [ ] 初回配布・再配布の冪等性、固有記述保持、異常マーカー時の非更新、固有Skill保持を一時ディレクトリ上で検証する

### Phase 4: shellと外部コマンド境界の整理
- [ ] SSH遷移用終了コードを単一定義からPythonとshellへ反映する
- [ ] zsh専用仕様なら`--shell`と常時真の分岐を削除する
- [ ] sshfs実行パスを一度だけ解決してmount処理へ渡す
- [ ] 対応OSを明示し、sshfs導入案内とunmountコマンドの扱いを統一する

### Phase 5: 未接続・未実装機能の整理
- [ ] Stateのstatus・priorityをstatus表示と編集処理へ接続する
- [ ] GitInfoをstatusのgit状態取得へ接続する
- [ ] manifest versionを対応値として検証するか、不要なら廃止する
- [ ] doctorの責務を定義して実装するか、実装までCLI登録を外す

### Phase 6: 回帰テストの整備
- [ ] workspace-hubルート起点の固定manifest・stateパスを検証するテストを追加する
- [ ] `.gitignore`とmanaged blockがユーザー記述を失わないテストを追加する
- [ ] `.codex`配布方式の保持・置換範囲を検証するテストを追加する
- [ ] symlink状態とlink/statusの整合性テストを追加する
- [ ] shell終了コード、補完、State/GitInfo連携のCLIテストを追加する

## 実行ログ

### 試行 1: workspace-hubルート起点の固定パスへ簡素化
- 実施内容: 任意manifest対応・root推測・パス引数を削除し、manifest/stateを各モデル内の固定パスへ統一
- 結果: `whub --help`、`whub status`、manifestキャッシュ、補完用読み込み、state読み込みが成功
- 判断: 続行

### 試行 2: resource種別と生存確認の共通化
- 実施内容: Resourceを判別Unionへ分割し、Health判定をlink・mount/unmount・statusへ統合
- 結果: 既存manifest互換、symlink各状態、mount浅部/SSH深度判定、link→status統合、host補完を確認
- 判断: 続行

### 試行 3: boot配布の非破壊化と`.gitignore`管理
- 実施内容: managed block検証を共通化し、ディレクトリ全削除を廃止、`.my-boot/.gitignore`をSSOTとしてbootとinstall.shから配布
- 結果: 構文・差分検査に成功し、install.shの2回実行で既存ignore保持とmanaged blockの冪等性を確認
- 判断: 続行

## 結果

（完了時に記録）
