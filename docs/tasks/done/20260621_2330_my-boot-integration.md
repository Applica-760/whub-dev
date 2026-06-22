# my-bootのwhub統合

## 目的・前提・方針案

- `.my-boot`の配布資産をwhubパッケージへ統合し、外部リポジトリ・symlink・manifestの特別リソース依存を廃止する
- 配布資産は`src/whub/boot/`へ置き、インストール後も利用できるよう`importlib.resources`で参照する
- managed block、settings.jsonマージ、固有ファイル保持、AppleDouble除去の現行仕様は維持する
- Skillはwhub内に共通正本を置き、Claude用`.claude/skills`とCodex用`.agents/skills`へコピーして内容を統一する
- Codexのプロジェクト指示は探索仕様に従いルート`AGENTS.md`へ配置し、`.codex/`への集約は行わない
- CodeGraphは`.mcp.json`・利用指示の配布と、利用可能な場合の対象プロジェクト初期化までをwhubで扱う
- CodeGraph viewer、npm依存、`.my-boot/install.sh`は移行せず廃止し、可視化機能は本タスクの対象外とする
- `.my-boot`リポジトリの削除・アーカイブはwhub側の移行と検証完了後に実施する

## 計画

### Phase 1: 移行対象と保持仕様の固定
- [x] `.my-boot`から配布資産だけを抽出し、viewer・npm・README・install.shを除外する
- [x] Claude・Codexで共用できるSkillとツール固有記述を分類し、共通正本からの配布仕様を固定する
- [x] whub配布とCodeGraph初期化の正常系・未導入・失敗時の出力と終了条件を定義する
- [x] workspace-hubと`.my-boot`の既存差分を記録し、本タスク外の変更を上書きしない

#### Phase 1 固定仕様
- 移行対象は`.claude/CLAUDE.md`・`settings.json`、`.codex/config.toml`、`skills/`、`AGENTS.md`、`.mcp.json`とする
- 配布先`.gitignore`のmanaged blockは実際の配布対象と`.codegraph/`から動的生成し、テンプレートを持たない
- 除外対象は`.DS_Store`、`.claude/specs`、README、idea、install.sh、viewer scripts、package.json、package-lock、node_modulesとする
- 3 Skillは共通正本とし、`argument-hint`削除、相対リソース参照、仕様書出力先の`docs/specs`化でエージェント中立にする
- Skillは`.claude/skills`と`.agents/skills`へ同一内容をコピーし、配布先固有Skillは削除しない
- CodeGraphは配布成功後に既存対象ごとに`codegraph init <target>`を実行し、成功時は対象名を表示する
- CodeGraph未導入時は警告を1回表示し、初期化失敗時は対象別に警告して処理を継続し、bootの終了コードは0とする
- workspace-hubの既存変更は保持し、cleanな`.my-boot`からは確定した配布資産だけを次Phaseでコピーする

### Phase 2: 配布資産のパッケージ統合
- [x] `.claude/`、`.codex/`、`skills/`、`AGENTS.md`、`.mcp.json`を`src/whub/boot/`へ移す
- [x] Skill共通正本を`skills/`へ置き、Phase 3で`.claude/skills`と`.agents/skills`へコピーできる構成にする
- [x] `AGENTS.md`は配布先ルート用原本、`.codex/`はconfig用原本として分離する
- [x] hidden fileを含む配布資産が設定追加なしでsdist・wheelへ収録されることを確認する
- [x] 開発ツリーとインストール済みwheelの両方で`importlib.resources`から資産を参照できることを確認する

### Phase 3: boot実装の独立化
- [x] `boot.py`の配布元をmanifestの`my-boot`リソースから`importlib.resources`のパッケージ資産へ変更する
- [x] `my-boot`検索・除外・配布元なし分岐を削除し、`boot: true`リソースとworkspace-hubだけを対象にする
- [x] managed block、settings.jsonマージ、固有ファイル保持、AppleDouble除去を維持する
- [x] 共通Skill正本をClaude・Codex双方へ同一内容でコピーし、配布先固有Skillを削除しない
- [x] 配布先`.gitignore`のmanaged blockを配布対象から動的生成し、構成との二重管理をなくす

