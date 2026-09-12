import SwiftUI

struct WidgetFrame<Content: View>: View {
    private let title: String
    private let content: Content

    init(_ title: String, @ViewBuilder content: () -> Content) {
        self.title = title
        self.content = content()
    }

    var body: some View {
        GroupBox(title) {
            content
        }
    }
}

#Preview {
    WidgetFrame("Widget") { Text("Content") }
}
