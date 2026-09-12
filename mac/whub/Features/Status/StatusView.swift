//
//  ResourceStatusView.swift
//  whub
//
//  Created by 村上匠 on 2026/09/10.
//

import SwiftUI

private struct ResourceStatus: Identifiable {
    var id: String { project }

    let project: String
    let state: String
    let type: String
}

struct ResourceStatusView: View {
    private let resources = [
        ResourceStatus(project: "whub-dev", state: "ok", type: "symlink"),
        ResourceStatus(project: "vault", state: "ok", type: "symlink"),
        ResourceStatus(project: "la-il", state: "slow", type: "remote"),
    ]

    var body: some View {
        GroupBox("Resource Status") {
            Table(resources) {
                TableColumn("Project", value: \.project)
                TableColumn("State", value: \.state)
                TableColumn("Type", value: \.type)
            }
        }
        .padding()
        .navigationTitle("Resource Status")
    }
}

#Preview {
    ResourceStatusView()
}
