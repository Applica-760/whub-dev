import AppKit
import SwiftTerm
import SwiftUI

struct TerminalView: View {
    var body: some View {
        TerminalWidget()
            .padding()
            .navigationTitle("Terminal")
    }
}

struct TerminalWidget: View {
    var body: some View {
        WidgetFrame {
            LocalTerminalView()
                .frame(maxWidth: .infinity, minHeight: 240)
        }
    }
}

private struct LocalTerminalView: NSViewRepresentable {
    func makeNSView(context: Context) -> LocalProcessTerminalView {
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
        return terminal
    }

    func updateNSView(_ terminal: LocalProcessTerminalView, context: Context) {}

    static func dismantleNSView(_ terminal: LocalProcessTerminalView, coordinator: ()) {
        terminal.terminate()
    }
}

#Preview {
    TerminalView()
}
