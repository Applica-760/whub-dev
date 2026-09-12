import SwiftUI
import WhubWorkspace

struct SettingsView: View {
    @State private var showsAddManifest = false

    var body: some View {
        TabView {
            Form {
                LabeledContent("Workspace Store") {
                    Text(Store.storeURL.path)
                        .textSelection(.enabled)
                }
            }
            .padding()
            .tabItem { Label("General", systemImage: "gearshape") }

            ManifestTable {
                showsAddManifest = true
            }
                .padding()
                .tabItem { Label("Manifests", systemImage: "folder") }

            ContentUnavailableView("Advanced", systemImage: "slider.horizontal.3")
                .tabItem { Label("Advanced", systemImage: "slider.horizontal.3") }
        }
        .frame(width: 720, height: 480)
        .sheet(isPresented: $showsAddManifest) {
            AddManifest()
        }
    }
}

#Preview {
    SettingsView()
}
