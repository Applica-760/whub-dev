# Terminal bridge contract

## Purpose

whub Web appから、Taskに対応する既存のAgent tmux sessionへ接続する。

## Scope

- 初期対象はlocalhost上のWeb appだけとする。外部公開とスマホからの接続は扱わない。
- 接続単位は`project`と`task_id`で特定する一つのtmux sessionとする。
- browserからtmux socket、session名、任意のcommandを指定しない。`agent.tmux_session`が登録済みworktreeから接続先を解決する。
- terminal bridgeはtmux session、shell、Agent processを作成または終了しない。

Operator TerminalはこのTask Terminalとは別の境界である。
`/api/operator-terminals`はtask非依存terminalを一覧・起動し、起動ごとに新しい
Operator ID、workspace-hub rootをCWDとするlogin shell、専用tmux sessionを作る。
`/api/operator-terminals/{operator_id}`のDELETEは指定sessionだけを停止・runtime
recordから除外し、同じIDへの接続を以後拒否する。Browserの切断・再読み込みは
Operator sessionを停止しない。

## Access modes

一つのtmux sessionには複数の接続を許可する。

- `viewer`: terminal出力を受信できる。入力とresizeは送れない。
- `controller`: terminal出力を受信し、入力とresizeを送れる。一つのsessionにつき常に一接続だけとする。

controllerが存在する間、別接続はcontrollerを強制的に奪取できない。controller自身が解放した後だけ、新しいcontrollerを取得できる。

## Lease lifecycle

- controllerの接続が切断された時点で、入力権は即時に失効する。
- clientはunmount時に`release`を送信する。送信できない切断でもserverが接続単位で入力権を解放する。
- Web appの再起動時は、すべての接続と入力権を失効する。
- 再接続した利用者は、空いている入力権を改めて取得する。

## WebSocket protocol

clientからserverへのメッセージは、次のJSON text frameとする。

- `{"type":"claim"}`: controller leaseを取得する。
- `{"type":"release"}`: controller leaseを解放する。
- `{"type":"input","data":"..."}`: terminal入力を送信する。`data`の空白文字は保持する。
- `{"type":"resize","columns":120,"rows":40}`: PTYをresizeする。`columns`と`rows`は1以上1000以下とする。

serverからclientへのPTY出力はbinary frameとする。clientはストリームとしてUTF-8を
decodeし、frame境界で分割された文字を保持する。不正なclient frameは
`{"type":"error","detail":"invalid frame"}`で通知する。入力とresizeはcontrollerだけが実行できる。

接続時は同一hostのHTTPまたはHTTPS Originだけを許可する。

## Bridge boundary

- `agent.tmux_session`はAgent tmux sessionの作成、存在確認、終了、attach先解決を担う。
- `agent.terminal_bridge`は解決済みsessionへのPTY attach、terminal入出力の中継、access mode、controller lease、resize制御を担う。
- Web appのWebSocket endpointは接続を受け付けて`agent.terminal_bridge`を呼び出すadapterとし、tmux操作や入力権の判断を持たない。
- Operator TerminalはTask Terminalとは別のcontroller lease registryを持つ。ただしPTY
  attach・resize・frame形式は同じterminal bridge契約を利用する。resizeは接続ごとに
  最後に適用したcolumns/rowsと異なる場合だけtmuxへ中継する。

## PTY lifecycle

接続ごとにPTY attachを一つ作成し、WebSocket入力とPTY出力をそれぞれ一つの長寿命pumpで処理する。片方が終了した時点でもう片方をcancelし、controller leaseを解放してPTY attachmentを閉じる。

PTY読取はfile descriptorのreadable状態を待ってからevent loop上で行う。cancel不能なblocking readをworker threadへ投入しない。process終了待ちはevent loop外で行う。
