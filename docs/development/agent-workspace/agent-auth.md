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

## Filesystem authorization

base agent authはHubの論理ツリー全体にreadを付与する。Hub直下の通常ファイル・ディレクトリに加え、Hub直下で登録されたdirectory symlinkまたはmountを入口として、そのProject配下の通常ファイル・ディレクトリを読める。

- `ls`、`tree`、`stat`、`file`、`wc`、`cat`、`head`、`tail`、`grep`などのread操作は、この範囲でのみ行う。
- MVPではProject内部のnested symlinkを特別扱いしない。必要性が生じた時点で、追跡可否と境界を別途定義する。
- `..`、未登録の絶対path、または許可された入口以外からHub論理ツリーの外へ出るpathは拒否する。
- このread範囲はworkspace調査の境界であり、秘密情報の隔離境界ではない。許可されたProject内のファイルはAgentから読める。
- Agent adapterはこの契約を強制できるfilesystem境界へ変換しなければならない。

## Deferred

- agent authの機械可読形式、配置、検証方法
- command、network、外部ツールごとの具体的な許可項目
- Agent adapterへの変換方法
