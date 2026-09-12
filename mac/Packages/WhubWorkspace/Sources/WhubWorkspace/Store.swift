import Foundation
import SwiftData

public enum Store {
    public static let storeURL: URL = {
        let directory = FileManager.default.urls(
            for: .applicationSupportDirectory,
            in: .userDomainMask
        )[0]
        return directory
            .appendingPathComponent("whub", isDirectory: true)
            .appendingPathComponent("workspace.store")
    }()

    public static func makeContainer(inMemory: Bool = false) throws -> ModelContainer {
        let configuration: ModelConfiguration

        if inMemory {
            configuration = ModelConfiguration(
                "WhubWorkspace",
                isStoredInMemoryOnly: true,
                cloudKitDatabase: .none
            )
        } else {
            try FileManager.default.createDirectory(
                at: storeURL.deletingLastPathComponent(),
                withIntermediateDirectories: true
            )
            configuration = ModelConfiguration(
                "WhubWorkspace",
                url: storeURL,
                cloudKitDatabase: .none
            )
        }

        return try ModelContainer(
            for: Host.self,
            Resource.self,
            LocalResource.self,
            RemoteResource.self,
            Project.self,
            configurations: configuration
        )
    }

    @MainActor
    public static func projects(in container: ModelContainer) throws -> [Project] {
        let descriptor = FetchDescriptor<Project>(
            sortBy: [SortDescriptor(\Project.name)]
        )
        return try container.mainContext.fetch(descriptor)
    }

    @MainActor
    public static func project(named name: String, in container: ModelContainer) throws -> Project? {
        try projects(in: container).first { $0.name == name }
    }
}
