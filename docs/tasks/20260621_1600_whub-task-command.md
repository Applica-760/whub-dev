# whub task コマンド — タスク管理機能

## 目的・前提・方針案

### 目的
`whub task` コマンドで、プロジェクト横断のタスク/ToDoをCLIから一元管理する。

### 前提
- 既存CLI: Click + `src/whub/commands/` 配下に1コマンド1ファイル
- `mind/tasks.md` にObsidian起点の試行痕跡あり（別管理として共存、マイグレーションしない）
- AIツール非依存であることが選定理由（Claude Skillではなく純CLIを選択）

---

## 要件

### UX仕様
- エントリポイントは `whub task` のみ（サブコマンド・オプション一切なし）
- 起動すると矢印キー選択のインタラクティブUIが立ち上がる
- TUI: 外部依存なし。Python標準ライブラリ `curses` で実装

### 画面構成
```
$ whub task

  > Add new task
    1. タスクA        (2026-06-20)
    2. タスクB        (2026-06-21)
    View completed tasks
```

- **初期カーソル**: 「Add new task」に合わせた状態
- **Add new task**: Enter → タスク名の入力プロンプト → 登録（created_at 自動付与）
- **各タスク**: Enter → タスクリスト上で矢印キーで対象選択 → Done or Delete を選択（done_at 自動付与）
- **View completed tasks**: Enter → 完了済みタスク一覧を表示（番号は完了済み全体で1から振り直し）

### タスク番号の採番ルール
- 永続IDは持たない（表示時に動的に振る）
- 未完了タスク一覧: 上から昇順に 1, 2, 3, ...
- 完了済みタスク一覧: 完了済み全体で上から昇順に 1, 2, 3, ...

### ストレージ
- **保存先**: `~/.whub/tasks.yaml`
- whub単体で動作、リソース非依存
- `~/.whub/` をgitリポジトリ化すればマシン間共有も可能

### データ形式（YAML）
```yaml
tasks:
  - title: "タスク名"
    done: false
    created_at: "2026-06-21"
    done_at: null
```

### MVPフィールド
| フィールド | 型 | 自動/手動 | 備考 |
|-----------|-----|----------|------|
| title | str | 手動 | タスク名（add時に入力） |
| done | bool | 自動 | false→true（done操作時） |
| created_at | date | 自動 | add時に自動記録 |
| done_at | date\|null | 自動 | done時に自動記録 |

### 将来拡張（MVP外）
- category: カテゴリタグ
- due: 締切日
- project: 紐づくリソース/プロジェクト

### 非機能要件
1. AI非依存 — CLIコマンドのみで完結
2. 既存の `whub` コマンド体系（Click group）に統合
3. `~/.whub/tasks.yaml` が存在しなければ初回起動時に自動生成

---

## 未決定事項

（すべて決定済み — 計画策定可能）

---

## 計画

（要件確定後に策定）

## 実行ログ

（実装開始後に記録）

## 結果

（完了後に記録）
