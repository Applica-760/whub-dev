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
        VStack(spacing: 8) {
            HStack(alignment: .bottom) {
                TerminalTabBar()

                Spacer()

                ControlGroup {
                    Button("Add Terminal", systemImage: "plus") {}
                    Button("Close Terminal", systemImage: "minus") {}
                }
                .controlGroupStyle(.automatic)
                .labelStyle(.iconOnly)
            }

            TerminalWidget()
        }
        .padding(.horizontal)
        .padding(.bottom)
        .padding(.top, 2)
        .navigationTitle("Terminal")
    }
}

private struct TerminalTabBar: View {
    var body: some View {
        Button("Terminal 1", systemImage: "terminal") {}
            .buttonStyle(.plain)
            .padding(.horizontal, 12)
            .frame(height: 28)
            .background(.background, in: RoundedRectangle(cornerRadius: 6))
            .overlay {
                RoundedRectangle(cornerRadius: 6)
                    .stroke(.quaternary)
            }
            .accessibilityAddTraits(.isSelected)
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
