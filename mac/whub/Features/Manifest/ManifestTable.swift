import SwiftData
import SwiftUI
import WhubWorkspace

struct ManifestTable: View {
    @Environment(\.modelContext) private var modelContext
    @Query(sort: \Project.name) private var projects: [Project]
    @State private var selection: PersistentIdentifier?
    @State private var errorMessage: String?
    let addManifest: () -> Void

    var body: some View {
        VStack(spacing: 8) {
            Table(of: Project.self, selection: $selection) {
                TableColumn("Name", value: \.name)
                TableColumn("Workspace Path") { project in
                    Text(project.resource?.workspacePath ?? "—")
                }
            } rows: {
                ForEach(projects, id: \.name) { project in
                    TableRow(project)
                }
            }

            HStack {
                ControlGroup {
                    Button("Add Manifest", systemImage: "plus", action: addManifest)
                    Button("Remove Manifest", systemImage: "minus", action: removeSelectedManifest)
                        .disabled(selection == nil)
                }
                .controlGroupStyle(.automatic)
                .labelStyle(.iconOnly)

                Spacer()
            }
        }
        .alert("Could not remove manifest", isPresented: hasError) {
            Button("OK", role: .cancel) {}
        } message: {
            Text(errorMessage ?? "")
        }
    }

    private var hasError: Binding<Bool> {
        Binding(
            get: { errorMessage != nil },
            set: { if !$0 { errorMessage = nil } }
        )
    }

    private func removeSelectedManifest() {
        guard let selection,
              let project = projects.first(where: { $0.persistentModelID == selection }) else {
            return
        }

        modelContext.delete(project)
        do {
            try modelContext.save()
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}
