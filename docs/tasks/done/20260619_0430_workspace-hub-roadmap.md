# workspace-hub ロードマップ策定

## 目的・前提・方針案

- `docs/requirements.md`の全FR/NFRを実現するためのアーキテクチャ意思決定を対話的に行う
- 決定事項はADRとして`docs/ADR/`に記録する
- .my-bootはClone済み。後のPhaseでworkspace-hubに統合する前提

## 計画

### 確定済みADR

- [ADR-0001: マニフェストを単一YAMLファイルとする](../ADR/0001-manifest-single-file.md)
- [ADR-0002: CLIツールの実装言語をPythonとする](../ADR/0002-cli-language-python.md)
- [ADR-0003: マニフェストをルート直下に配置する](../ADR/0003-manifest-placement-root.md)
- [ADR-0004: マニフェストスキーマ定義](../ADR/0004-manifest-schema.md)
- [ADR-0005: CLIサブコマンド体系](../ADR/0005-cli-subcommands.md)
- [ADR-0006: Agentルール配布方式](../ADR/0006-agent-rules-deploy.md)

### 確定済み方針（ADR未起票）

- ディレクトリ構成はドメイン別（ロケーション別ではない）
- mind/, recruit/ はルート直下にsymlinkで配置
- 既存ローカルリポジトリはsymlinkで参照（SSOT維持）
- リモートリソースはsshfs mountでドメイン内に配置
- workspace-hub自体をGit管理する（symlink/mountは.gitignoreで除外）
- 構成の詳細は `docs/directory-structure.yml` に記載（随時追加）

### 残意思決定

- [x] マニフェストの配置パス → ADR-0003
- [x] mindディレクトリの位置づけ → ルート直下symlink
- [x] ディレクトリ構成の方針 → ドメイン別
- [x] マニフェストの詳細スキーマ設計 → ADR-0004
- [x] CLIのサブコマンド体系 → ADR-0005
- [x] FR-5: Agentルール配布の仕組み → ADR-0006

### Phase 1: 基盤構築
- [x] git init + .gitignore整備
- [x] マニフェストスキーマ設計・ADR化 → ADR-0004
- [x] CLI基盤作成（uv + Click + Pydantic）
  - [x] Step 1: uv init + pyproject.toml + src/whub/ 構造
  - [x] Step 2: Pydanticマニフェストモデル（ADR-0004準拠、SSOT）
  - [x] Step 3: manifest.yamlをADR-0004スキーマに更新
  - [x] Step 4: Clickサブコマンドスタブ（link, mount, unmount, cd, status, boot, doctor）
  - [x] Step 5: `whub status` 実装（マニフェスト読み→リソース状態表示）
  - [x] .yml → .yaml 統一（manifest, ADR, docs全体）

### Phase 2: symlink管理（FR-6, FR-7）
- [x] Step 1: `excludes`をスキーマから削除（ADR-0004 + manifest.py）— 不要と判断
- [x] Step 2: workspace root解決ユーティリティ追加（manifest.yaml基準、CWD非依存）
- [x] Step 3: `whub link` 実装（symlink作成 + 親ディレクトリ自動作成 + 冪等性 + サマリー出力）
- [x] Step 4: `whub link` 実行時にsymlinkパスを.gitignoreへ自動追記（重複なし）
- [x] Step 5: 動作検証（`whub link` → `whub status`）

### Phase 3: リモートマウント（FR-2）
- [x] Step 1: `mount.py` 新設 — sshfsコマンド組み立て + 実行（mount/unmount）
- [x] Step 2: `cli.py` の mount/unmount スタブを `mount.py` 呼び出しに更新
- [x] Step 3: FUSE-T + sshfs-fuse-t インストール
- [x] Step 4: 動作検証（mount成功）

auto_mount制御（ADR-0004スキーマ追加）:
- Host に `auto_mount: bool`（default: true）を追加
- `whub mount` → `auto_mount: true` のホストのみ
- `whub mount <host>` → 明示指定で実行（auto_mount無視）
- `whub mount --all` → 全ホスト

