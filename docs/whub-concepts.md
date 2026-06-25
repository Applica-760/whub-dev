> この文書はwhubの用語・責務・CLI設計ポリシーの現時点の正とする。
> 他のドキュメントに異なる記述がある場合、この文書を優先する。
> ただし用語や設計は発展中であり、変更する場合はこの文書を先に更新する。

# 用語定義
- `project`: 私が抱えているプロジェクトのこと
- `resource`: `project`が持つ任意の接続先データリソース
    - `remote`: `resource`が持つ属性で、リモートのコンピュータに格納されている`project`データを指す
    - `local`: `resource`が持つ属性で、このコンピュータにある`project`データを指す。シンボリックリンクでwhub以下に接続する
- `workspace-hub`: whub自体の`project`。ただしmount/link対象ではないため、現時点では`resource`ではない
- `manifest`: `project`、`resource`、接続情報を定義する設定ファイル
- `target`: `resource`を操作するための実行対象。`local`/`remote`の差を一般操作として吸収する
- `roadmap`: `project`ごとの長期方針・思いつき・新機能案を置くドキュメント
- `todo`: 実行可能な単発アクション。長期方針そのものは`roadmap`に置く
- `task-planning`: 個別作業の実行計画と作業ログ（skills）
- `specs`: 実装前に固めた仕様（skills）
- `ADR`: 重要な設計判断の記録
- `Skill`: AI/Agentに特定の作業手順を担わせるための指示セット

# コマンド
- `status`: whubでの接続状態、ヘルスチェックが目的
- `cd`: `project`または`resource`へ移動することが目的。`local`ならパス移動、`remote`ならSSH接続
- `todo`: `project`横断のToDoを管理することが目的。これを見て、自分が次に何をすべきかを決定できるのが理想
- `roadmap`: `project`ごとの`roadmap`へ未整理メモを追記することが目的
- `boot`: whubのAgent設定・`Skill`・CodeGraph初期化を各`resource`へ配布することが目的

# データモデル制約
- `project`は活動単位であり、必須フィールドは`name`のみ
- `project` 1 -- 0..1 `resource`
- `resource`は`project`直下に定義する
- `resource`のパス系フィールドは意味が曖昧な`path`へ寄せず、`workspace_path`や`source`など用途が分かる名前を使う

# CLI設計ポリシー（コードをどう作るか）
- CLI側から、操作対象の`resource`が`remote`か`local`かを意識せず操作できる
- Clickの`command callback`では`resource`が`remote`か`local`かを秘匿して記述する。条件分岐はローカル関数に移譲する
- `target`は`resource`と処理データの列を受け取り、`local`/`remote`ごとの関数呼び分けを担う
- 各コマンドは`target`の入力インターフェースへ処理対象を整形する責務を持つ
- `target.py`は`resolve_target`など、入力インターフェースへ整形するための汎用ヘルパーを提供する
- `target`は存在確認、ファイル書き込みのような、`resource`属性ごとに処理が変わるもののうち、一般操作だけを担う
- `roadmap`のテンプレート、`status`の表示、`boot`の配布手順などのドメイン処理は各コマンド側に置く
- `remote.py`はSSH/rsyncの低レイヤーを担い、`project`や`roadmap`の意味は持たない
- `Skill`は壁打ち、整理、昇格、仕様化など、CLIに持たせない判断処理を担う

# CLI振る舞いポリシー（どのような挙動を想定するか）
- とにかく`whub`を特別扱いしない。ただし`boot`は例外。
- `cd <project>`で紐づく`resource`がない場合は移動先なしを通知する（whubも）
- `status`は接続状態、ヘルスチェック、git差分確認に責務を絞る
- `status`は`resource`を持つ全`project`を対象にする
- `todo`は`project`に紐づく単発アクションを管理する。`project`に`resource`がなくても`todo`は持てる
- `roadmap`は`<project>/docs/roadmap.md`へ未整理メモを追記する
- `roadmap`の整理済み領域への昇格、`todo`や`specs`や`ADR`への分解は`Skill`/Agent側で行う
