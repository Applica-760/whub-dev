# ADR-0006: Agentルール配布方式

- **Status:** Accepted
- **Date:** 2026-06-19

## Context

.my-bootの`install.sh`は`rsync -a`で`.claude/`ディレクトリを丸ごとコピーしており、プロジェクト固有のCLAUDE.md内容やsettings.jsonの追加設定を上書きしてしまう。`hub boot deploy`ではプロジェクト固有の記述を保護しつつ、共通ルールを更新できる仕組みが必要。

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

CLAUDE.md と同じマーカー方式。`codex/AGENTS.md` をソースとし、プロジェクトルートの `AGENTS.md` にマーカー範囲のみ置換する。

### その他 — 上書き方式

| ファイル | 戦略 |
|----------|------|
| `skills/*` | 上書き（常に最新化） |
| `.mcp.json` | 上書き |
| `.codex/` | 上書き |

## Rationale

- CLAUDE.mdの全体上書きではプロジェクト固有の概要・指示が消えてしまい、毎回手動で復元する必要がある
- マーカー方式はsedやPythonで容易に実装でき、マーカーが壊れた場合も検出可能
- settings.jsonのpermissionsはプロジェクトによってBash許可範囲が異なるため、マージが必要

## Consequences

- CLAUDE.mdにHTMLコメントのマーカーが残る（表示には影響しない）
- マーカーが手動で削除された場合、deployは共通部分を更新できない → `hub doctor`で検出する
- .my-bootの`install.sh`はスタンドアロン用途として現行維持する（workspace-hub外での単体利用向け）
- workspace-hub配下では`hub boot deploy`を使用する
