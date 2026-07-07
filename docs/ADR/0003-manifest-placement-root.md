# ADR-0003: マニフェストをwhub data_dirに配置する

- **Status:** Accepted
- **Date:** 2026-06-19

## Context

単一YAMLマニフェスト（ADR-0001）の配置先を決める必要がある。候補はルート直下・config/・.hub/だった。

ADR-0008により、個人データをworkspace-hub repoから分離し、任意のprivate data_dirへ置く方針に変更した。

## Decision

whub data_dirの`manifest.yaml`として配置する。

data_dirは`<workspace-hub>/.whub/config.toml`の`data_dir`で登録し、CLIは`paths.py`経由で解決する。

## Rationale

- manifest/todos/downloadsなどのwhub自己データをworkspace-hub repoから分離できる
- data_dirを任意パスとして登録でき、vault固有パスをパッケージへハードコードしない
- CLI側のパス解決を`paths.py`に集約し、CWD依存を避けられる

## Consequences

- CLIは`paths.manifest_path()`でdata_dirの`manifest.yaml`を読む
- `<workspace-hub>/.whub/config.toml`は個人パスを含むためgit管理しない
