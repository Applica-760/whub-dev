# ADR-0008: ツールとデータのプレーン分離（whub / vault）

- **Status:** Accepted
- **Date:** 2026-07-06

## Context

- `manifest.yaml`・`todos.yaml`がworkspace-hub repoにコミットされており、個人データ（自宅サーバIP・スパコンホスト名・個人todo）がツールのリポジトリに混入していた
- 個人ナレッジ（旧mind repo）とwhubの運用データが別々の場所にあり、タスク管理も2系統（`todos.yaml`と`tasks.md`）に分裂していた
- 「これさえ見ればいい」と言える単一の自己データ置き場が欲しい。一方でwhub自体は将来公開する可能性がある

## Decision

- **workspace-hub＝ツール・機能基盤（公開可能）、vault＝私の固有記述の貯蔵庫（private）** としてプレーンを分離する
- vaultは旧mind repoを転用・改名し、知識プレーン（`inbox/` `literature/` `concepts/` `permanent/` `daily/`）と機械プレーン（`whub/`: `manifest.yaml`・`todos.yaml`）を収容する
- 機械プレーン`whub/`は全project横断のwhub基盤（config・状態）に限る。単一ドメインのコンテンツ索引は当該知識ドメイン配下に置く（例: 外部ソース取り込みログは`literature/log.jsonl`）
- workspace-hubの`.whub/config.toml`にdata_dirを登録し、CLIはその先の`manifest.yaml`・`todos.yaml`等を読む
- Obsidian互換は維持しない。プレーンなmarkdown＋相対リンクで管理し、特定エディタに依存しない
- 今後whubの新機能が持つ自己データ（ログ・キャプチャ等）も原則vaultに置く。**whubはvaultを読み書きする入口に徹する**

## Rationale

- 「これさえ見ればいい」の本体はrepo統合ではなくデータの一元化。repo統合はコードと個人コンテンツのgit履歴が混在し、公開の道を塞ぐ
- data_dirをパス登録にすることで、vault固有パスをパッケージへハードコードせず、symlink媒介も不要にできる
- todo×2・inbox×2のような重複が生まれた際、「私のデータはvault」という一貫した解消原則になる

## Consequences

- workspace-hubのgit履歴には過去のmanifest等が残る。実公開時は履歴のscrubまたは新repo化が必要
- vaultはprivate必須。boot配布対象としては従来のmind同様に扱う
- `whub fetch`の保存先はdata_dirの`downloads/`となるため、data_dir側でgitignoreする
- `tasks.md`と`todos.yaml`の統合、recruit由来文書（志向・自己分析）のvaultへの集約は後続タスク
