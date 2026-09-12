import SwiftUI

struct AppView: View {
    private enum Section: CaseIterable, Hashable {
        case overview
        case resourceStatus
        case vault
        case todo

        var label: String {
            switch self {
            case .overview: "Overview"
            case .resourceStatus: "リソース"
            case .vault: "Vault"
            case .todo: "Todo"
            }
        }

        var systemImage: String {
            switch self {
            case .overview: "rectangle.3.group"
            case .resourceStatus: "tablecells"
            case .vault: "tray.full"
            case .todo: "list.bullet.clipboard"
            }
        }

        @ViewBuilder
        var content: some View {
            switch self {
            case .overview: OverviewView()
            case .resourceStatus: ResourceStatusView()
            case .vault: VaultExplorerView()
            case .todo: TodoView()
            }
        }
    }

    @State private var section = Section.overview

    private let projects = ["whub-dev", "vault", "portfolio", "research-hub"]

    var body: some View {
        NavigationSplitView {
            List(projects, id: \.self) { project in
                Label(project, systemImage: "folder")
            }
            .navigationTitle("Projects")
        } detail: {
            section.content
        }
        .frame(minWidth: 700, minHeight: 430)
        .toolbar {
            ToolbarItem(placement: .primaryAction) {
                Picker("ページ", selection: $section) {
                    ForEach(Section.allCases, id: \.self) { section in
                        Label(section.label, systemImage: section.systemImage)
                            .tag(section)
                    }
                }
                .pickerStyle(.segmented)
                .labelsHidden()
            }
        }
    }
}

#Preview {
    AppView()
}
