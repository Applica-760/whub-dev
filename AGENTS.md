## 参照先

- コマンド一覧・セットアップは`README.md`、詳細は`docs/reference/`
- 実装構造・開発規約は`docs/architecture/`と`docs/development/`
- Remote GUI sessionの運用は`docs/operations/session.md`

## Operation release

- operation releaseの正本は`docs/operations/releace.md`とし、`whub release build --source <path>`、`verify`、`apply`を順に実行する。
- `build --source`にはcleanなwhub開発checkoutを明示し、release-idやsource pathを推測しない。
- apply後の動作確認は`~/.local/bin/whub`を使う。作業中shellの`PATH`には起動時点の旧release venvが残るため、素の`whub`は`current`の切替を反映せず旧releaseを指す。
