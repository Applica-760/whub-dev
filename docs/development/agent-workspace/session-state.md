# Agent workspace session state

## Decision

sessionの状態は、実行状態、通知状態、詳細状態の三つで扱う。

```text
execution_state: standby | working
attention_state: attention | acknowledged
detail_state: not_started | running | input_requested | approval_requested | completed | failed | interrupted
```

## Meaning

- `execution_state` は人間に見せる大まかな状態である。`working` はAgentが実行中、`standby` は人間の次の判断または指示を待つ。
- `attention_state` は未確認の呼び出しを表す。`attention` は実行状態ではなく、利用者へ通知すべき状態変化が未確認であることだけを示す。
- `detail_state` はsessionの具体的な段階を表す。Agent adapterはAgent固有の出力をこの状態へ正規化する。

## Derived behavior

- `detail_state` が `running` のとき、`execution_state` は `working` とする。
- それ以外の `detail_state` では、`execution_state` は `standby` とする。
- `input_requested`、`approval_requested`、`completed`、`failed` への遷移時は、`attention_state` を `attention` とする。
- 利用者がsessionを開くと、`attention_state` を `acknowledged` へ更新する。`detail_state` は変えない。
- 完了または失敗を確認した後もsessionは `standby` とする。Taskを閉じるか、次の案を指示するかは利用者が決める。
