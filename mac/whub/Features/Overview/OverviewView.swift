import SwiftUI

struct OverviewView: View {
    @EnvironmentObject private var terminalStore: TerminalStore

    var body: some View {
        let columns = Array(repeating: GridItem(.flexible(), alignment: .top), count: 3)

        ScrollView {
            LazyVGrid(columns: columns, alignment: .leading, spacing: 16) {
            column("Projects", items: ["whub-dev", "vault", "portfolio"])
            column("Tasks", items: ["SwiftUI migration", "Vault explorer", "Resource status"])
            column("Activity", items: ["Status: ok", "Vault: updated", "No pending tasks"])
                StatusWidget()
                TerminalWidget(session: terminalStore.selectedSession)
            }
            .padding()
        }
        .navigationTitle("Overview")
    }

    private func column(_ title: String, items: [String]) -> some View {
        WidgetFrame {
            VStack(alignment: .leading, spacing: 8) {
            ForEach(items, id: \.self) { item in
                Text(item)
            }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
        .frame(maxWidth: .infinity, alignment: .topLeading)
    }
}

#Preview {
    OverviewView()
        .environmentObject(TerminalStore())
}
