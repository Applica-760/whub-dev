import SwiftUI

struct TodoView: View {
    private let todos = ["SwiftUIの基本を確認する", "Vault Explorerを作る", "Resource Statusを接続する"]

    var body: some View {
        List(todos, id: \.self) { todo in
            Label(todo, systemImage: "circle")
        }
        .navigationTitle("Todo")
    }
}

#Preview {
    TodoView()
}
