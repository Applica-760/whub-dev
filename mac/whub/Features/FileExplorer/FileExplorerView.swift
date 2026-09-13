import SwiftData
import SwiftUI
import WhubCore

struct FileExplorerView: View {
    @Query(sort: \Project.name) private var projects: [Project]
    @State private var selectedProject: String?

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            Picker("Project", selection: $selectedProject) {
                if projects.isEmpty {
                    Text("---").tag(nil as String?)
                } else {
                    ForEach(projects, id: \.name) { project in
                        Text(project.name).tag(Optional(project.name))
                    }
                }
            }
            .pickerStyle(.menu)
            .labelsHidden()

            Divider()

            FileOutlineView(rootURL: rootURL)
                .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
        .onAppear {
            selectedProject = projects.first?.name
        }
        .onChange(of: projects.map(\.name)) { _, names in
            if !names.contains(selectedProject ?? "") {
                selectedProject = names.first
            }
        }
    }

    private var rootURL: URL? {
        guard
            let selectedProject,
            let project = projects.first(where: { $0.name == selectedProject }),
            let resource = project.resource as? LocalResource
        else {
            return nil
        }
        return URL(fileURLWithPath: resource.localPath)
    }
}

#Preview {
    FileExplorerView()
}
