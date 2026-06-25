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
- [ ] `boot` callbackのresource type分岐を`on_targets`へ置き換える → Phase 3-2完了後に実施

## Phase 3-1: モデル層の整理（manifest依存の除去）
Phase 3の適用中に判明した負債。resourceデータクラスを自己完結させ、Manifestへの不要な依存を断つ。

### Step 1: RemoteResourceにHost注入
- [ ] `RemoteResource._host_config: Host | None = PrivateAttr(default=None)` を追加
- [ ] `Manifest._validate_projects`内で`resource._host_config = self.hosts[resource.host]`を注入

### Step 2: resolve_path / workspace_root の全箇所置換
すべての呼び出し元を`Path.cwd()`に置換してから、Manifestの定義を削除する。
- [ ] `health.py`: `inspect_symlink` / `inspect_remote` / `inspect_resource`からmanifest引数を除去
- [ ] `cd.py`: `_cd_local` / `_cd_remote`からmanifest引数を除去
- [ ] `link.py`: `m.workspace_root` / `m.resolve_path()`を`Path.cwd()`に置換
- [ ] `boot.py`: `manifest.workspace_root` / `manifest.resolve_path()`を`Path.cwd()`に置換

### Step 3: Manifest._root系の廃止（Step 2完了後）
- [ ] `Manifest._root` / `resolve_path()` / `workspace_root`プロパティを削除
- [ ] `load_manifest()`の`m._root = Path.cwd()`を削除
- [ ] テスト(`test_manifest.py`, `test_boot.py`)を更新

## Phase 3-2: ⭐️案の実装（callbackの中間データクラス廃止）
Phase 3の適用中に`_StatusData`等の詰め替えが冗長と判明。Phase 3-1でmanifest依存を除去済みのため、シグネチャ変更は1回で済む。

- [ ] target.pyに新関数（仮: `collect_targets`）を追加: manifestを受け取り`list[TargetItem[Project]]`を返す
- [ ] `status`: `_StatusData`廃止、callbackが`(Resource, Project)`を受ける形に修正
- [ ] `cd`: callbackが`(Resource, Project)`を受ける形に修正
- [ ] `Manifest.project_resources()`を廃止（呼び出し元が`collect_targets`に切り替わった後）

## Phase 4: 検証
- [ ] target解決と`on_targets`の単体テストを追加する
- [ ] 既存コマンドのテストを更新し、挙動を壊していないことを確認する

## 決定事項

### workspace_rootの渡し方 → `Path.cwd()`を直接使用し、Manifest._root / resolve_path()を廃止
- whubはuv仮想環境の制約でworkspace-hubディレクトリからしか起動しない
- 現状すでに`MANIFEST_PATH = Path(".whub/manifest.yaml")`と`m._root = Path.cwd()`でcwd前提
- `Path.cwd()`で全箇所代替可能。`Manifest._root` / `resolve_path()` / `workspace_root`を廃止する
- 対象箇所: health.py, cd.py, link.py, boot.py, テスト

### hosts解決 → RemoteResourceにPrivateAttrで注入
- `RemoteResource._host_config: Host | None = PrivateAttr(default=None)` を追加
- `Manifest._validate_projects`のmodel_validator内で、host検証と同時に`resource._host_config = self.hosts[resource.host]`を注入
- `host: str`（YAMLキー名）はそのまま残す
- SSOTはYAMLの`hosts:`セクション。各RemoteResourceがHostインスタンスを持つだけで定義の重複なし

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

⭐️案
・_StatusDataデータクラスを廃止、project_resources関数の廃止
・（いい感じの名前を後で定めた上で）targetに関数を新設する。
　それは、`get_manifest(ctx)`で取得したマニフェストを受け取り、リソースが存在するプロジェクトをフィルターして、
　TargetItemのリスト（[TargetItem(project1.resource, project1), ...]）を返す。（concept記載の通り、on_targetが求める形式のモデルを返す）
（↓処理の一部の例。project_resourcesの代替となるイメージ）
```
return [
          TargetItem(project.resource, project)
          for project in manifest.projects
          if project.resource is not None
      ]
```

_fetch_*_info()関数は、現時点ではリソースのデータクラス、name, manifestを引数に取っているが、manifestに全て入っている。そのため、
_fetch_*_info()は、あるプロジェクトの`Project`データクラスさえ受け取れば、nameを取得できるし、投入されるデータクラスも、on_targets()関数がソートするので、
symlink, remoteいずれか、関数が要求するデータクラスが勝手に投入される

target新設関数が、on_targetに投げるTargetItemのリストを作る。同時に投げるlocal, remote関数も修正する
on_target内のループで、projectデータモデルが、そのリソースのデータクラスに応じた関数に渡される

## ⭐️案の評価

### 方向性: 妥当
1. `_StatusData`廃止 → Projectをそのまま渡せば中間詰め替え不要、自然
2. `project_resources()`のtarget.py移設 → manifestは「データの器」、フィルタリングはtarget層の責務として整理が正しい
3. callbackからmanifest依存を外す改修が前提条件 → これをやらないとProject渡しにしてもmanifestを別ルートで引く必要が出て効果が半減する

### 前提として必要な負債解消
health.py / cd.pyのcallbackがmanifestを丸ごと受け取っているが、実際に使うのは以下の2つだけ:
- `workspace_root: Path` — symlink系が`resolve_path`経由で使用
- `hosts[key] -> Host` — remote系がホスト情報取得に使用

これらはresourceデータクラスのフィールドでカバーできる情報であり、Manifestへの依存は不要。
Phase 4でこの負債を先に解消した上で、Phase 5で⭐️案を実装する。

### manifest依存の実態（確認済み）
| 箇所 | manifest経由で取得 | 本質的に必要なもの |
|------|------|------|
| `inspect_symlink` | `manifest.resolve_path(workspace_path)` | `workspace_root` |
| `inspect_remote` | `manifest.hosts[r.host]` | `Host`データクラス |
| `_fetch_symlink_info` | `inspect_symlink(r, m)` | 上記の間接依存 |
| `_fetch_remote_info` | `m.hosts[r.host]` | 同上 |
| `cd._cd_local` | `manifest.resolve_path(workspace_path)` | `workspace_root` |
| `cd._cd_remote` | `manifest.hosts[r.host]` | `Host` |

# 結果
