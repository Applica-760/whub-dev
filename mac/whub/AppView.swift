import SwiftUI

struct AppView: View {
    private enum Section: CaseIterable, Hashable {
        case overview
        case file
        case terminal
        case todo
        case vault
        case status
        case timer

        var label: String {
            switch self {
            case .overview: "Overview"
            case .file: "File"
            case .status: "Status"
            case .timer: "Timer"
            case .vault: "Vault"
            case .terminal: "Terminal"
            case .todo: "Todo"
            }
        }

        var systemImage: String {
            switch self {
            case .overview: "rectangle.3.group"
            case .file: "doc.text"
            case .status: "tablecells"
            case .timer: "timer"
            case .vault: "tray.full"
            case .terminal: "terminal"
            case .todo: "list.bullet.clipboard"
            }
        }

        @ViewBuilder
        func content(fileURL: URL?) -> some View {
            switch self {
            case .overview: OverviewView()
            case .file: FileViewerView(fileURL: fileURL)
            case .status: StatusView()
            case .timer: TimerView()
            case .vault: VaultExplorerView()
            case .terminal: TerminalView()
            case .todo: TodoView()
            }
        }
    }

    @StateObject private var terminalStore = TerminalStore()
    @State private var section = Section.overview
    @State private var selectedFileURL: URL?
    @Environment(\.openSettings) private var openSettings

    var body: some View {
        NavigationSplitView {
            FileExplorerView { fileURL in
                selectedFileURL = fileURL
                section = .file
            }
                .navigationSplitViewColumnWidth(min: 260, ideal: 320, max: 640)
        } detail: {
            section.content(fileURL: selectedFileURL)
        }
        .frame(minWidth: 950, minHeight: 550)
        .toolbar {
            ToolbarItemGroup(placement: .primaryAction) {
                Picker("ページ", selection: $section) {
                    ForEach(Section.allCases, id: \.self) { section in
                        Label(section.label, systemImage: section.systemImage)
                            .tag(section)
                    }
                }
                .pickerStyle(.segmented)
                .labelsHidden()

                Button {
                    openSettings()
                } label: {
                    Label("Settings", systemImage: "gearshape")
                }
                .labelStyle(.iconOnly)
            }
        }
        .environmentObject(terminalStore)
    }
}

#Preview {
    AppView()
}
