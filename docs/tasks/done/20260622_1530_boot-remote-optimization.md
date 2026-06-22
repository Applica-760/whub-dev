# 目的・前提・方針案

## 目的
`whub boot` のリモート（mount）リソースに対する実行速度を改善する。

## 前提
- 現状、ファイルデプロイ（`_deploy_to_project`）とCodeGraph init（`_init_codegraph`）はすべてsshfsマウントポイント経由のファイルI/Oで実行されており、ネットワークRTTがファイル数・リポジトリサイズ分だけ累積する
- 最大ボトルネックはCodeGraph init（リポジトリ全体スキャン × sshfs）
- 対象リソース: `esn-lab`, `la-imitation-learning`（ともにhome-server、boot=true）
- `build_ssh_command()` ヘルパーが既存（`__init__.py:23-40`）

## 方針
- CodeGraph initとファイルツリーコピー（`_copy_tree`）をSSH経由のリモート実行に変更
- `_deploy_marked` / `_merge_settings` のマージ処理はsshfs経由のまま残す（既存ファイルとの差分統合が必要なため）
- リモートにcodegraphが未インストールの場合はスキップ（既存のフォールバックと同様）

# 計画

## Phase 1: ファイルデプロイのリモート実行化
- [x] `_deploy_to_remote` を追加。`rsync -a -e ssh` で単純コピー対象を転送
- [x] マージ処理（`_deploy_marked`, `_merge_settings`）はsshfs経由のまま残す

## Phase 2: CodeGraph initのリモート実行化
- [x] `_init_codegraph_remote` を追加し、`boot()` からMountResource判別で呼び分ける
- [x] 非対話SSHではnvmのPATHが通らないため、`source "$HOME/.nvm/nvm.sh"` で解決

## Phase 3: 検証
- [x] home-serverマウント状態で `whub boot` を実行し、エラーなく完了することを確認
- [x] リモート側のファイルが正しく配置されていることを確認

# 実行ログ

### 試行 1: tar+sshでファイルデプロイ
- 実施内容: tarアーカイブをSSH経由でパイプする方式を実装
- 結果: ユーザから過剰と指摘。rsync方式に変更
- 判断: 棄却

### 試行 2: bash -lcでcodegraph PATH解決
- 実施内容: `bash -lc` でログインシェルとして実行
- 結果: `.bashrc`の非対話ガードでnvm初期化がスキップされ、command not found
- 判断: 方針変更 → `source "$HOME/.nvm/nvm.sh"` で直接解決

# 結果
- MountResourceに対するファイルデプロイを `rsync -a -e ssh` に変更し、速度を大幅改善
- CodeGraph initを `_init_codegraph_remote` でSSH経由リモート実行に変更
- マージ処理（`_deploy_marked` / `_merge_settings`）はsshfs経由で据え置き
