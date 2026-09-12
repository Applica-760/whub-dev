// swift-tools-version: 6.2

import PackageDescription

let package = Package(
    name: "WhubWorkspace",
    platforms: [.macOS(.v26)],
    products: [
        .library(name: "WhubWorkspace", targets: ["WhubWorkspace"]),
        .executable(name: "whub", targets: ["WhubCLI"]),
    ],
    targets: [
        .target(name: "WhubWorkspace"),
        .executableTarget(name: "WhubCLI", dependencies: ["WhubWorkspace"]),
    ]
)
