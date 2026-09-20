// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "EngramCompanion",
    platforms: [.macOS(.v14)],
    products: [
        .executable(name: "EngramCompanion", targets: ["EngramCompanion"]),
    ],
    targets: [
        .executableTarget(
            name: "EngramCompanion",
            path: "Sources/EngramCompanion",
            resources: [
                .copy("payment-worker-datadog.txt"),
            ]
        ),
    ]
)
