# 実行仕様書: Task 104 App Server 結合検証

## 目的
- 未マージの `tasks/104` が worktree ごとに Codex App Server を管理し、Web UI から prompt、応答、コマンド承認を完結できることを確認する。

## 背景・前提
- 対象 worktree は ``、対象は `whub-dev/TASK-104` である。
- `whub agent open` は対象 worktree を cwd とする Codex App Server を起動し、`whub agent close` はその App Server と tmux session を停止する。
- tmux は Codex 実行系から独立した汎用 Shell として維持する。
- 未マージの実装を使うため、すべての `whub` 操作は対象 worktree で `uv run whub` として実行する。
- `agent close` は対象 Task の tmux session を停止するため、現在の session 外で実行する。

## 対象範囲
- App Server の起動、単一 thread の prompt 送信、ストリーミング応答、コマンド承認、Explorer の承認待ち表示、Browser Notification、close cleanup を検証する。
- `app/src/features/terminal/CodexPanel.tsx` の最小会話 UI と `src/whub/services/agent/app_server.py` の状態連携を対象とする。

## 非対象範囲
- 本格的な会話 UI、複数 thread の選択・履歴管理、tmux 内からの Codex 対話、Main への merge、worktree の作成・削除、Task YAML の更新、release は行わない。
- `.codex/config.toml`、Agent 認可 asset、App Server のプロトコル状態を手編集しない。

## 変更要件
- `agent open` 後に対象 worktree の App Server が利用可能となり、Web UI はその単一 thread の状態を表示すること。
- Web UI で送信した prompt の Codex 応答が表示されること。
- コマンド承認要求で内容と allow/deny 操作を表示し、応答後に承認待ちを解除すること。
- App Server の承認待ちが既存の Explorer badge、banner、既読化、Browser Notification に反映されること。
- `agent close` 後に App Server が停止し、Harness 所有の設定だけが cleanup されること。

## 実装方針
- source worktree の `uv run whub app dev` を起動し、同一の localhost Web app で Agent 状態と承認を確認する。
- source worktree の `uv run whub agent open whub-dev TASK-104 --auth implementer` により、App Server と検証用 tmux session を開く。

## 受け入れ基準
- [ ] `agent open` 後に Browser の Terminal 画面で対象 worktree の Agent パネルを表示できる。
- [ ] Agent パネルから prompt を送信すると Codex 応答が表示される。
- [ ] `uv run pytest src/whub/tests/services/agent/test_attention.py` の実行を依頼すると、強いコマンドの承認要求が Agent パネル、Explorer badge、banner に表示される。
- [ ] Agent パネルで許可すると command が実行され、承認待ちが解除される。
- [ ] Agent パネルで拒否すると command は実行されず、承認待ちが解除される。
- [ ] banner の `Terminalを開く` または対象 worktree 行を選ぶと、対象 Terminal が開き、badge と banner が既読化される。
- [ ] Browser Notification が許可済みの場合、tab 非表示中の新規承認待ちで通知される。
- [ ] `agent close` 後に App Server が停止し、Harness 所有の生成物だけが cleanup される。

## 検証条件
- control shell で対象 worktree へ移動し、次を順に実行する。

```sh
uv run whub agent close whub-dev TASK-104
uv run whub app dev
uv run whub agent open whub-dev TASK-104 --auth implementer
```

- Browser で `http://127.0.0.1:8712/terminal` を開き、`whub-dev / TASK-104` を選択して Agent パネルから prompt を送信する。
- 承認表示を確認する場合は、Codex に `uv run pytest src/whub/tests/services/agent/test_attention.py を実行して承認を要求する` と依頼する。
- Browser Notification は browser 側で permission を許可してから、Terminal tab を非表示にして新しい承認要求を発生させる。
- 検証後は control shell で次を実行し、tmux session、App Server、dev app を停止する。

```sh
uv run whub agent close whub-dev TASK-104
uv run whub app down --dev
```

## リスク・注意点
- Codex App Server の起動・認証に失敗した場合は、Agent パネルから turn を開始できない。
- `agent close` が生成物の内容変更を検出した場合は cleanup を停止するため、手編集せずエラーと対象ファイルを報告する。
- Browser Notification は browser permission が未許可なら検証できないため、未許可の場合は未実施として記録する。
- 承認要求が発生しない prompt は allow/deny の受け入れ基準を検証できない。

## 不明点・確認事項
- Browser Notification の permission を今回の検証環境で許可できない場合は、Agent 応答、承認表示、allow/deny、既読化、cleanup までを必須結果とする。