sshfsデフォルトオプション: `-o reconnect,ServerAliveInterval=15,ServerAliveCountMax=3`

sshfsインストール手順（macOS、FUSE-T推奨）:
  `brew install --cask fuse-t && brew install macos-fuse-t/cask/sshfs-fuse-t`
  macFUSE（カーネル拡張）はセキュリティポリシー変更が必要なため非推奨
  → 再起動不要、Intel/Apple Silicon両対応

### Phase 4: hub cd + shell-init + Tab補完（FR-3, FR-6, FR-7）

cd のプロトコル:
- symlink → stdout にパスを出力、exit 0。シェル関数が `builtin cd` する
- mount → `os.execvp("ssh")` でプロセスを SSH に置換。行ったっきり
- `command` 引数は不要（削除）

Steps:
- [x] Step 1: `cd.py` 実装 — リソース名でマニフェスト検索、symlink→パス stdout出力、mount→`os.execvp("ssh")`
- [x] Step 2: `shell_init.py` 新設 — `whub` ラップシェル関数 + Click Tab補完初期化を stdout 出力
- [x] Step 3: `cli.py` に `shell-init` コマンド登録
- [x] Step 4: `cd` のリソース名Tab補完（Click `shell_complete`）— `__init__.py` に `resource_names` として統合
- [x] Step 5: 他コマンドのTab補完 → ホストは2つで実用価値低、スキップ
- [x] Step 6: `status` 整形修正（名前列幅を最長リソース名に揃え）
- [x] Step 7: 動作検証（`eval "$(whub shell-init)"` → `whub cd mind` で cd 確認、`.zshrc` に追記）

### Phase 5: 状態確認（FR-4）
- [x] hub status 更新 — リモートリソース接続実装前に作ったコマンドがローカル挙動しか想定しない実装になっているため、更新する

### Phase 6: Agentルール統合（FR-5）

ADR-0006 からの方針変更:
- CLAUDE.md / AGENTS.md: マーカー方式で既存内容を尊重（旧: 上書き）
- install.sh: 現行維持・スタンドアロン用（旧: 廃止）
- .my-boot は symlink で参照し、テンプレートソースとして維持

配布戦略（install.sh の構造を反映）:
- `claude/` → `.claude/`（CLAUDE.md はマーカー、settings.json はマージ、他は上書き）
- `claude/mcp.json` → `.mcp.json`（上書き）
- `codex/` → `.codex/`（上書き）
- `codex/AGENTS.md` → `AGENTS.md`（マーカー）

Steps:
- [x] CLAUDE.md / AGENTS.md にマーカー追加
- [x] `rules` → `boot`、`agent_rules` → `boot` にリネーム（CLI, manifest, ADR）
- [x] .my-boot クリーンアップ（`.claude/`, `.codex/`, `AGENTS.md` 削除）
- [x] `whub boot deploy` 実装（boot.py + cli.py 薄ラッパー）
- [ ] `whub doctor` — 後回し（下記検討メモ参照）
- [x] ADR-0006 更新（AGENTS.md マーカー化、install.sh 維持を反映）
- [x] 動作検証（symlink リソースのみ、mount は後回し）

### `whub doctor` 検討メモ

ADR-0005定義: リンク切れ、接続不能、manifest構文等の整合性チェック。
ADR-0006要件: マーカー破損検出。

検討の結果、現時点では実用価値のあるチェック項目が少ないため後回し:
- manifest構文エラー → 全コマンドのload時に即検出される
- SSH接続 → mount/SSH実行時に判明する
- マーカー有無 → deploy直後にわかる、deployし直せば済む

実際に使いながら「doctorで検出したい」具体ケースが出てから実装する方針。
候補: リンク切れ検出、deploy後の二重化検出、manifest追加後のlink忘れ検出。

出力形式は `ok / WARN / FAIL` 3段階、リソースごと1行＋末尾サマリーで合意済み。
終了コードは常に0（後続コマンド実行を妨げない）。

## 実行ログ

（なし）

## 結果

（未完了）
