import SwiftUI

struct TabBar: View {
    let title: String
    let systemImage: String
    let action: () -> Void

    var body: some View {
        Button(title, systemImage: systemImage, action: action)
            .buttonStyle(.bordered)
            .accessibilityAddTraits(.isSelected)
    }
}

#Preview {
    TabBar(title: "Terminal 1", systemImage: "terminal") {}
}
