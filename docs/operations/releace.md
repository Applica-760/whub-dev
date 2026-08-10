
# Whub operation release

開発checkoutから、PATH上の`whub`が参照するoperation releaseを更新する手順を定義する。
releaseは`~/.whub/releases/<release-id>`配下の`artifact/`・`venv/`・`release.json`からなるimmutable unitとし、検証が完了するまで`current`を変更しない。

release操作だけは、古い`current` releaseの実装に依存しないよう、cleanな開発checkoutのPython moduleとして実行する。通常の操作は引き続きPATH上の`whub` CLIを使う。

releaseは運用作業であり、Taskの起票・worktreeの作成・Task計画の承認を必要としない。変更済みでcleanな親repositoryをpushしてから、この手順を実行する。

## 前提

- release commandでは`<path>/src`を`PYTHONPATH`に指定し、`uv run --project <path> python -m whub release ...`を使う。
- `build --source <path>`の`<path>`はwhub-devの開発checkoutである。
- `--source`は必須である。config.tomlのworkspace_rootから開発checkoutを推測しない。
- Git worktreeはcleanで、release-idはpackage versionとHEAD commitから決定する。
- frontend依存とPython build環境が利用可能である。

## 実行形式

```sh
source=/path/to/whub
PYTHONPATH="$source/src" uv run --project "$source" python -m whub app down
PYTHONPATH="$source/src" uv run --project "$source" python -m whub release deploy --source "$source"
```

`app down`は`app stopped`または`app not running`で成功することを確認してから
`deploy`を実行する。managed appのプロセスグループへSIGTERM/SIGKILLを送れない実行環境では
`PermissionError`になる。この場合は同じ環境で`deploy`を再試行せず、プロセスを管理できる
実行環境で`app down`を成功させてからreleaseを再開する。失敗した`deploy`は`current`を変更しない。

apply後は、作業中shellのPATHを使わず、次で新releaseとapp起動を確認する。

```sh
~/.local/bin/whub --version
lsof -nP -iTCP:8710 -sTCP:LISTEN
```

## `whub release deploy --source <path>`

- build、verify、applyを順に実行し、buildで決定したrelease-idを後続処理へ引き継ぐ。
- 各処理の停止・復旧条件は、それぞれの単独コマンドと同じである。

## `whub release build --source <path>`

- 管理中のproduction `whub app`を常に停止する。停止済みでも成功とする。
- `app/`で`npm run build`を実行し、`src/whub/webapp/dist/`を生成する。
- HEAD commitを`src/whub/_build.json`へ刻印する。
- `uv build --wheel`でwheelを作成する。
- wheelとrelease-idを`~/.whub/releases/.staging/<release-id>/artifact/`へ保存する。
- build失敗時はstagingを残して、旧currentの`whub app`を再起動する。`current`は変更しない。

## `whub release verify <release-id>`

- staging wheelのpackage version・刻印commit・SHA-256を確認する。
- wheelに`whub/webapp/dist/index.html`とassets、`whub`のentry pointが含まれることを確認する。
- staging内にvenvを作成し、`uv pip install --python <venv>/bin/python <wheel>`で非editable installする。
- staging venvの絶対パスで`whub --version`と`whub task --help`を実行し、release-idと一致することを確認する。
- staging venvの実行は`PYTHONPATH`・`VIRTUAL_ENV`を遮断した環境で行う。呼び出し側の`PYTHONPATH`を継承すると、wheelではなく開発checkoutのsrcを検証してしまう。applyでのvenv再作成も同様に遮断する。
- 成功時にwheel hashと検証結果を含む`release.json`をstagingへ記録する。失敗時は`current`を変更しない。
- verify失敗時は旧currentの`whub app`を再起動する。

## `whub release apply <release-id>`

- `release.json`が検証済みで、staging venvが存在するreleaseだけを対象にする。
- staging unitを`~/.whub/releases/<release-id>`へatomicに配置し、既存の同一release-idは上書きしない。
- venvは絶対pathを含むため、配置後のrelease pathでwheelから再作成する。
- `~/.whub/releases/current`を新releaseへatomicに切り替える。
- 確認を求めず最後まで実行し、新releaseの`whub app`を必ず起動する。
- `~/.local/bin/whub`は`current/venv/bin/`を参照し続けるため、再起動後のappと次回起動から新releaseが使われる。
- applyまたはapp再起動が失敗した場合は旧`current`へ戻し、旧releaseの`whub app`を再起動する。旧releaseはrollback用に削除しない。
