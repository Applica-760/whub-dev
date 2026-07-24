
# Whub operation release

開発checkoutから、PATH上の`whub`と`wflow`が参照するoperation releaseを更新する手順を定義する。
releaseは`~/.whub/releases/<release-id>`配下の`artifact/`・`venv/`・`release.json`からなるimmutable unitとし、検証が完了するまで`current`を変更しない。

## 前提

- `whub release build --source <path>`の`<path>`はwhub-devの開発checkoutである。
- `--source`は必須である。config.tomlのworkspace_rootから開発checkoutを推測しない。
- Git worktreeはcleanで、release-idはpackage versionとHEAD commitから決定する。
- frontend依存とPython build環境が利用可能である。

## `whub release build --source <path>`

- 管理中のproduction `whub app`を常に停止する。停止済みでも成功とする。
- `app/`で`npm run build`を実行し、`src/whub/webapp/dist/`を生成する。
- HEAD commitを`src/whub/_build.json`へ刻印する。
- `uv build --wheel`でwheelを作成する。
- wheelとrelease-idを`~/.whub/releases/.staging/<release-id>/artifact/`へ保存する。
- build失敗時はstagingを残して、旧currentの`whub app`を再起動する。`current`は変更しない。

## `whub release verify <release-id>`

- staging wheelのpackage version・刻印commit・SHA-256を確認する。
- wheelに`whub/webapp/dist/index.html`とassets、`whub`・`wflow`のentry pointが含まれることを確認する。
- staging内にvenvを作成し、`uv pip install --python <venv>/bin/python <wheel>`で非editable installする。
- staging venvの絶対パスで`whub --version`と`wflow --help`を実行し、release-idと一致することを確認する。
- 成功時にwheel hashと検証結果を含む`release.json`をstagingへ記録する。失敗時は`current`を変更しない。
- verify失敗時は旧currentの`whub app`を再起動する。

## `whub release apply <release-id>`

- `release.json`が検証済みで、staging venvが存在するreleaseだけを対象にする。
- staging unitを`~/.whub/releases/<release-id>`へatomicに配置し、既存の同一release-idは上書きしない。
- `~/.whub/releases/current`を新releaseへatomicに切り替える。
- 確認を求めず最後まで実行し、新releaseの`whub app`を必ず起動する。
- `~/.local/bin/whub`と`~/.local/bin/wflow`は`current/venv/bin/`を参照し続けるため、再起動後のappと次回起動から新releaseが使われる。
- applyまたはapp再起動が失敗した場合は旧`current`へ戻し、旧releaseの`whub app`を再起動する。旧releaseはrollback用に削除しない。
