# 目的・前提・方針案

- 目的: whubパッケージのテストを信頼できる仕様検証へ作り直す
- 前提: 既存テストはAI提案を無条件承認したもので、正しさの根拠にしない
- 根拠: `docs/whub-concepts.md`、現行実装、実際のCLI境界を優先する
- 現状: 既存discoverは62件OKだが、`cd/link/run/todo/render/tmux/target`など専用テストが薄い
- 範囲: 既存テストを最終的に全部置換し、旧テストは`tests_old`へ一括退避する
- 方針: 意味的基盤を優先し、外部副作用をmock境界に閉じて段階的に再作成する
- テスト方針: `docs/ADR/0009-test-specification-policy.md`に従う

# 計画

## Phase 1: テスト原則と対象範囲の確定
- [x] 現状のテスト件数・対象ファイル・未カバー領域を確認する
- [x] 全面刷新の範囲を「既存テストの全部置換」までに決める
- [x] 旧テストは`tests_old`へ一括退避し、参照のみ許可する方針に決める
- [x] private関数は副作用境界・複雑分岐に限って直接テストする方針に決める
- [x] whubの仕様根拠を`docs/whub-concepts.md`と実装から短く列挙する
- [x] 永続的なテスト仕様化ルールをADR-0009へ昇格する

## Phase 2: テスト基盤の再設計
- [x] 旧テストを`src/whub/tests_old`へ退避し、新`tests`を作る
- [x] 新`tests`を`models`/`commands`/`core`へ分割し、対象責務と対応させる
- [ ] manifest/resource/todo/temp workspaceの共通fixtureを作る
- [ ] SSH/sshfs/rsync/subprocess/ファイル書込のmock境界を統一する
- [ ] CLIは`CliRunner`、純粋関数は直接検証に分ける
- [ ] 領域ごとのケース提示と合意後実装の運用を守る

## Phase 3: 意味的基盤の再作成
- [x] `paths.py`の正常系・異常系を仕様から再検証する
- [x] manifest modelの正常系・異常系を仕様から再検証する
- [x] todo modelの正常系・異常系を仕様から再検証する
- [x] `tmux.py`/`render.py`の純粋関数テストを追加する
- [x] `remote.py`の純粋関数テストを追加する
- [x] `target.py`の純粋関数テストを追加する
- [x] `health.py`のmount/symlink判定を副作用mockで再検証する

## Phase 4: コマンド層の再作成
- [ ] `init/link/cd/run/fetch/mount/status/boot/roadmap/todo`の代表CLI振る舞いを検証する
- [ ] リモート系は実SSHを使わずargv・入力・失敗時表示を検証する
- [ ] 破壊的操作や実環境依存操作は一切実行しない

## Phase 5: 旧テストの参照と検証
- [ ] 旧テストを参照し、仕様根拠が確認できるものだけ新テストへ流用する
- [x] `uv run pytest`を標準検証にする
- [x] テスト名と配置を責務単位に整理する

# 実行ログ

### 仕様根拠メモ
- `paths`: `WHUB_ROOT`/`WHUB_DATA_DIR`を優先し、通常は`.whub/config.toml`の`data_dir`をSSOTにする
- `manifest`: `project`は`name`必須・`resource`任意、全`resource`は相対`workspace_path`必須にする
- `manifest`: `symlink.source`と`remote.path`は絶対パスにし、remote host参照とproject/workspace重複を拒否する
- `todo`: projectにresourceがなくてもtodoを持て、todoは単発アクションとして保存・分類できる
- `target`: コマンドはproject/resourceをtarget入力へ整形し、local/remote呼び分けはtarget層が担う
- `remote`: SSH/rsync/sshfs/scpの低レイヤーargv生成だけを担い、projectの意味は持たない
- `health`: symlink/mountの健全性検査を集約し、mount table不明時はstale扱いにする
- `tmux`: remote cd用のセッション命名とリモートシェルsnippetの組み立てだけを担う
- `render`: CLI表出力の幅・色・右寄せだけを担い、ドメイン判断を持たない

### 試行 1: 旧テストを退避して新testsを開始する
- 実施内容: `src/whub/tests`を`src/whub/tests_old`へ移動し、新`tests/__init__.py`を作成
- 結果: 旧テストは参照用に残り、新テスト領域は空から開始
- 判断: 続行

### 試行 2: テストケースの合意前に実装を進めた
- 実施内容: `helpers.py`と`test_paths.py`を先行作成
- 結果: 旧テストと同じ承認構造になる懸念が出た
- 判断: 方針変更

### 試行 3: テスト仕様化ルールをADRへ昇格する
- 実施内容: 永続ルールを`docs/ADR/0009-test-specification-policy.md`へ抽出
- 結果: task mdはADR参照に寄せ、個別計画だけを残した
- 判断: 続行

### 試行 4: pathsテストを実行する
- 実施内容: `uv run python -m unittest src.whub.tests.test_paths`
- 結果: 3件OK
- 判断: 続行

### 試行 5: linkのcwd依存を既知問題としてroadmapへ記録する
- 実施内容: workspace-hub外で`whub link`が別repoの`.gitignore`を書き換える可能性を追記
- 結果: `docs/roadmap.md`の小粒の修正に記録
- 判断: 続行

### 試行 6: manifestテストを実装・実行する
- 実施内容: 合意済み8ケースで`src/whub/tests/test_manifest.py`を追加
- 結果: `uv run python -m unittest discover -s src/whub/tests`で11件OK
- 判断: 続行

### 試行 7: todo modelテストを実装・実行する
- 実施内容: storageを除く合意済み6ケースで`src/whub/tests/test_todo_model.py`を追加
- 結果: `uv run python -m unittest discover -s src/whub/tests`で17件OK
- 判断: 続行

### 試行 8: targetテストを実装・実行する
- 実施内容: 合意済み9ケースで`src/whub/tests/test_target.py`を追加
- 結果: `uv run python -m unittest discover -s src/whub/tests`で26件OK
- 判断: 続行

### 試行 9: remoteテストを実装・実行する
- 実施内容: 合意済み10ケースで`src/whub/tests/test_remote.py`を追加
- 結果: `uv run python -m unittest discover -s src/whub/tests`で36件OK
- 判断: 続行

### 試行 10: tmux/renderテストを実装・実行する
- 実施内容: 合意済み6ケースの`test_tmux.py`と最小5ケースの`test_render.py`を追加
- 結果: renderのANSI直接確認は非TTYで失敗したため`click.style`呼び出し確認へ変更し、全体47件OK
- 判断: 続行

### 試行 11: healthテストを実装・実行する
- 実施内容: 合意済み12ケースで`src/whub/tests/test_health.py`を追加
- 結果: `uv run python -m unittest discover -s src/whub/tests`で59件OK
- 判断: 続行

### 試行 12: テスト配置とランナーを整理する
- 実施内容: `tests/models`/`tests/core`へ既存テストを移動し、pytest形式へ移行
- 結果: `uv run pytest`で59件OK
- 判断: 続行

# 結果
