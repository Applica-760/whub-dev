# 目的・前提・方針案

## 目的
local/remoteで処理が分かれる一般的なresource操作を、薄いTarget/Router層へ寄せる。

## 前提
- 正本は`docs/whub-concepts.md`
- manifestはversion 2で、`Manifest.projects[]`の`Project.resource`に`symlink`または`remote`を任意で持つ
- 現行APIとして`Manifest.resolve_project(project_name)`、`Manifest.resolve_path(relative)`、`remote.run_ssh_command`が使える
- Routerはproject名から`project.resource`をたどってlocal/remote targetを解決する
- `resource`を持たないprojectはTarget/Routerの対象外とする
- Targetは`exists` / `read_text` / `write_text` / `append_text` / `run`程度の一般操作だけを担う
- local/remoteで処理手順が違う場合は、呼び分け補助関数に`local=` / `remote=`で関数を渡す
- 呼び分け補助関数の引数名は明示し、記述順は原則`local`→`remote`にする
- roadmap/status/fetch/editなどの業務ロジックは各コマンド側に残す
- bootのような複雑な処理は最初から全面共通化しない。workspace-hubへのboot配布は例外として扱う

## 方針案
- まず既存コマンドのlocal/remote分岐を棚卸しする
- 共通化対象はresource typeによる呼び分けに限定する
- `on_targets(targets, local=..., remote=...)`で、callback側のresource type分岐とループ呼び出しを減らす
- `roadmap`は今回のスコープ外とする
- 将来候補として`exists` / `read_text` / `write_text` / `append_text` / `run`をTargetへ寄せる
- `Manifest.project_resources()`でresourceを持つproject一覧を提供する
- `status`は`boot`フラグで絞らず、全resourceを対象にする
- 暫定候補として`ProjectResource`と`on_targets(items, target=...)`方式を検討する
- `unhealthy`時の終了判定は現時点では`status`側に残す

## 確認済み事実
- `src/whub/commands/roadmap.py`はまだ存在しない
- `cd`はproject未定義を`unknown project: <name>`、resourceなしprojectを`project has no resource: <name>`で扱っている
- `boot`はworkspace-hub配布を例外として扱っている
- `ResourceInfo`はhealth/git差分を持つ実行結果でありmanifest modelでは代替しない
- `_StatusData`は暫定実装であり、`ProjectResource`導入時に廃止候補とする

# 計画

## Phase 1: 既存分岐の棚卸し
- [x] `cd` / `status` / `boot` / `todo`のlocal/remote分岐を確認する
- [x] 共通化対象をresource typeによる呼び分け、残す処理を各コマンド固有ロジックとして分ける

## Phase 2: Target/Router仕様
- [x] `src/whub/target.py`に既存`Resource`を使ったTarget解決層を追加する
- [x] `resolve_target(manifest, project_name)`でproject resourceからtargetを解決する
- [x] `Manifest.project_resources()`でresourceを持つproject一覧を取得できるようにする
- [x] `on_targets(targets, local=..., remote=...)`でlocal/remote関数を順次呼び分ける

## Phase 3: 既存コマンドへの適用
- [x] `cd` callbackを1要素リストの`on_targets`呼び出しへ置き換える
- [x] `status` callbackを`project_resources()`と`on_targets`へ置き換える
- [x] `status`の`boot`条件と`_format_git_column`を廃止する
- [x] `status`のresource type表示は`resource.type`を使う
- [ ] ⭐️`ProjectResource`と`on_targets(items, target=...)`方式の採否を決める
- [ ] `boot` callbackのresource type分岐を`on_targets`へ置き換える

## Phase 4: 検証
- [ ] target解決と`on_targets`の単体テストを追加する
- [ ] 既存コマンドのテストを更新し、挙動を壊していないことを確認する

# 実行ログ

### 試行 1: 単数`on_target`で呼び分ける
- 実施内容: `target.py`に`resolve_target`/`on_target`を追加し、`cd`へ適用した
- 結果: `cd`は薄くなったが、`status`/`boot`の複数resource処理ではcallback側にループが残る
- 判断: 方針変更

### 試行 2: `on_targets`へ`(resource, data)`列を渡す
- 実施内容: `Manifest.project_resources()`と`on_targets()`を追加し、`cd`/`status`へ適用した
- 結果: `status`に`_StatusData`詰め替えが残り、`project_resources()`との接続がやや冗長になった
- 判断: 暫定継続

### 試行 3: `ProjectResource`とtarget getter方式
- 実施内容: 未実施、`on_targets(items, target=...)`でitemからresourceを取得する案を検討した
- 結果: `_StatusData`を廃止でき、manifestはresource付きproject要素の提供に集中できる見込み
- 判断: 保留

# 結果
