# 目的・前提・方針案

**状態：方向性の案（未確定）。実行前にユーザ承認が必要。**

- 目的: inbox消化に先立ち、自分のマインド系ノートの置き場を再設計する
- 前提: `vault/readme.md` が構造のSSOT。「主軸＝成熟度、複数軸をディレクトリに詰め込まない、フラット＋リンク」の原則は維持する
- 前提: `vault/docs/backlog.md` に既存Question「permanentの粒度を整理したい」があり、本タスクはその決着にあたる
- 方針案1: `permanent/` → `mind/` に改名。mind（起源＝自分）/ literature（起源＝外部）でトップレベルが起源軸で対称になる
- 方針案2: `mind/問い/` を新設。持続する悩み・未決の問い（fleetingでも確立でもない）の置き場。確立したら親へ昇格
- 方針案3: それ以上の細分（価値観/認知/技術観 等）はディレクトリ化せず、リンクと `_map.md`（frontmatter `summary:` 集約）で表現する
- 見送った案: 洗練度によるサブディレクトリ階層化（成熟度軸がライフサイクルと二重になり readme 原則に反するため）
- 改名コスト: `permanent` 参照は readme.md / whub-concepts.md / refile Skill×2 / vault backlog / sourcesノート1件 / done tasks 等 約9箇所

# 計画

（方向性確定後に記載）

## Phase 1: 構造変更（案）
- [ ] `git mv vault/permanent vault/mind`・`vault/mind/問い/` 作成
- [ ] 参照9箇所の更新（readme.md, whub-concepts.md, refile Skill, backlog 等）
- [ ] `vault/readme.md`（SSOT）に mind/問い の定義・昇格ルールを反映

## Phase 2: 決着の記録（案）
- [ ] `vault/docs/backlog.md` の既存Question「permanentの粒度整理」を決着として更新

## Phase 3: inbox消化（案・別タスク化も可）
- [ ] refile Skillで inbox 14件を新構造へ振り分け（優先順: 統合明確4件 → 自分史 → ノート管理Question）
- [ ] `mind/_map.md` 生成・`core.md` 見直し

# 実行ログ

# 結果
