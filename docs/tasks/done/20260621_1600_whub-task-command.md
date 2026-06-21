# whub todo コマンド — タスク管理

## 目的・前提・方針案

### 目的
`whub todo`: 個人のやることリストをCLIから一元管理

### 前提
- 既存CLI: Click + `src/whub/commands/` 配下に1コマンド1ファイル
- `mind/tasks.md` にObsidian起点の試行痕跡あり（別管理として共存、マイグレーションしない）
- AI非依存であることが選定理由（Claude Skillではなく純CLIを選択）
### 用語定義
| 用語 | 意味 | 備考 |
|------|------|------|
| resource | manifestで管理されるワークスペース（symlink/mount） | コード・データ上の正式名称 |
| todo | 個人の離散的アクションアイテム | `whub todo` で管理 |

---

## 要件

### A. whub todo

#### UX仕様
- エントリポイント: `whub todo`（サブコマンド・オプションなし）
- 起動すると矢印キー選択のインタラクティブUIが立ち上がる
- TUI: Python標準ライブラリ `curses` で実装（外部依存なし）

#### 画面構成
```
$ whub todo

  > Add new todo
    1. タスクA        esn-lab    (2026-06-20)
    2. タスクB        ──         (2026-06-21)
    View completed
```

- **初期カーソル**: 「Add new todo」に合わせた状態
- **Add new todo**: Enter → タイトル入力 → resource選択（任意） → 登録
- **各todo**: Enter → Done or Delete を選択
- **View completed**: Enter → 完了済み一覧を表示

#### 番号の採番ルール
- 永続IDは持たない（表示時に動的に振る）
- 未完了一覧: 上から昇順に 1, 2, 3, ...
- 完了済み一覧: 同様に 1, 2, 3, ...

#### ストレージ
- **保存先**: `~/.whub/todos.yaml`
- whub単体で動作、外部サービス非依存
- `~/.whub/` をgitリポジトリ化すればマシン間共有も可能

#### データ形式
```yaml
todos:
  - title: "シミュで箱掴む"
    done: false
    created_at: "2026-06-21"
    done_at: null
    resource: "la-imitation"   # manifest resource name (nullable)
    priority: "yellow"          # red / yellow / blue (nullable)
```

#### フィールド定義
| フィールド | 型 | 自動/手動 | 備考 |
|-----------|-----|----------|------|
| title | str | 手動 | add時に入力 |
| done | bool | 自動 | false→true（done操作時） |
| created_at | date | 自動 | add時に自動記録 |
| done_at | date\|null | 自動 | done時に自動記録 |
| resource | str\|null | 手動 | manifest resource name。null許容 |
| priority | str\|null | 手動 | red / yellow / blue。null許容 |

#### 将来拡張（MVP外）
- label: 活動種別タグ（💻🔍🤝🧠 等）
- due: 締切日

---

### 非機能要件
1. AI非依存 — CLIコマンドのみで完結
2. 既存の `whub` コマンド体系（Click group）に統合
3. `~/.whub/todos.yaml` が存在しなければ初回起動時に自動生成

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
