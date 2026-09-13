import SwiftData
import SwiftUI
import WhubCore

struct ProjectTable: View {
    @Query(sort: \Project.name) private var projects: [Project]
    @State private var selection: PersistentIdentifier?

    var body: some View {
        VStack(spacing: 8) {
            Table(of: Project.self, selection: $selection) {
                TableColumn("Name", value: \.name)
                TableColumn("Workspace Path") { project in
                    Text(project.resource.workspacePath)
                }
            } rows: {
                ForEach(projects) { project in
                    TableRow(project)
                }
            }

            HStack {
                ControlGroup {
                    Button("Add Project", systemImage: "plus", action: {})
                    Button("Remove Project", systemImage: "minus", action: {})
                }
                .controlGroupStyle(.automatic)
                .labelStyle(.iconOnly)
                .disabled(true)

                Spacer()
            }
        }
    }
}