### Phase 4: CodeGraph連携
- [x] `.mcp.json`とAGENTS.md・CLAUDE.mdのCodeGraph利用指示を配布資産として維持する
- [x] 配布成功後、ローカルの`codegraph`が利用可能な場合だけ対象ごとに`codegraph init <target>`を実行する
- [x] 未導入時は警告を1回、初期化失敗時は対象別に警告し、いずれも配布成功・終了コード0を維持する
- [x] viewerスクリプト・package.json・node_modulesを配布または同梱しないことを確認する

### Phase 5: manifest・構成・文書の整理
- [x] `.whub/manifest.yaml`から`my-boot`リソースを削除し、`.my-boot` symlinkへの依存を除く
- [x] README、CLI仕様、ディレクトリ構成、ADRから外部`.my-boot`前提とinstall.sh記述を削除する
- [x] `.gitignore`等の`.my-boot`参照を整理し、不要になったローカルsymlinkを削除する

### Phase 6: 回帰検証と旧配布物整理
- [x] 隔離先で初回配布、再配布、冪等性、固有記述保持、JSONマージ、異常マーカーを検証する
- [x] CodeGraph導入済み・未導入の両条件を模擬し、実プロジェクトへ配布せず動作を確認する
- [x] sdist・wheelを生成して資産収録、インストール後のCLI help・boot実行、旧`.my-boot`非依存を確認する
- [x] Claudeが`.claude/skills`、Codexが`.agents/skills`とルート`AGENTS.md`を認識する配置になっていることを確認する
- [x] 構文、import、YAML、差分、旧参照検索を通過し、既存プロジェクト内の旧`.my-boot`を削除する

## 実行ログ

### 試行 1: 配布元.gitignoreが配布資産を無視する
- 実施内容: `.gitignore`原本を削除し、Phase 3で実際の配布対象からmanaged blockを動的生成する方針へ変更した
- 結果: `.claude`・`.codex`・`AGENTS.md`・`.mcp.json`がGit追跡対象になり、構成との二重管理も解消できる
- 判断: 方針変更

### 試行 2: 動的.gitignoreの再配布で固有記述と連結する
- 実施内容: 生成するmanaged blockへ末尾改行を追加した
- 結果: 2回目以降も固有記述との境界とファイルハッシュが維持された
- 判断: 続行

### 試行 3: 固定構造に対してboot処理が汎用的すぎる
- 実施内容: gitignoreの動的解析と不要な型変換を削除し、固定配布一覧と全階層AppleDouble除去へ整理した
- 結果: 開発ツリー・wheelの配布仕様を維持しつつ処理を単純化できた
- 判断: 続行

### 試行 4: link用gitignoreブロックの再生成は他symlinkも操作し得る
- 実施内容: 今回だけ自動生成ブロックから`.my-boot`を手動削除し、外部リポジトリを残してローカルsymlinkのみ削除した
- 結果: manifestとgitignoreの管理対象が一致し、他リソースを変更せず旧symlink依存を除去できた
- 判断: 続行

### 試行 5: YAML全探索がsymlink・mount先まで走査する
- 実施内容: 検証対象をGit管理領域の`.whub`と`docs`へ限定し、directory-structureの不正な入れ子を修正した
- 結果: YAML 3件の構文検証に成功し、外部・リモート領域を走査せず検証できた
- 判断: 方針変更

### 試行 6: マウント先の旧`.my-boot`削除が低速
- 実施内容: 既存プロジェクトを調査し、imitation-learning内の旧配布物1件をリモート側で削除した
- 結果: 全boot対象から旧`.my-boot`がなくなり、外部my-bootリポジトリ本体は保持された
- 判断: 続行

## 結果

- my-boot配布資産をwhubパッケージへ統合し、manifest・symlink・外部リポジトリへの実行時依存を除去した
- 隔離テスト4件、sdist・wheel収録、インストール後CLI・boot、YAML・import・差分・旧参照検索を通過した
- 既存プロジェクト内の旧`.my-boot`を削除し、外部my-bootリポジトリ本体はユーザー方針により保持した
