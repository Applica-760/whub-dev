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

## Deferred

- agent authの機械可読形式、配置、検証方法
- command、filesystem、network、外部ツールごとの具体的な許可項目
- Agent adapterへの変換方法
