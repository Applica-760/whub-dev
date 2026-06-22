# リモートマウントのAppleDouble対策

## 目的・前提・方針案

- macOSからsshfs/FUSEマウントへアクセスした際の`._*`生成と、`whub boot`のリモート全体走査による停止を解消する
- sshfsマウントオプションで`._*`生成を根本抑止し、bootの再帰走査・削除を廃止する
- codegraph initにtimeoutを設け、1対象の停止で後続を塞がないようにする

## 計画

### Phase 1: sshfsマウントオプション追加
- [x] `build_sshfs_command`に`noappledouble`,`noapplexattr`,`defer_permissions`を追加（`src/whub/commands/__init__.py`）

### Phase 2: bootの再帰走査廃止
- [x] `_clean_apple_double`関数と`_deploy_to_project`からの呼び出しを削除（`src/whub/commands/boot.py`）

### Phase 3: codegraph initにtimeout追加
- [x] `_init_codegraph`の`subprocess.run`にtimeout=60を設定（`src/whub/commands/boot.py`）

### Phase 4: 検証・既存`._*`の一括削除
- [x] `whub mount`→`whub boot`が停止せず完了することを確認
- [x] リモートマウント上の既存`._*`をSSH先で手動一括削除

## 実行ログ

### 試行 1: CodeGraph初期化が停止原因
- 実施内容: 停止中プロセス、出力位置、`.codegraph`生成有無を確認した
- 結果: `esn-lab`の`done`前でCodeGraph子プロセスもなく、配布処理内で停止していた
- 判断: 棄却

### 試行 2: AppleDouble全体清掃がリモートI/Oを増大
- 実施内容: boot実装とマウント状態を確認し、対象全体の`rglob("._*")`を特定した
- 結果: NFS/FUSE越しにリポジトリ全体を同期走査するため、配布量11ファイル・44KBと無関係に停止し得る
- 判断: 続行

## 結果

- sshfsに`noappledouble`+`noapplexattr`+`defer_permissions`を追加し、`._*`生成を根本抑止
- `_clean_apple_double`（`rglob("._*")`による全走査・削除）を廃止し、bootのリモートハングを解消
- `_init_codegraph`にtimeout=60sを追加し、1対象の停止で後続が塞がれないようにした
- 既存`._*`はSSH先で手動削除済み
