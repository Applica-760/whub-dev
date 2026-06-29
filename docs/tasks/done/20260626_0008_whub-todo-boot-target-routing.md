# 目的・前提・方針案

## 目的
`20260624_1629_whub-resource-target-routing.md`から残作業を分離し、`todo` / `boot`の改修を小さく完了させる。

## 前提
- 正本は`docs/whub-concepts.md`
- `cd` / `status`のTarget/Router適用は完了済み
- `todo`はresource操作ではなく、projectに紐づくタスク管理コマンド
- `boot`はworkspace-hub配布を例外として残す
- `target`は現時点では`TargetItem`整形と`local` / `remote`呼び分けを担う
- `boot`の配布処理、CodeGraph初期化、失敗時の継続判断は`boot.py`側に残す
- 配布資産は`src/whub/boot/`を維持し、実装内の変数名は`source`ではなく`boot_assets`へ統一する

## 確認済み事実
- concept明文化済み: workspace-hub配布は例外、bootの複雑なcallback分岐は現時点で許容
- concept明文化済み: targetはresourceと処理データの列を受け取りlocal/remote呼び分けを担う
- concept未明文化: `boot: true` resourceのみ配布対象にする実装仕様
- concept未明文化: local missingはskip、deploy/CodeGraph失敗はWARNで後続targetへ継続
- concept未明文化: local CodeGraph未検出は1回だけWARNし、remote CodeGraph失敗もdeploy成功後の非致命扱い
- 設計決定: `files("whub").joinpath("boot")`参照はboot.py内に閉じ、必要なら`_boot_assets()` helper経由にする

## 方針案
- `todo`はTarget適用せず、manifest取得とproject存在確認の責務を整理する
- `todo`一覧は期限順を最優先し、同じ期限ならpriority順で表示する
- `todo -a`の完了済み一覧は完了日順で表示する
- `boot`はworkspace-hub例外を維持しつつ、resource type分岐を`on_targets`へ寄せられる範囲だけ寄せる
- `boot`は先にManifest v2モデルから配布データを準備し、その後で`on_targets`を導入する
- `on_targets`導入後に`todo`同様、全体構成と責務境界を見直す
- 複雑な配布処理そのものは`boot.py`側に残す
- 既存挙動を変えず、単体テストで回帰を確認する

# 計画

## Phase 1: `todo`改修
- [x] `todo add`を`load_manifest()`直呼びから`get_manifest(ctx)`利用へ変更する
- [x] `todo`にはTargetを導入しない方針を維持する
- [x] 未完了todoを期限順、同一期限内priority順で表示する
- [x] `todo -a`の完了済みtodoを完了日順で表示する


## Phase 3: `boot`へのTarget導入
- [x] `_collect_boot_targets()`を`boot: true` / resourceありの`TargetItem[Project]`だけ返す前処理へ変更する
- [x] `_apply_local_path_boot`は追加せず、`_apply_local_boot(resource, project)`へ単一target処理を集約する
- [x] `_apply_local_boot(resource, project)`を`on_targets()` callback形式に合わせた単一target処理へ変更する
- [x] `_apply_workspace_boot()`を追加し、仮`SymlinkResource`経由で`_apply_local_boot()`を呼ぶ
- [x] `_apply_remote_boot(resource, project)`を`on_targets()` callback形式に合わせた単一target処理へ変更する
- [x] `source`変数を`boot_assets`へ改名し、`src/whub/boot/`参照をboot.py内のhelperへ閉じる
- [x] `boot()` callbackを`manifest取得`、`targets準備`、`workspace-hub適用`、`on_targets()`呼び出しだけに薄くする
- [x] 既存bootテストを単一target applyとworkspace-hub例外の構成に合わせて更新する

## Phase 4: 構成見直し
- [x] `boot()` callbackをworkspace-hub適用と`on_targets()`呼び出し中心に薄くする
- [x] helper名・型・責務境界を見直し、CodeGraph初期化を`_init_*_codegraph()`へ抽出する
- [x] concept未明文化の挙動は矛盾なしと判断し、docs追記は後続判断に回す

## Phase 5: 検証
- [ ] `todo`のprojectなし/未知project/既知project/resourceなしproject/ソートのテストを追加する
- [x] bootでworkspace-hub配布が維持されることを確認する
- [ ] bootで`boot: false` resourceが配布対象外になることを確認する
- [x] bootのlocal/remote失敗継続テストが壊れていないことを確認する
- [x] `uv run python -m unittest discover -s src/whub/tests`を実行する
- [x] `docs/whub-concepts.md`との乖離が残っていないか確認する

# 実行ログ

# 結果
- Phase 4まで完了し、Phase 5の残検証は後続のtest系再構築でまとめて対応するため本タスクはここで閉じる
- conceptとの矛盾はなし、`boot: true`対象化やWARN継続などの未明文化仕様は後続で必要に応じてdocs化する

# 📝構成案

_collect_boot_targets(manifest)
    boot:True、project.resource is not None、の判定
    isinstance(resource, SymlinkResource) または　isinstance(resource, RemoteResource)　の判定
    local_path = resource._resolved_workspace_path　が存在するかの判定
    まで全て済ませたうえで、TargetItemのリストを返す。
    可能なら、`local_targets = [("workspace-hub", Path.cwd())]`のように、力技でTargetItemとしてworkspace-hubを組み立てられない？

_apply_local_boot()
    shutil.which("codegraph")  が常に必要かつリソース固有の情報を含まないのであれば、関数内部に組み込んでしまえばいいのでは？
    もしかして、これを廃止すると、codegraph以外のツールを組み込みにしようとしたらリストの編集が必要になる？
    その場合manifestのトップレベルにboot_items: ["codegraph"] みたいなフィールドを追加するのはだめか？
    既存のlist受け取りをやめ、TargetItem単体を処理する形へ寄せる。
    localのCodeGraph初期化は毎回実行し、未検出時だけ対象ごとにWARNしてskipする。

_apply_workspace_boot()
    workspace-hubはresourceではないため、TargetItem化せず専用関数で単体適用する。

boot()
    manifest = get_manifest(ctx)
    targets = _collect_boot_targets(manifest)
    with as_file(files("whub").joinpath("boot")) as source:
        """workspace-hubだけ実行する処理の挿入（collect bootで解決できるなら不要？）"""
        on_targets(...)
    と、超短縮できないか？
