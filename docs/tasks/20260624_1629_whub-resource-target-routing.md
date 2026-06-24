# 目的・前提・方針案

## 目的
local/remoteで処理が分かれる一般的なresource操作を、薄いTarget/Router層へ寄せる。

## 前提
- Routerはresource名からlocal/remote targetを解決する
- Targetは`exists` / `read_text` / `write_text` / `append_text` / `run`程度の一般操作だけを担う
- local/remoteで処理手順が違う場合は、呼び分け補助関数に`local=` / `remote=`で関数を渡す
- 呼び分け補助関数の引数名は明示し、記述順は原則`local`→`remote`にする
- roadmap/status/fetch/editなどの業務ロジックは各コマンド側に残す
- bootのような複雑な処理は最初から全面共通化しない

## 方針案
- まず既存コマンドのlocal/remote分岐を棚卸しする
- 共通化対象は単純なファイル操作・コマンド実行に限定する
- `on_resource(resource, local=..., remote=...)`のような補助関数で、コマンド内の条件分岐を減らす
- `whub roadmap`を最初の利用例としてTarget/Routerの有効性を検証する

# 計画

## Phase 1: 既存分岐の棚卸し
- [ ] `cd` / `status` / `boot` / `todo`のlocal/remote分岐を確認する
- [ ] 共通化できる一般操作と残すべき業務ロジックを分ける

## Phase 2: Target/Router仕様
- [ ] `resolve_target(manifest, name)`の責務を定義する
- [ ] `LocalTarget` / `RemoteTarget`の最小APIを定義する
- [ ] `on_resource(resource, local=..., remote=...)`相当の呼び分け補助関数を定義する
- [ ] remote操作のエラー・timeout・shell quote方針を決める

## Phase 3: 導入範囲
- [ ] 初期導入対象を`whub roadmap`に絞る
- [ ] 既存コマンドへ横展開する順序を決める
- [ ] bootを全面共通化しない判断を記録する

## Phase 4: 検証
- [ ] local targetでファイル操作が動くことを確認する
- [ ] remote targetでSSH経由の基本操作が動くことを確認する
- [ ] 既存コマンドの挙動を壊していないことを確認する

# 実行ログ

# 結果
