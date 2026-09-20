import AppKit
import Combine

/// ⌃⌥Space → capture window & ask. Avoids Max’s ⌘R-style shortcut.
@MainActor
final class CaptureHotKeyMonitor: ObservableObject {
    private var monitor: Any?

    func start(onTrigger: @escaping () -> Void) {
        stop()
        monitor = NSEvent.addLocalMonitorForEvents(matching: .keyDown) { event in
            // Control + Option + Space
            if event.modifierFlags.contains(.control),
               event.modifierFlags.contains(.option),
               event.keyCode == 49
            {
                onTrigger()
                return nil
            }
            return event
        }
    }

    func stop() {
        if let monitor {
            NSEvent.removeMonitor(monitor)
            self.monitor = nil
        }
    }

    deinit {
        if let monitor {
            NSEvent.removeMonitor(monitor)
        }
    }
}
