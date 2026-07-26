# ADR-0010: Knowledgeエントリの分類

- **Status:** Superseded by ADR-0013
- **Date:** 2026-07-13

## Context

- Knowledge YAMLの`policies`に、人間・Agentの運用判断と、データ・実装・CLIが満たすべき性質が混在している
- 両者では適用主体と例外の意味が異なるため、同じ分類では記述と参照時の判断が不安定になる
- IDプレフィックスの意味はKnowledgeの実データではなく、Knowledge YAMLを解釈するための形式定義である

## Decision

Knowledgeエントリを次の5種類に分類する。

- `DEF-*`: 用語が何であるか
- `REL-*`: 用語同士の関係
- `POL-*`: 人間・Agentがどう運用するか
- `CON-*`: データ・実装・CLIが必ず満たす性質
- `EXC-*`: PolicyまたはConstraintの例外

各エントリは、見出しや周辺の記述がなくても単独で意味が通る内容にする。

現在有効な分類・フィールド・参照規則は`src/whub/models/knowledge.py`のPydanticモデルを正とする。各モデルのdocstringで分類の意味を示し、バリデーションでIDプレフィックスと参照規則を強制する。Knowledge YAMLには形式定義を自己記述せず、その形式に従った実データだけを置く。

## Rationale

- Policyを運用判断に限定すると、人間・Agentが判断時に参照する規則を抽出しやすい
- Constraintを分離すると、実装やデータの検証対象を明確にできる
- IDプレフィックスの意味をKnowledge YAML自身へ置くと、形式をその形式自身で説明する自己参照になる
- 独立したschema文書を正とするとPydanticモデルとの重複が生じるため、実行可能な形式定義であるモデルへ集約する
- 種別フィールドを追加すると、YAMLのセクションとIDプレフィックスに対して情報が重複する

## Consequences

- 既存のPolicyを運用判断とConstraintへ再分類する必要がある
- Pydanticモデル、Service、CLI、Knowledge YAMLを`CON-*`に対応させる必要がある
- Exceptionの参照先はPolicyだけでなくConstraintも許可する必要がある
- 将来whub appで形式を説明する場合は、PydanticモデルのJSON Schemaを利用できる
