import AppKit
import Combine
import SwiftTerm
import SwiftUI

final class TerminalSession: ObservableObject {
    let terminal: LocalProcessTerminalView

    init() {
        let terminal = LocalProcessTerminalView(frame: .zero)
        terminal.font = .monospacedSystemFont(ofSize: 13, weight: .regular)
        terminal.lineSpacing = 1.1
        terminal.nativeBackgroundColor = NSColor(calibratedWhite: 0.1, alpha: 1)
        terminal.nativeForegroundColor = NSColor(calibratedWhite: 0.9, alpha: 1)
        terminal.wantsLayer = true
        terminal.layer?.cornerRadius = 8
        terminal.layer?.masksToBounds = true
        terminal.terminal.setCursorStyle(.steadyBar)
        terminal.startProcess(
            executable: "/bin/zsh",
            args: ["-l"],
            currentDirectory: "\(NSHomeDirectory())/workspace-hub"
        )
        self.terminal = terminal
    }

    deinit {
        terminal.terminate()
    }
}

struct TerminalView: View {
    var body: some View {
        TerminalWidget()
            .padding()
            .navigationTitle("Terminal")
    }
}

struct TerminalWidget: View {
    @EnvironmentObject private var session: TerminalSession

    var body: some View {
        WidgetFrame {
            LocalTerminalView(terminal: session.terminal)
                .frame(maxWidth: .infinity, minHeight: 240)
        }
    }
}

private struct LocalTerminalView: NSViewRepresentable {
    let terminal: LocalProcessTerminalView

    func makeNSView(context: Context) -> LocalProcessTerminalView {
        return terminal
    }

    func updateNSView(_ terminal: LocalProcessTerminalView, context: Context) {}
}

#Preview {
    TerminalView()
        .environmentObject(TerminalSession())
}
