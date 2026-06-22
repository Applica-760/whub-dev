# boot配布構造とCLIの簡素化

## 目的・前提・方針案

- `.my-boot`を配布先と同じディレクトリ構造へ揃え、`boot.py`のパス変換と個別分岐を削減する
- `whub boot deploy`を`whub boot`へ短縮し、用途が一つだけのClick groupを廃止する
- 冒頭の配布仕様定数、managed block検証、settings.jsonマージ、プロジェクト固有設定の保持は維持する
- 旧`whub boot deploy`との互換処理は設けず、関連ドキュメントを`whub boot`へ統一する
- `.my-boot`は別Gitリポジトリで既存の未コミット変更があるため、内容を保持して構造だけを移行する
- コミットは`.my-boot`とworkspace-hubで分け、各リポジトリ内の変更単位を独立して検証する

## 計画

### Phase 1: 現行仕様の固定
- [x] 配布対象、更新戦略、保持条件を整理し、初回配布・再配布・異常マーカーの回帰ケースを定義する
- [x] `.my-boot`とworkspace-hubの既存差分を記録し、本タスク外の変更を上書きしない境界を確定する

### Phase 2: `.my-boot`構造の移行
- [x] `claude/`を`.claude/`、`codex/`を`.codex/`へ移動し、`mcp.json`をルートの`.mcp.json`へ配置する
- [x] `.codex/AGENTS.md`をルート`AGENTS.md`へ移動し、配布先と同形の構造へ統一する
- [x] `install.sh`を新構造へ追従させ、managed blockとsettings.jsonの非破壊更新を維持する
- [x] `.my-boot/README.md`の構成説明と利用例を新構造へ更新する

### Phase 3: boot配布実装の簡素化
- [x] 配布元の相対パスを配布先へそのまま対応させ、`_REMAP`と`_ROOT_MARKERS`に依存する変換を削除する
- [x] 相対パスごとのmanaged block・JSONマージ・通常コピー戦略を冒頭の定数群から選択する
- [x] ディレクトリ走査と更新処理を整理し、プロジェクト固有ファイルを削除しない挙動を維持する
- [x] AppleDouble除去とskip対象が新しい`.claude/`・`.codex/`構造で機能することを確認する

### Phase 4: CLIの短縮
- [x] `boot`をClick groupから直接実行コマンドへ変更し、`boot_deploy`を統合する
- [x] `whub boot`のhelp・正常配布・対象なし・配布元なしの出力と終了動作を確認する
- [x] 旧`whub boot deploy`が提供されないことを確認する

### Phase 5: ドキュメントと検証
- [x] README、CLI仕様、ディレクトリ構成、ADR、task文書を現行CLI実装へ更新する
- [x] サンドボックス内の模擬ファイル構成で初回配布、再配布の冪等性、固有記述保持、JSONマージを検証する
- [x] `.my-boot/install.sh`を隔離先へ2回実行し、whub実装と同じ配布結果になることを確認する
- [x] 構文、import、CLI help、差分検査を実行し、実プロジェクトへ配布せず完了判定する

## 実行ログ

### 試行 1: install.shの配布元マーカー欠損を検出できない
- 実施内容: 期待するマーカー文字列を引数化し、配布元・配布先の個数と順序を検証した
- 結果: 配布元・配布先の欠損、重複、逆順をエラーにできた
- 判断: 続行

## 結果

- `.my-boot`を配布先と同形へ変更し、whubとinstall.shの非破壊配布結果を統一した
- `whub boot`へCLIを短縮し、旧`whub boot deploy`を廃止した
- 初回・再配布、固有記述保持、JSONマージ、異常マーカー、AppleDouble除去を隔離環境で検証した
- CLI・manifest・ディレクトリ構成・ADRを現行実装へ更新し、構文・import・help・差分検査を通過した
