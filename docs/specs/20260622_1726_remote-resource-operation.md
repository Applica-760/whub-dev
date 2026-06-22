# 実行仕様書: リモートリソース操作方式の変更

## 目的
- リモートリソースをマウントせず、SSH経由で操作する。
- ローカルファイル走査がリモートリソースへ到達しない構成にする。

## 背景・前提
- SSHFS越しの走査がCodeGraph等を遅延させ、Apple Bundleの重複を発生させている。
- リモートリソースをworkspace-hubのファイルツリーへ含める要求はない。
- manifestの後方互換性は維持しない。

## 対象範囲
- manifest、`cd`、`status`、`boot`、SSH実行基盤。
- `mount`、`unmount`、SSHFS依存処理の廃止。
- 関連文書およびテスト。

## 非対象範囲
- ローカルsymlinkリソースの操作方式。
- CodeGraph MCPのリモート中継。
- 旧マウントポイントの削除。
- 旧manifestの互換処理および自動移行。

## 変更要件

- manifest
  - 理想の状態
    - symlinkとremoteが独立したスキーマを持つ。
  - 乖離内容
    - 全リソースが`path`を共有し、remote相当が`mount`とSSHFS専用設定を持つ。
  - 変更方針
    - `MountResource`を`RemoteResource`へ変更し、`resources.symlinks`と`resources.remotes`へ分類する。
    - symlinkは相対`workspace_path`と絶対`source`、remoteは`host`と絶対`path`を持つ。
    - remoteの`path`では相対パスと`~`を許可しない。
    - `auto_mount`を廃止し、remoteのhost参照を検証する。

- `whub cd`
  - 理想の状態
    - symlinkではローカルへ移動し、remoteでは対象パスで対話シェルを開始できる。
  - 乖離内容
    - リモート分岐が`MountResource`へ依存している。
  - 変更方針
    - `RemoteResource`をSSH接続対象とし、失敗時は非ゼロで終了する。

- `whub status`
  - 理想の状態
    - symlinkのローカル状態とremoteの接続・パス状態を一覧できる。
  - 乖離内容
    - remote相当の判定がローカルマウントと`--check`に依存している。
  - 変更方針
    - remoteは常にSSH確認し、接続不能とパス不在を区別する。
    - `--check`を廃止し、失敗後も後続を確認して最終的に非ゼロで終了する。

- `whub boot`
  - 理想の状態
    - localとremoteへ配布し、remote上でCodeGraphを初期化できる。
  - 乖離内容
    - remote処理がmount型と個別のSSH実装に依存し、一部の失敗を検出できない。
  - 変更方針
    - localとremoteの対象解決を分離し、全処理結果を検査する。
    - CodeGraph初期化は共通SSH実行基盤を内部利用する。
    - 失敗を対象別に表示し、後続を処理する。

- `whub mount` / `whub unmount`
  - 理想の状態
    - CLIと実装がSSHFSに依存しない。
  - 乖離内容
    - mount操作とSSHFSコマンド生成処理が存在する。
  - 変更方針
    - コマンド、実装、設定およびマウント状態判定を削除する。

- SSH実行基盤
  - 理想の状態
    - `cd`、`status`、`boot`が共通の接続設定と実行基盤を利用する。
  - 乖離内容
    - SSH実行とエラー処理がコマンドごとに分散している。
  - 変更方針
    - ホスト解決、TTY、タイムアウト、入出力、終了コードを共通化する。
    - 任意コマンド実行用の公開CLIは設けず、remote操作は内部APIとして提供する。

- 関連文書
  - 理想の状態
    - manifest、CLIおよび文書が実装と一致している。
  - 乖離内容
    - ADR、README、要求定義およびCLI仕様がSSHFSを前提としている。
  - 変更方針
    - ADR-0004、0005と利用者向け文書を更新し、ADR-0007をSupersededとする。

## 実装方針
- manifestは`resources.symlinks`と`resources.remotes`に独立モデルを持つ。
- remote操作はローカルパスを経由せず、共通SSH実行基盤へ集約する。
- SSHFS固有コードと旧スキーマの互換層を残さない。
- 対象単位の失敗を収集し、独立した後続処理を継続する。

## 受け入れ基準
- [ ] symlinkとremoteが独立したスキーマとして検証される。
- [ ] remoteの`path`が絶対パス以外を拒否する。
- [ ] `mount`、`auto_mount`および旧スキーマが受理されない。
- [ ] remoteがローカルファイルツリーに存在しない。
- [ ] remoteに対する`cd`、`status`、`boot`がSSH経由で動作する。
- [ ] `status`と`boot`が共通SSH実行基盤を利用する。
- [ ] `status`が失敗後も後続を処理し、最終的に非ゼロで終了する。
- [ ] `boot`が失敗を対象別に表示し、後続を処理する。
- [ ] `boot`がremote上でCodeGraphを初期化する。
- [ ] mount、unmountおよびSSHFS依存コードが存在しない。
- [ ] CodeGraphの索引とローカル走査がremoteへ到達しない。
- [ ] symlinkリソースの既存動作が維持される。

## 検証条件
- manifestの正常系、旧形式、host不在および不正なremote pathを検証する。
- SSH処理をテストダブルへ置換し、各コマンドの構築、失敗継続および終了コードを検証する。
- 実環境でremoteがローカルツリーとCodeGraph索引に存在しないことを確認する。
- symlinkの既存テストを実行する。

## リスク・注意点
- statusの応答時間はremote数と接続状態に依存する。
- remote上のCodeGraph実行には接続先へのCodeGraph導入が必要である。
- SSHコマンドの引用処理を誤ると、引数の誤解釈や意図しない実行につながる。

## 不明点・確認事項
- なし。

## manifestスキーマ
```yaml
version: "1"

hosts:
  home-server:
    hostname: "100.105.236.93"
    user: "takumi"
    identity_file: "~/.ssh/id_rsa"
    port: 22

resources:
  symlinks:
    - name: mind
      workspace_path: mind
      source: 
      git:
        url: git@github.com:Applica-760/mind.git
        branch: main
      boot: true

  remotes:
    - name: esn-lab
      host: home-server
      path: 
      git:
        url: git@github.com:Applica-760/esn-lab.git
        branch: main
      boot: true
```
