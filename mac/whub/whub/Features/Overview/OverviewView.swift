import SwiftUI

struct OverviewView: View {
    var body: some View {
        HStack(spacing: 0) {
            column("Projects", items: ["whub-dev", "vault", "portfolio"])
            Divider()
            column("Tasks", items: ["SwiftUI migration", "Vault explorer", "Resource status"])
            Divider()
            column("Activity", items: ["Status: ok", "Vault: updated", "No pending tasks"])
        }
        .navigationTitle("Overview")
    }

    private func column(_ title: String, items: [String]) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(title)
                .font(.headline)

            ForEach(items, id: \.self) { item in
                Text(item)
            }

            Spacer()
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
        .padding()
    }
}

#Preview {
    OverviewView()
}
