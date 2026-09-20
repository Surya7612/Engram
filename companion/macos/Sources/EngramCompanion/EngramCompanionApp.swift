import SwiftUI

@main
struct EngramCompanionApp: App {
    var body: some Scene {
        WindowGroup("Engram Companion") {
            ContentView()
        }
        .defaultSize(width: 740, height: 760)
        .commands {
            CommandGroup(replacing: .newItem) {}
        }
    }
}
