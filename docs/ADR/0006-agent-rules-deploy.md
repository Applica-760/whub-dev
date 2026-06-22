# ADR-0006: Agentルール配布方式

- **Status:** Accepted
- **Date:** 2026-06-19

## Context

whubパッケージ内の共通設定を配布しつつ、プロジェクト固有のCLAUDE.md・AGENTS.md・settings.json・.gitignoreを保護する必要がある。

## Decision

配布対象ファイルごとに更新戦略を分ける。

### CLAUDE.md — マーカー方式（部分置換）

共通部分を`<!-- hub:managed:start -->` / `<!-- hub:managed:end -->`で囲み、deploy時はマーカー範囲のみ置換する。マーカー外はプロジェクト側が自由に記述でき、deployで触らない。

```markdown
<!-- hub:managed:start -->
# 注意事項
（共通内容）

# Skills早見表
（共通内容）
<!-- hub:managed:end -->

# 概要
（プロジェクト固有 — deployで保護される）
```

初回配布時はマーカー付きテンプレート全体をコピーする。

### settings.json — マージ方式

- `permissions.allow`: 共通ベースをマージ（既存のプロジェクト固有エントリを消さない）
- `hooks`: 共通hookで上書き

### AGENTS.md — マーカー方式（部分置換）

CLAUDE.md と同じマーカー方式。パッケージ内の`AGENTS.md`をソースとし、プロジェクトルートの`AGENTS.md`にマーカー範囲のみ置換する。

### .gitignore — マーカー方式（部分置換）

`# hub:managed:start` / `# hub:managed:end`の範囲のみ置換する。

### その他 — 上書き方式

| ファイル | 戦略 |
|----------|------|
| `.claude/`内のその他 | 上書き（既存の固有ファイルは削除しない） |
| `.mcp.json` | 上書き |
| `.codex/` | 上書き（既存の固有ファイルは削除しない） |

## Rationale

- CLAUDE.mdの全体上書きではプロジェクト固有の概要・指示が消えてしまい、毎回手動で復元する必要がある
- マーカー方式はsedやPythonで容易に実装でき、マーカーが壊れた場合も検出可能
- settings.jsonのpermissionsはプロジェクトによってBash許可範囲が異なるため、マージが必要

## Consequences

- CLAUDE.mdにHTMLコメントのマーカーが残る（表示には影響しない）
- 配布先にマーカーがない場合は共通ブロックを先頭へ挿入する
- マーカーの重複・片側欠損・逆順はエラーとする
- 配布資産は`importlib.resources`で参照し、外部リポジトリへ依存しない
