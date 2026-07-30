# Agent authorization

## Decision

Agentに付与する権限の再利用可能な定義を `agent auth` と呼ぶ。

`base agent auth` はすべてのAgent実行に適用し、非破壊的な参照・確認コマンドだけを許可する。用途ごとに選択する `extension agent auth` は、許可する行動を追加する。

agent authはcommand、filesystem、network、外部ツールを対象とする。すべての権限はホワイトリストとして定義する。

## Meaning

- `agent auth` はAgentの責務や人格ではなく、権限だけを表す。
- `base agent auth` は常に一つ適用する。
- `extension agent auth` は一つ以上選択できる。
- 「適用profile」は用語として使わない。base agent authと選択したextension agent authをそのまま扱う。

## Derived behavior

- Agentに付与される権限は、base agent authと選択したextension agent authの和集合である。
- extension agent authは許可する行動を追加するだけであり、既存の規定を緩めない。
- どのagent authにも記載されない行動に、権限は与えない。
- extension agent authの選択順序は権限の意味を変えない。

## Machine-readable assets

開発時のagent authは`src/whub/assets/roles`に配置する。常に一つ適用するbase agent authは
`base.yaml`とする。extension agent authは`<name>/agent-auth.yaml`とし、Agentへの
役割指示が必要なextensionだけ同じディレクトリに`description.md`を置く。base agent authに
`description.md`は置かない。

`grants.network.policy`は現在`deny_all`だけを受け付け、network accessを許可しない。

`variables`はroleの権限評価に使う、adapterが解決または検証する値である。
`registered_task_worktree`は、現在のAgentに割り当てられた登録済みworktreeから`project`、`task`、`path`を
解決する。未解決または複数候補の場合、adapterは実行を拒否する。
`registered_project`はargvの値がwhubに登録済みのProject名であることを検証し、未登録なら実行を拒否する。

`grants.commands.prefixes`と`grants.commands.exact`は、固定`executable`と順序付きの`arguments` token列でargvを
許可する。argumentsの各tokenはliteralまたは`$current_worktree.project`のような変数参照であり、文字列結合およびshell展開は行わない。

`grants.extension_tools`はHubに登録された外部ツールIDの集合である。外部ツールの接続定義はcatalogで管理する。
CodeGraph catalogの`tools`は許可する固定MCP tool名の集合である。

- `id`: MCP serverの設定名
- `transport`: 接続方式。MVPではローカルプロセスの`stdio`だけを扱う。
- `tools`: 許可するMCP toolの固定名の配列

CodeGraphは`stdio`の外部ツールとしてbase agent authに含める。`codegraph_explore`、
`codegraph_search`、`codegraph_node`、`codegraph_callers`、`codegraph_callees`、
`codegraph_impact`、`codegraph_files`、`codegraph_status`だけを許可する。CodeGraph MCPは
ローカルプロセスであり、network権限を必要としない。

## Task operation boundary

implementerはTask YAMLを直接編集せず、対応Taskに束縛した`wflow task`操作を使う。
`wflow task --project PROJECT`は実行cwdに依存せず、登録済みProjectのcontent rootにある
`docs/tasks/`を操作する。本元のTask YAMLがSSOTであり、worktree内に残るTask YAMLの
スナップショットは更新対象ではない。

この直接編集禁止は現在はAgentへの指示であり、profileのcommand allowlistだけでは強制しない。
adapter/harnessは後続Taskで、本元Task YAMLへのraw writeを拒否し、許可済み`wflow`操作だけを
通す境界として実装・検証する。

## Filesystem authorization

`grants.filesystem.read`と`grants.filesystem.write`は、それぞれの操作を許可するscopeの集合である。
readとwriteは独立し、write scopeはreadを暗黙に許可しない。

base agent authはHubの論理ツリー全体にreadを付与する。Hub直下の通常ファイル・ディレクトリに加え、Hub直下で登録されたdirectory symlinkまたはmountを入口として、そのProject配下の通常ファイル・ディレクトリを読める。

- `ls`、`tree`、`stat`、`file`、`wc`、`cat`、`head`、`tail`、`grep`などのread操作は、この範囲でのみ行う。
- MVPではProject内部のnested symlinkを特別扱いしない。必要性が生じた時点で、追跡可否と境界を別途定義する。
- `..`、未登録の絶対path、または許可された入口以外からHub論理ツリーの外へ出るpathは拒否する。
- このread範囲はworkspace調査の境界であり、秘密情報の隔離境界ではない。許可されたProject内のファイルはAgentから読める。
- Agent adapterはこの契約を強制できるfilesystem境界へ変換しなければならない。

## Deferred

- networkの接続先表現
- `stdio`以外のtransport
- Agent adapter/harnessによるfilesystem・Task YAML操作の強制
