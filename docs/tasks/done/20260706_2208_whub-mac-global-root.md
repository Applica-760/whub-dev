# 目的・前提・方針案

- 目的: Mac内でどのディレクトリからでもwhubが動くようにする（CWD依存の解消）
- 決定: リモートcd先でのwhub利用は非対応。本タスクはMacローカル限定（`docs/whub-concepts.md`「スコープ境界」）
- 課題: 現状`MANIFEST_PATH`/`TODO_PATH`/`DOWNLOADS_DIR`と`Path.cwd()`がすべてCWD前提で、`whub cd`した先でwhubが使えない
- 方針（確定）: `paths.py`にroot/data_dir解決を集約し、symlinkではなく`<root>/.whub/config.toml`にdata_dirを登録する
    - `whub_root()`解決順: **`WHUB_ROOT` env → パッケージ位置からworkspace-hub root導出**
    - `whub_data_dir()`解決順: **`WHUB_DATA_DIR` env → `<root>/.whub/config.toml`の`data_dir` → 未初期化でClickException**
    - `init`は`whub init <data_dir>`で`config.toml`へ絶対パスを登録する
- symlinkは不要。`<root>/.whub`はgitignore対象の設定ディレクトリとする

# 計画

## Phase 1: 旧案 whub_root() 導入とCWD依存の置換（Phase 4で置換済み）
- [x] `init.py`に`whub_root()`（env → `~/.whub` → ClickException）と`_ensure_symlink`を実装、`init`を2symlink作成へ拡張
- [x] `manifest.py`: `MANIFEST_PATH`廃止、`load_manifest`/`workspace_hub_resource`/`_validate_projects`を`whub_root()`由来に
- [x] `todo.py`: `TODO_PATH`廃止、`_todo_path()`ヘルパ経由に
- [x] `fetch.py`: `DOWNLOADS_DIR`廃止、`whub_root()`由来に
- [x] 循環import対処: models(`manifest.py`/`todo.py`)は関数内import、`fetch.py`はトップレベルimport

## Phase 2: テスト（Phase 4で追加更新）
- [x] `tests/__init__.py`で`WHUB_ROOT`をtmpへ設定しスイート自己完結化
- [x] `test_manifest.py`/`test_fetch.py`のCWD相対アサーションを`whub_root()`基準へ更新、未使用`Path`除去
- [x] 全54テストがグリーン
- [x] `paths.py`単体テスト（env優先 / config読み込み / 未初期化ClickException）を追加

## Phase 3: ドキュメント・検証
- [x] `whub-concepts.md`に`paths.py`/`config.toml`/data_dir運用を追記
- [x] roadmap該当項目（CWD依存解消/Mac内グローバル化）を消化済みに
- [x] ADR-0003「CWD相対で読む」とADR-0008「symlinkブリッジ」を新方針へ更新
- [x] ツリー外`/tmp`から`whub todo`動作・未初期化エラーを手動確認（`whub cd`先の実地確認は残）

## Phase 4: 改善案（paths.py集約・symlink依存削減）
- [x] `src/whub/paths.py`を追加し、`whub_root`/`data_dir`/`manifest_path`/`todo_path`/`downloads_dir`を集約する
- [x] `whub_root`は`WHUB_ROOT`優先、通常はパッケージ位置からworkspace-hub rootを導出する
- [x] `whub init <data_dir>`はsymlink作成ではなく`<root>/.whub/config.toml`へ絶対パスを登録する
- [x] `WHUB_DATA_DIR`を一時overrideとして用意し、通常は`config.toml`の`data_dir`をSSOTにする
- [x] `manifest.py`/`todo.py`/`fetch.py`を`paths.py`経由へ変更し、modelsからcommandsへの関数内importを除去する
- [x] 既存の`~/.whub`登録案と`<root>/.whub` symlink案を撤回し、ADR/概念/roadmapを新方針へ更新する

# 実行ログ

### 試行 1: root永続化の設計確定
- 実施内容: 当初「`.whub/`上方探索＋`WHUB_ROOT`」案。だが`whub cd <local>`は`os.getcwd()`がsymlink解決後の実パス（ツリー外）を返し上方探索が届かないと判明
- 結果: 上方探索を廃し「rootを`~/.whub` symlinkで永続化して読む」へ転換。`init`が登録、`whub_root()`が読む1機構に
- 判断: 方針変更（(a)`~/.whub` symlink採用、`~/.config`案・上方探索は不採用）

### 試行 2: whub_root()の配置と循環import
- 実施内容: `whub_root()`を`init.py`に置き、`manifest.py`からトップレベルimportを試行
- 結果: `manifest.py(models) → whub.commands.init → commands/__init__(get_manifest) → whub.models` の循環でImportError。相対import・再export・`__init__.py`/`cli.py`配置いずれも「command層がmodelsをimportし返す」構造ゆえ解決不可
- 判断: models層の2ファイルのみ**関数内import**で循環を断つ（新規ファイル追加・get_manifest移設・大規模改修を回避）。`fetch.py`は同層なのでトップレベルimントで可

### 試行 3: テストのroot解決
- 実施内容: pytest未導入・unittest形式のため、`whub_root()`がenv/`~/.whub`未設定だと全manifest構築テストが落ちる
- 結果: 既存の空`tests/__init__.py`で`WHUB_ROOT`をtmpへ`setdefault`し、パッケージimport時に一度だけ解決。新規ファイルなしで自己完結
- 判断: 続行。CWD相対前提だった`test_manifest`/`test_fetch`の2アサーションを`whub_root()`基準へ更新

### 試行 4: symlink登録案の見直し
- 実施内容: `~/.whub`登録・`<root>/.whub` symlink・models内関数importの違和感を再評価
- 結果: root解決はパッケージ位置、data_dir解決は`<root>/.whub/config.toml`のパス登録へ分離する改善案を採用
- 判断: 方針変更（Phase 4で現実装を置き換える）

### 試行 5: config.toml方式への移行
- 実施内容: `./.whub` symlinkを削除し、`whub init <data_dir>`で`./.whub/config.toml`を作成
- 結果: `data_dir = ""`として登録済み
- 判断: 続行

# 結果

- CWD依存を解消。root/data_dir解決は`paths.py`に集約（root=env or package位置、data_dir=env or `.whub/config.toml`）
- 変更ファイル:
    - `src/whub/paths.py`: root/data_dir/manifest/todo/downloadsパス解決を追加
    - `src/whub/commands/init.py`: symlink作成を廃止し、`config.toml`へのdata_dir登録へ変更
    - `src/whub/models/manifest.py` / `todo.py` / `commands/fetch.py`: `paths.py`経由へ変更
    - `src/whub/tests/test_paths.py` / `test_init.py`: 新パス解決とinit登録のテスト追加
    - `docs/whub-concepts.md` / `docs/ADR/0003-manifest-placement-root.md` / `docs/ADR/0008-tool-data-plane-separation.md` / `docs/roadmap.md`: 新方針へ更新
- 検証: ✅ `./.whub`がディレクトリ化され`config.toml`にdata_dir登録済み ✅ 全59テストpass
- 残: `whub cd`先の実地検証
