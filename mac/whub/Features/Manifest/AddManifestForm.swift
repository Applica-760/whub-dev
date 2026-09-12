import SwiftUI

struct AddManifestForm: View {
    @Binding var name: String
    let cancel: () -> Void
    let submit: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("Add Manifest")
                .font(.headline)
            TextField("Manifest Name", text: $name)
            HStack {
                Spacer()
                Button("Cancel", action: cancel)
                Button("Add", action: submit)
                    .keyboardShortcut(.defaultAction)
                    .disabled(name.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
            }
        }
        .padding()
        .frame(width: 360)
    }
}
