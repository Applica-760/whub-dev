# roadmap → backlog 改名

## 目的・前提・方針案
- 目的: `roadmap`という名前が実態に沿っていないため、project固有の未整理入力・作業候補を表す`backlog`へ更新する
- 前提: 現在の`roadmap`は長期計画ではなく、project固有の構想や「次にやりたいこと」の投入口として使われている
- 方針: 命名・CLI・文書・Skill参照を実態に合わせて整理する

## 計画
## Phase 1: 方針確定
- [x] `roadmap`は互換なしで`backlog`へ完全置換する
- [x] 既存`docs/roadmap.md`は`docs/backlog.md`へリネームして内容も刷新する
- [x] マーカーは`hub:backlog:appended`へ更新し、旧マーカー互換は持たない
- [x] vault側の`roadmap`参照も今回更新する
- [x] 未完了タスク内の`roadmap`表記だけ更新し、完了済み履歴は触らない

## Phase 2: 実装更新
- [x] `roadmap`コマンド実装を`backlog`へリネームし、CLI登録・出力・エラー文言を更新する
- [x] 追記先を`docs/backlog.md`へ変更し、新テンプレートとマーカーを適用する
- [x] 旧`roadmap`コマンド・旧ファイル名・旧マーカー前提のコードを除去する

## Phase 3: テスト更新
- [x] `test_roadmap.py`を`backlog`仕様へリネーム・更新する
- [x] local/remote/workspace-hub/空メモの既存ケースを`backlog`仕様で維持する

## Phase 4: 文書・運用データ更新
- [x] README、`docs/whub-concepts.md`、`docs/workflow.md`を`backlog`前提へ更新する
- [x] `.agents/skills`、`.claude/skills`、vault側の`roadmap`参照を`backlog`へ更新する
- [x] 未完了タスクmdの`roadmap`表記を必要範囲で更新する

## Phase 5: 検証
- [x] `uv run pytest src/whub/tests/commands/test_backlog.py`でコマンド単体を検証する
- [x] 必要に応じて`uv run pytest`で回帰確認する

## 実行ログ

## 結果
- `whub roadmap`を互換なしで`whub backlog`へ置換し、追記先を`docs/backlog.md`へ更新した
- README、docs、`.agents/skills`、`.claude/skills`、vault側、未完了task mdを`backlog`前提へ更新した
- 検証: `uv run pytest src/whub/tests/commands/test_backlog.py` 5 passed、`uv run pytest` 127 passed
