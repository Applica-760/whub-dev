# 目的・前提・方針案

## 目的
uv系パッケージ管理コマンドをClaude Codeの許可リストに追加し、パッケージ操作時のApprove手間を削減する。
`whub boot deploy`の共通設定（`src/whub/boot/json/.claude/settings.json`）に採用するか検討・決定する。

## 前提
- 現在のboot settings.jsonは読み取り系コマンドとCodeGraph MCPのみ許可
- `uv run` / `uv tool run` / `uvx` は任意コマンド実行が可能なため、許可してはならない
- Claude Code許可パターンは `Bash(uv add:*)` のようにサブコマンド単位で記述可能
- boot設定はJSON再帰マージで既存設定と統合される（既存の許可は消えない）

## 方針案
- 安全なuvサブコマンドのみをホワイトリスト方式で許可する
- boot配布設定に含め、全プロジェクト共通で適用する（uvを使わないプロジェクトでも害はない）

# 計画

## Phase 1: 許可対象コマンドの選定
- [ ] 下記の分類を精査し、許可リストを確定する

### 許可候補（安全）
| コマンド | 用途 | リスク |
|----------|------|--------|
| `uv add` | 依存関係追加 | 低：pyproject.tomlとlockfileの変更のみ |
| `uv remove` | 依存関係削除 | 低：同上 |
| `uv sync` | lockfileに基づく環境同期 | 低：宣言済みパッケージのインストールのみ |
| `uv lock` | lockfile生成・更新 | 低：ファイル生成のみ、インストールなし |
| `uv venv` | 仮想環境作成 | 低：ディレクトリ作成のみ |

### 要検討
| コマンド | 用途 | リスク |
|----------|------|--------|
| `uv pip install` | pip互換インストール | 中：悪意あるパッケージのsetup.py実行の可能性 |
| `uv pip uninstall` | pip互換アンインストール | 低：削除のみ |
| `uv init` | プロジェクト初期化 | 低：ファイル生成のみだが、既存構造との干渉あり得る |

### 除外（許可しない）
| コマンド | 理由 |
|----------|------|
| `uv run` | 任意コマンド・スクリプト実行 |
| `uv tool run` / `uvx` | 任意ツール実行 |
| `uv tool install` | グローバルツールインストール（意図しない副作用） |

## Phase 2: boot settings.jsonへの反映
- [ ] Phase 1で確定したコマンドを `src/whub/boot/json/.claude/settings.json` に追加
- [ ] パターン記法の動作確認（`Bash(uv add:*)` で `uv add requests` 等がマッチするか）

## Phase 3: 配布と検証
- [ ] `whub boot deploy` で既存プロジェクトへ配布
- [ ] 配布先でuv操作がApproveなしで実行されることを確認
- [ ] `uv run` が依然としてApprove要求されることを確認

# 実行ログ

# 結果
