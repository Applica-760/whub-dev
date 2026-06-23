# 目的・前提・方針案

whub statusを拡充し、既存のヘルスチェックに加えてgit差分ファイル数を表示する。
remoteは`run_ssh_command()`で1回のSSHにヘルス確認とgit情報を統合し、`concurrent.futures`で全リソースを並列取得する。
state.yaml接続・編集機能は後続Phaseとして計画に含めるが、今回はPhase 1のみ実施。

出力イメージ:
```
mind            symlink  ok           3 files
laplust-docs    symlink  ok           -
esn-lab         remote   ok           0 files
esn-lab-run     remote   unreachable  -
```

# 計画

## Phase 1: git差分表示 + 並列取得

- [x] Step1: `_fetch_symlink_info()` / `_fetch_remote_info()` を `status.py` に追加
  - symlink: `subprocess.run(["git", "-C", source, "status", "--porcelain"])` → 行数
  - remote: 1回SSH `test -d <path> && git -C <path> status --porcelain` でhealth+git統合取得。`inspect_remote()`は変更なし
  - git定義なし → `None`、ヘルス異常 → `None`
- [x] Step2: symlink逐次 + remote のみ `ThreadPoolExecutor` で並列取得。`boot: true` のリソースのみ対象
- [x] Step3: 表示を4列に更新 `{name}  {type}  {health}  {git_diff}`。git_diff: `N files` or `-`
- [ ] Step4: `src/whub/tests/test_status.py` 新設。subprocess/SSHモックで正常系・異常系検証
- [x] Step5: 実環境で動作確認

## Phase 2: State/GitInfo接続

- [x] `state.yaml`のstatus text / priorityを表示に統合
- [x] priority emoji表示
- [x] manifest version検証 → 不要と判断。現状`version: "1"`固定で検証の実益なし
- [x] doctor → 空実装のためCLI登録削除で決着

## Phase 3: status編集機能

- [x] `-e <resource> "text"`でstatus textを更新
- [x] `-p <resource> <priority>`でpriorityを更新
- [x] manifestとのresource名バリデーション
- [x] resource / priority の tab補完（`resource_names` + `click.Choice(PRIORITIES)`）
- [x] `Priority` Literal → `get_args()` で `PRIORITIES` 導出。SSOT化
- [x] `status()` 本体を `_show_status()` / `_update_state()` に分離
