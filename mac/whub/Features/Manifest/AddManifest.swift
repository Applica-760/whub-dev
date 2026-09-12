import SwiftData
import SwiftUI
import WhubWorkspace

struct AddManifest: View {
    @Environment(\.dismiss) private var dismiss
    @Environment(\.modelContext) private var modelContext
    @Query(sort: \Project.name) private var projects: [Project]
    @State private var name = ""
    @State private var errorMessage: String?

    var body: some View {
        AddManifestForm(name: $name, cancel: dismiss.callAsFunction, submit: addManifest)
            .alert("Could not save manifest", isPresented: hasError) {
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

    private func addManifest() {
        let name = name.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !name.isEmpty else { return }
        guard !projects.contains(where: { $0.name == name }) else {
            errorMessage = "A manifest named \(name) already exists."
            return
        }

        modelContext.insert(Project(name: name))
        do {
            try modelContext.save()
            dismiss()
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}
