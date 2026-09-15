import AppKit
import Combine
import SwiftTerm
import SwiftUI

final class TerminalSession: Identifiable {
    let id = UUID()
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

final class TerminalStore: ObservableObject {
    @Published private(set) var sessions: [TerminalSession]
    @Published private(set) var selectedSessionID: TerminalSession.ID

    init() {
        let session = TerminalSession()
        sessions = [session]
        selectedSessionID = session.id
    }

    var selectedSession: TerminalSession {
        sessions.first { $0.id == selectedSessionID } ?? sessions[0]
    }

    func add() {
        let session = TerminalSession()
        sessions.append(session)
        selectedSessionID = session.id
    }

    func select(_ id: TerminalSession.ID) {
        selectedSessionID = id
    }
}

struct TerminalView: View {
    @EnvironmentObject private var store: TerminalStore

    var body: some View {
        VStack(spacing: 8) {
            HStack(alignment: .bottom) {
                ForEach(Array(store.sessions.enumerated()), id: \.element.id) { index, session in
                    TabBar(title: "Terminal \(index + 1)", systemImage: "terminal") {
                        store.select(session.id)
                    }
                }

                Spacer()

                ControlGroup {
                    Button("Add Terminal", systemImage: "plus") {
                        store.add()
                    }
                    Button("Close Terminal", systemImage: "minus") {}
                }
                .controlGroupStyle(.automatic)
                .labelStyle(.iconOnly)
            }

            TerminalWidget(session: store.selectedSession)
        }
        .padding(.horizontal)
        .padding(.bottom)
        .padding(.top, 8)
        .navigationTitle("Terminal")
    }
}

struct TerminalWidget: View {
    let session: TerminalSession

    var body: some View {
        WidgetFrame {
            LocalTerminalView(terminal: session.terminal)
                .id(session.id)
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
        .environmentObject(TerminalStore())
}
