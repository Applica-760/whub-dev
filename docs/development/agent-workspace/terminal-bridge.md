# Terminal bridge contract

## Purpose

whub Web appから、Taskに対応する既存のAgent tmux sessionへ接続する。

## Scope

- 初期対象はlocalhost上のWeb appだけとする。外部公開とスマホからの接続は扱わない。
- 接続単位は`project`と`task_id`で特定する一つのtmux sessionとする。
- browserからtmux socket、session名、任意のcommandを指定しない。`agent.tmux_session`が登録済みworktreeから接続先を解決する。
- terminal bridgeはtmux session、shell、Agent processを作成または終了しない。

## Access modes

一つのtmux sessionには複数の接続を許可する。

- `viewer`: terminal出力を受信できる。入力とresizeは送れない。
- `controller`: terminal出力を受信し、入力とresizeを送れる。一つのsessionにつき常に一接続だけとする。

controllerが存在する間、別接続はcontrollerを強制的に奪取できない。controller自身が解放した後だけ、新しいcontrollerを取得できる。

## Lease lifecycle

- controllerの接続が切断された時点で、入力権は即時に失効する。
- Web appの再起動時は、すべての接続と入力権を失効する。
- 再接続した利用者は、空いている入力権を改めて取得する。

## Bridge boundary

- `agent.tmux_session`はAgent tmux sessionの作成、存在確認、終了、attach先解決を担う。
- `agent.terminal_bridge`は解決済みsessionへのPTY attach、terminal入出力の中継、access mode、controller lease、resize制御を担う。
- Web appのWebSocket endpointは接続を受け付けて`agent.terminal_bridge`を呼び出すadapterとし、tmux操作や入力権の判断を持たない。

## Pending protocol details

WebSocketのメッセージ形式、localhost接続におけるOrigin検証の具体的な方法、PTYの実装方式は、terminal bridge実装Taskで決定する。
