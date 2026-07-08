> この文書はwhubの用語・責務・CLI設計ポリシーの現時点の正とする。
> 他のドキュメントに異なる記述がある場合、この文書を優先する。
> ただし用語や設計は発展中であり、変更する場合はこの文書を先に更新する。
> 運用フローは`docs/workflow.md`、vaultの構造と配置判断は`vault/readme.md`を正とする。

# 用語定義
- `project`: 私が抱えているプロジェクトのこと
- `resource`: `project`が持つ任意の接続先データリソース
    - `remote`: `resource`が持つ属性で、リモートのコンピュータに格納されている`project`データを指す。sshfs mountでwhub以下に接続し（参照・編集）、実行はSSHで行う
    - `local`: `resource`が持つ属性で、このコンピュータにある`project`データを指す。シンボリックリンクでwhub以下に接続する
- `workspace-hub`: whub自体の`project`。ただしmount/link対象ではないため、現時点では`resource`ではない
- `vault`: 私の固有記述（知識・信念・whub運用データ）を集約するprivateな貯蔵庫repo。知識プレーン（inbox/literature/concepts/permanent/daily）と機械プレーン（manifest・todos・各種ログ）を持つ。whubの自己データは原則vaultに置き、workspace-hubの`.whub/config.toml`にdata_dirとして登録する（ADR-0008）
- `manifest`: `project`、`resource`、接続情報を定義する設定ファイル
- `target`: `resource`を操作するための実行対象。現時点では`local`/`remote`の呼び分け層を指す
- `roadmap`: `project`ごとの長期方針・思いつき・新機能案を置くドキュメント
- `todo`: 実行可能な単発アクション。project紐付けは任意。長期方針そのものは`roadmap`に置く

# コマンド
- `status`: whubでの接続状態、ヘルスチェックが目的
- `cd`: `project`または`resource`へ移動することが目的。`local`ならパス移動、`remote`ならSSH接続
- `link`: `symlink` resourceをworkspace-hub配下へ接続することが目的
- `todo`: `project`横断のToDoを管理することが目的
- `boot`: whubのAgent設定・`Skill`・CodeGraph初期化を各`resource`へ配布することが目的
- `roadmap`: `project`ごとの`roadmap`へ未整理メモを追記することが目的
- `mount`/`unmount`: `remote` resourceをsshfsでwhubツリーへ接続/解除することが目的
- `run`: `remote`でのワンショット実行が目的。対話セッションは`cd`が担う
- `fetch`: workspace-hub相対パスで指定した`remote`のファイルをwhub data_dirの`downloads/`へ取得することが目的

# リモート操作の用途分担
- 編集・コード確認・`project`横断のコンテキスト参照は`mount`で行う
- 走査系・長時間処理はリモート側で実行する（ワンショットは`run`、作業セッションは`cd`のtmux）
- 大容量ファイルの手元確認は`fetch`で逐次取得する
- この参照と実行の分離により、SSHFSのレイテンシ弱点と双方向同期のコンフリクトを回避する

# データモデル制約
- `project`は活動単位であり、必須フィールドは`name`のみ
- `project` 1 -- 0..1 `resource`
- `resource`は`project`直下に定義する
- `resource`のパス系フィールドは意味が曖昧な`path`へ寄せず、`workspace_path`や`source`など用途が分かる名前を使う
- 全`resource`はwhubツリー上の位置`workspace_path`を必須で持つ（`remote`も必ずツリーに配置し、横断参照を保証する）

# CLI設計ポリシー（コードをどう作るか）
- CLI側から、操作対象の`resource`が`remote`か`local`かを意識せず操作できる
- Clickの`command callback`では`resource`が`remote`か`local`かを秘匿して記述する。条件分岐はローカル関数に移譲する
- `target`は`resource`と処理データの列を受け取り、`local`/`remote`ごとの関数呼び分けを担う
- 各コマンドは`target`の入力インターフェースへ処理対象を整形する責務を持つ
- `target.py`は`resolve_project_resource`など、入力インターフェースへ整形するための汎用ヘルパーを提供する
- 現時点の`target`は`resource`と処理データの組み立て、`local`/`remote`関数の呼び分けを担う
- 将来的に`target`は存在確認、ファイル書き込みのような、`resource`属性ごとに処理が変わる一般操作も担う
- `roadmap`のテンプレート、`status`の表示、`boot`の配布手順などのドメイン処理は各コマンド側に置く
- `boot`はworkspace-hub配布と複雑な配布手順を持つため、現時点ではcallback内の`local`/`remote`分岐を許容する
- `remote.py`はSSH/rsync/sshfsのargvビルダー等の低レイヤーを担い、`project`や`roadmap`の意味は持たない
- `health.py`はsymlink/mountの健全性検査を集約する（remoteの健全性は`status`のホスト単位プローブが担う）
- `tmux.py`はセッション命名規約とリモートシェルスニペットの組み立てを担う
- `paths.py`はwhub rootとdata_dir、およびmanifest/todo/downloadsのパス解決を一元的に担う
- whub rootは`WHUB_ROOT`があれば優先し、通常はインストール済みパッケージ位置からworkspace-hub rootを導出する
- data_dirは`WHUB_DATA_DIR`があれば優先し、通常は`<workspace-hub>/.whub/config.toml`の`data_dir`をSSOTとする

# CLI振る舞いポリシー（どのような挙動を想定するか）
- とにかく`whub`を特別扱いしない。ただし`boot`は例外。
- `cd <project>`で紐づく`resource`がない場合は移動先なしを通知する（whubも）
- `status`は接続状態、ヘルスチェック、git差分確認に責務を絞る
- `status`は`resource`を持つ全`project`を対象にする
- `mount`は無引数で`mount: true`の`resource`のみを対象にし、名指し・`-a`はフラグを無視する
- `todo`は実行可能な単発アクションを管理する。project紐付けは任意
- `roadmap`は`<project>/docs/roadmap.md`へ未整理メモを追記する
- `fetch`はworkspace-hub相対パス（VS Codeの相対パスコピーを想定）から`resource`を解決し、data_dirの`downloads/`直下へフラットに保存する（同名は上書き）。単ファイル前提

---

(me)---(MacBook)---(Linux Desktop)
                 |
                  -(supercomputer)

MacBook、特にwhubを唯一のインターフェースとして、Macローカルも、自宅にホストしているLinuxのリソースにもシームレスに接続できるようにするのが目的

# スコープ境界: whubはMacローカル専用ツール
- whubはMacBook上でのみ動作するCLIであり、リモート先（Linux Desktop/supercomputer）へはインストール・配布しない
- そのため`cd`で`remote` resourceへSSH接続した先ではwhubコマンドは使えない。これは意図した割り切りである
    - 理由: 唯一のインターフェースはMacBookであり、リモートcd先でwhubを使いたい場面ではVS Codeで新しいターミナルタブを開き、Macローカルのwhubを叩けば足りる
    - リモート先でwhubを動かすためのグローバル化・配布は対応コストに見合わず、本質的に不要と判断する
- 一方、Mac内ではどのディレクトリからでもwhubを叩けるようにする（パッケージ位置からrootを導出し、`.whub/config.toml`のdata_dirを読む）。`whub cd`でMacローカルの`local` resourceへ移動した先でもwhubが動くことは、この範囲で保証する
