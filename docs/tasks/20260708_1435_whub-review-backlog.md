# whub実装改善バックログ消化（2026-07-03レビュー分）

## 目的・前提・方針案
- 目的: 2026-07-03コードレビュー指摘（backlog.md「whub 実装改善」）を消化する
- 前提: pytest移行済み・127件全パス（0.24s）。各項目は独立で既存テストを壊さず導入可能
- 方針: バグ候補を含むmanaged-block統合を最優先、次に効果の大きいControlMaster、最後に小粒修正を1バッチで



## 計画

### Phase 1: managed-blockロジック統合（3実装 → utils共通化）
- [x] `src/whub/utils/`新設。`render.py`もutilsへ移動し、補助責務の置き場を明確化
- [x] `src/whub/utils/managed_block.py`新設。boot `_managed_range`をベースに範囲検出＋置換/末尾挿入APIを提供（CRLF対応・重複マーカー検査を継承）
- [x] boot merge処理を新モジュール直接利用に置換（挙動不変、managed_block testで担保）
- [x] backlog `_insert_memo`を新モジュール利用に置換（ClickExceptionはコマンド層で維持）
- [x] link `_update_gitignore`をstart/endマーカー形式へ移行。旧形式（startのみ）ブロックは次回link時に新形式へ書き換え
- [x] link版バグ（ブロック直後に空行なしの行が消える）の再現テスト→修正確認テストを追加

### Phase 2: SSH ControlMaster導入
- [ ] `build_ssh_command`に`-o ControlMaster=auto -o ControlPath=<socket> -o ControlPersist=60s`を追加（ControlPath配置先は実装時に決定）
- [ ] rsyncのssh transport（`-e ssh ...`）にも同オプションを適用
- [ ] test_remote.pyのコマンド組み立てassertionを更新
- [ ] 実測: `whub status`のremote 1件あたり所要時間をbefore/afterで比較
- [ ] （任意・別コミット可）statusのhealth+gitの1コマンド結合、ThreadPool並列化

### Phase 3: 小粒修正バッチ
- [x] `build_rsync_command`のidentityパスをshlex.quoteで引用
- [x] backlogのremote失敗系がexit 0で終わる経路を特定し非ゼロ終了に修正
- [x] statusのgit列「-」を「git未設定」と「取得失敗」で表示区別
- [x] `--version`実装は低重要度のため今回スキップ
- [x] `_parse_due_date`年またぎ・link gitignore編集のテスト追加（後者はPhase 1で実施済み）
- [x] `whub link`をworkspace-hub外で実行した際のガード（別repoの.gitignore書き換え防止）
- [x] `backlog`の引数順序をtext-firstへ変更（`todo add`は変更不要と判断）

### Phase 4（保留・要判断）
- [ ] shell-init補完のファイルキャッシュ化（設計判断が要るため小粒から分離）
- [ ] backlogのworkspace-hub特別扱いとコンセプト文書の整合（文書修正か実装修正かの判断待ち）

## 実行ログ
### 試行 1: managed-blockをutilsへ統合
- 実施内容: `utils/managed_block.py`新設、`render.py`移動、boot/backlog/linkの管理ブロック処理をマーカーペアAPIへ統合
- 結果: link旧形式.gitignoreの後続行保持テストを追加し、`uv run pytest` 129件全パス
- 判断: 続行
### 試行 2: rsync identity path quote
- 実施内容: `build_rsync_command`のssh transport内identity pathを`shlex.quote`で引用し、空白入りパスのテストを追加
- 結果: `uv run pytest src/whub/tests/core/test_remote.py` 11件全パス
- 判断: 続行
### 試行 3: backlog remote失敗系の確認
- 実施内容: remote root/state/write失敗テストを追加し、`utils/process.py`でsubprocessエラー整形をboot/backlog共通化
- 結果: 非ゼロ終了とstderr/stdout由来メッセージを確認、`uv run pytest src/whub/tests/commands/test_backlog.py src/whub/tests/commands/test_boot.py` 15件全パス
- 判断: 続行
### 試行 4: status git取得失敗表示
- 実施内容: git未設定は`-`維持、local/remoteのgit取得失敗を`failed`表示へ変更
- 結果: `uv run pytest src/whub/tests/commands/test_status.py` 8件全パス
- 判断: 続行
### 試行 5: `--version`実装の要否確認
- 実施内容: CLI versionはmanifest schema versionとは別物であり、現時点の運用価値を再評価
- 結果: 低重要度のため今回スキップ
- 判断: 続行
### 試行 6: `_parse_due_date`年またぎテスト追加
- 実施内容: MMDDが今日と同日なら今年、過去日なら翌年になる境界テストを追加
- 結果: `uv run pytest src/whub/tests/commands/test_todo_cmd.py` 12件全パス
- 判断: 続行
### 試行 7: `whub link`実行場所ガード
- 実施内容: `Path.cwd() != whub_root()`ならClickExceptionで停止し、別repoの`.gitignore`更新を防止
- 結果: `uv run pytest src/whub/tests/commands/test_link.py` 7件全パス
- 判断: 続行
### 試行 8: `backlog`引数順序変更
- 実施内容: `whub backlog <text> <project>`へ変更し、複数語textはquote前提に整理（`todo add`は変更なし）
- 結果: `uv run pytest src/whub/tests/commands/test_backlog.py` 8件全パス
- 判断: 続行

## 結果
