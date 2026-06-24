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
- `on_target(target, data=..., local=..., remote=...)`で、callback側のresource type分岐を減らす
- `roadmap`は今回のスコープ外とする
- 将来候補として`exists` / `read_text` / `write_text` / `append_text` / `run`をTargetへ寄せる

## 確認済み事実
- `src/whub/commands/roadmap.py`はまだ存在しない
- `cd`はproject未定義を`unknown project: <name>`、resourceなしprojectを`project has no resource: <name>`で扱っている
- `boot`はworkspace-hub配布を例外として扱っている

# 計画

## Phase 1: 既存分岐の棚卸し
- [x] `cd` / `status` / `boot` / `todo`のlocal/remote分岐を確認する
- [x] 共通化対象をresource typeによる呼び分け、残す処理を各コマンド固有ロジックとして分ける

## Phase 2: Target/Router仕様
- [x] `src/whub/target.py`に既存`Resource`を使ったTarget解決層を追加する
- [x] `resolve_target(manifest, project_name)`でproject resourceからtargetを解決する
- [x] `on_target(target, data=..., local=..., remote=...)`でlocal/remote関数を呼び分ける

## Phase 3: 既存コマンドへの適用
- [x] `cd` callbackのresource type分岐を`on_target`へ置き換える
- [ ] `status` callbackのresource type分岐を`on_target`へ置き換える
- [ ] `boot` callbackのresource type分岐を`on_target`へ置き換える
resolve_project とかが不要になってないか確かめる

## Phase 4: 検証
- [ ] target解決と`on_target`の単体テストを追加する
- [ ] 既存コマンドのテストを更新し、挙動を壊していないことを確認する

# 実行ログ

# 結果
