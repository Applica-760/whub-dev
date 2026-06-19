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
- [ ] マニフェストの詳細スキーマ設計
- [ ] CLIのサブコマンド体系
- [ ] FR-5: Agentルール配布の仕組み（.my-bootからの移行方式）

### Phase 1: 基盤構築
- [ ] git init + .gitignore整備
- [ ] マニフェストスキーマ設計・ADR化
- [ ] CLIの骨組み作成（pyproject.toml + エントリポイント）

### Phase 2: symlink管理（FR-6, FR-7）
- [ ] manifest.ymlのsymlinkエントリに基づくリンク作成コマンド

### Phase 3: リモートマウント（FR-2）
- [ ] manifest.ymlのmountエントリに基づくsshfsマウントコマンド

### Phase 4: リモート操作（FR-3）
- [ ] exec / sshコマンド

### Phase 5: 同期・コンテキスト生成（FR-1, FR-4）
- [ ] Git一括同期（gitタイプ追加時）
- [ ] 状態サマリー自動生成

### Phase 6: Agentルール統合（FR-5）
- [ ] .my-bootからの移行

## 実行ログ

（なし）

## 結果

（未完了）
