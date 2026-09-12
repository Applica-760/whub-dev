import SwiftData
import SwiftUI
import WhubWorkspace

struct AppView: View {
    private enum Section: CaseIterable, Hashable {
        case overview
        case terminal
        case todo
        case vault
        case status
        case timer

        var label: String {
            switch self {
            case .overview: "Overview"
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
            case .status: "tablecells"
            case .timer: "timer"
            case .vault: "tray.full"
            case .terminal: "terminal"
            case .todo: "list.bullet.clipboard"
            }
        }

        @ViewBuilder
        var content: some View {
            switch self {
            case .overview: OverviewView()
            case .status: StatusView()
            case .timer: TimerView()
            case .vault: VaultExplorerView()
            case .terminal: TerminalView()
            case .todo: TodoView()
            }
        }
    }

    @State private var section = Section.overview

    @Query(sort: \Project.name) private var projects: [Project]

    var body: some View {
        NavigationSplitView {
            List(projects, id: \.name) { project in
                Text(project.name)
            }
            .navigationTitle("Projects")
        } detail: {
            section.content
        }
        .frame(minWidth: 700, minHeight: 430)
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

                SettingsLink {
                    Label("Settings", systemImage: "gearshape")
                }
                .labelStyle(.iconOnly)
            }
        }
    }
}

#Preview {
    AppView()
}
