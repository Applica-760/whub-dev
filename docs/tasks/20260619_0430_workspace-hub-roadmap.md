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
  - [x] Step 4: Clickサブコマンドスタブ（link, mount, unmount, cd, status, rules, doctor）
  - [x] Step 5: `whub status` 実装（マニフェスト読み→リソース状態表示）
  - [x] .yml → .yaml 統一（manifest, ADR, docs全体）

### Phase 2: symlink管理（FR-6, FR-7）
- [ ] manifest.yamlのsymlinkエントリに基づくリンク作成コマンド

### Phase 3: リモートマウント（FR-2）
- [ ] manifest.yamlのmountエントリに基づくsshfsマウントコマンド

### Phase 4: hub cd + リモート操作（FR-3, FR-6, FR-7）
- [ ] hub cd（symlink→ローカルcd、mount→SSH接続）
- [ ] hub shell-init（シェル関数生成）
- [ ] Tab補完

### Phase 5: 状態確認（FR-4）
- [ ] hub status（全リソースの状態一覧）

### Phase 6: Agentルール統合（FR-5）
- [ ] CLAUDE.mdのマーカー方式テンプレート作成
- [ ] hub rules deploy（マーカー範囲のみ置換 + settings.jsonマージ + skills/mcp上書き）
- [ ] 既存.my-boot install.shからの移行

## 実行ログ

（なし）

## 結果

（未完了）
