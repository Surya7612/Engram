import AppKit
import Foundation
import ScreenCaptureKit

enum ScreenCaptureError: LocalizedError {
    case noDisplay
    case noWindow
    case permissionDenied
    case captureFailed(String)

    var errorDescription: String? {
        switch self {
        case .noDisplay:
            return "No display available to capture."
        case .noWindow:
            return "No capturable window found. Open a window (e.g. Fake Datadog) and try again."
        case .permissionDenied:
            return "Screen Recording permission is required. Enable it in System Settings → Privacy & Security → Screen Recording."
        case let .captureFailed(message):
            return "Capture failed: \(message)"
        }
    }
}

enum ScreenCaptureService {
    static func requestPermissionIfNeeded() async -> Bool {
        do {
            _ = try await SCShareableContent.excludingDesktopWindows(false, onScreenWindowsOnly: true)
            return true
        } catch {
            return false
        }
    }

    static func openScreenRecordingSettings() {
        if let url = URL(string: "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture") {
            NSWorkspace.shared.open(url)
        }
    }

    static func captureFrontmostWindowImage() async throws -> CGImage {
        let content: SCShareableContent
        do {
            content = try await SCShareableContent.excludingDesktopWindows(false, onScreenWindowsOnly: true)
        } catch {
            throw ScreenCaptureError.permissionDenied
        }

        let frontNumber = NSWorkspace.shared.frontmostApplication?.processIdentifier
        let candidates = content.windows.filter { window in
            window.frame.width >= 80 && window.frame.height >= 80
        }
        let match =
            candidates.first(where: { $0.owningApplication?.processID == frontNumber })
            ?? candidates.first
        guard let window = match else {
            throw ScreenCaptureError.noWindow
        }

        let filter = SCContentFilter(desktopIndependentWindow: window)
        let config = SCStreamConfiguration()
        let width = max(Int(window.frame.width), 1)
        let height = max(Int(window.frame.height), 1)
        config.width = width
        config.height = height
        config.showsCursor = false
        config.capturesAudio = false

        do {
            return try await SCScreenshotManager.captureImage(contentFilter: filter, configuration: config)
        } catch {
            throw ScreenCaptureError.captureFailed(error.localizedDescription)
        }
    }

    /// Interactive region capture via system screenshot selection (user drags a region).
    static func captureRegionViaSystemUI() async throws -> CGImage {
        let temp = FileManager.default.temporaryDirectory
            .appendingPathComponent("engram-capture-\(UUID().uuidString).png")
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/sbin/screencapture")
        process.arguments = ["-x", "-i", "-r", temp.path]
        do {
            try process.run()
            process.waitUntilExit()
        } catch {
            throw ScreenCaptureError.captureFailed(error.localizedDescription)
        }
        guard process.terminationStatus == 0, FileManager.default.fileExists(atPath: temp.path) else {
            throw ScreenCaptureError.captureFailed("Region capture cancelled or failed.")
        }
        defer { try? FileManager.default.removeItem(at: temp) }
        guard let nsImage = NSImage(contentsOf: temp),
              let cgImage = nsImage.cgImage(forProposedRect: nil, context: nil, hints: nil)
        else {
            throw ScreenCaptureError.captureFailed("Could not read region image.")
        }
        return cgImage
    }
}
