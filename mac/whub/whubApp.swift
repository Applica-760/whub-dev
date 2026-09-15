//
//  whubApp.swift
//  whub
//
//  Created by 村上匠 on 2026/09/10.
//

import SwiftData
import SwiftUI
import WhubCore

@main
struct whubApp: App {
    @StateObject private var terminalStore = TerminalStore()
    @State private var section = AppView.Section.overview
    private let workspaceContainer: ModelContainer

    init() {
        do {
            workspaceContainer = try Container.make()
        } catch {
            fatalError("Unable to open workspace store: \(error)")
        }
    }

    var body: some Scene {
        WindowGroup {
            AppView(section: $section)
                .environmentObject(terminalStore)
        }
        .modelContainer(workspaceContainer)

        Settings {
            SettingsView()
        }
        .modelContainer(workspaceContainer)
    }
}
