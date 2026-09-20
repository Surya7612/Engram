import SwiftUI

struct ContentView: View {
    @AppStorage("engram.apiBase") private var apiBase = "https://engram-cjph.onrender.com"
    @State private var screenText = ""
    @State private var question = "What's happening here? What should I check first?"
    @State private var busy = false
    @State private var statusText: String?
    @State private var errorText: String?
    @State private var result: SituationResponseDTO?
    @State private var showSettings = false
    @State private var showAdvancedText = false
    @StateObject private var hotKey = CaptureHotKeyMonitor()

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                header
                primaryActions
                questionField
                if showAdvancedText {
                    screenEditor
                }
                statusBlock
                resultBlock
            }
            .padding(22)
        }
        .frame(minWidth: 680, minHeight: 560)
        .onAppear {
            if screenText.isEmpty {
                screenText = FixtureText.paymentWorkerDatadog
            }
            hotKey.start {
                Task { await captureAndAsk(mode: .window) }
            }
        }
        .onDisappear { hotKey.stop() }
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text("Engram Companion")
                    .font(.title2.weight(.semibold))
                Spacer()
                Button("Settings") { showSettings.toggle() }
            }
            Text("On-call context from what’s on your screen. Capture is explicit—nothing is recorded in the background.")
                .font(.callout)
                .foregroundStyle(.secondary)
            Text("OCR text is sent once to Engram and is not stored as permanent memory.")
                .font(.caption)
                .foregroundStyle(.secondary)
            if showSettings {
                VStack(alignment: .leading, spacing: 8) {
                    Text("API base")
                        .font(.headline)
                    TextField("https://engram-cjph.onrender.com", text: $apiBase)
                        .textFieldStyle(.roundedBorder)
                    Text("Default is the hosted Try API. Use http://127.0.0.1:8000 for local builders.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    Button("Open Screen Recording settings") {
                        ScreenCaptureService.openScreenRecordingSettings()
                    }
                }
                .padding(12)
                .background(Color.secondary.opacity(0.08), in: RoundedRectangle(cornerRadius: 10))
            }
        }
    }

    private var primaryActions: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 10) {
                Button {
                    Task { await captureAndAsk(mode: .window) }
                } label: {
                    label(busy ? "Working…" : "Capture window & ask")
                }
                .buttonStyle(.borderedProminent)
                .disabled(busy)

                Button {
                    Task { await captureAndAsk(mode: .region) }
                } label: {
                    Text("Capture region & ask")
                }
                .disabled(busy)
            }
            HStack(spacing: 10) {
                Button("Use demo fixture") {
                    screenText = FixtureText.paymentWorkerDatadog
                    errorText = nil
                    statusText = "Loaded payment-worker Datadog fixture."
                }
                .disabled(busy)
                Button {
                    Task { await ask() }
                } label: {
                    Text("Ask with current text")
                }
                .disabled(busy || screenText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                Toggle("Show captured text", isOn: $showAdvancedText)
                    .toggleStyle(.checkbox)
            }
            Text("Shortcut: ⌃⌥Space captures the frontmost window and asks Engram (when this window is focused).")
                .font(.caption2)
                .foregroundStyle(.secondary)
        }
    }

    private var questionField: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("Question")
                .font(.headline)
            TextField("What's happening here?", text: $question)
                .textFieldStyle(.roundedBorder)
        }
    }

    private var screenEditor: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("Screen text (editable)")
                .font(.headline)
            TextEditor(text: $screenText)
                .font(.system(.body, design: .monospaced))
                .frame(minHeight: 120)
                .border(Color.secondary.opacity(0.3))
        }
    }

    @ViewBuilder
    private var statusBlock: some View {
        if let statusText {
            Text(statusText)
                .font(.callout)
                .foregroundStyle(.secondary)
        }
        if let errorText {
            Text(errorText)
                .foregroundStyle(.red)
            if errorText.localizedCaseInsensitiveContains("Screen Recording") {
                Button("Open Screen Recording settings") {
                    ScreenCaptureService.openScreenRecordingSettings()
                }
            }
        }
    }

    @ViewBuilder
    private var resultBlock: some View {
        if let result {
            Divider()
            Text("Resolved service: \(result.service)")
                .font(.headline)
            Text(result.answer)
                .textSelection(.enabled)
            if !result.entities.isEmpty {
                Text("Entities")
                    .font(.headline)
                ForEach(result.entities) { entity in
                    Text("• \(entity.kind): \(entity.value)")
                        .font(.callout)
                }
            }
            Text("Evidence")
                .font(.headline)
            ForEach(result.evidence) { item in
                VStack(alignment: .leading, spacing: 2) {
                    Text(item.label)
                        .font(.subheadline.weight(.semibold))
                    Text(item.snippet)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                .padding(.vertical, 2)
            }
            Text(result.note)
                .font(.caption)
                .foregroundStyle(.secondary)
        }
    }

    private func label(_ title: String) -> some View {
        HStack {
            if busy { ProgressView().controlSize(.small) }
            Text(title)
        }
    }

    private enum CaptureMode {
        case window
        case region
    }

    @MainActor
    private func captureAndAsk(mode: CaptureMode) async {
        busy = true
        errorText = nil
        result = nil
        statusText = mode == .window ? "Capturing frontmost window…" : "Drag a region to capture…"
        defer { busy = false }
        do {
            let allowed = await ScreenCaptureService.requestPermissionIfNeeded()
            if !allowed {
                throw ScreenCaptureError.permissionDenied
            }
            let image: CGImage
            switch mode {
            case .window:
                image = try await ScreenCaptureService.captureFrontmostWindowImage()
            case .region:
                image = try await ScreenCaptureService.captureRegionViaSystemUI()
            }
            statusText = "Reading text (Vision OCR)…"
            let raw = try await VisionOCR.recognizeText(in: image)
            screenText = ScreenTextRedactor.redact(raw)
            showAdvancedText = true
            statusText = "Asking Engram…"
            await ask(preserveStatus: true)
        } catch {
            errorText = error.localizedDescription
            statusText = nil
        }
    }

    @MainActor
    private func ask(preserveStatus: Bool = false) async {
        if !preserveStatus {
            busy = true
            errorText = nil
            result = nil
            statusText = "Asking Engram…"
        }
        defer {
            if !preserveStatus { busy = false }
        }
        do {
            result = try await SituationClient(apiBase: apiBase).explain(
                screenText: ScreenTextRedactor.redact(screenText),
                question: question
            )
            statusText = "Done. Screen text was not stored as Engram memory."
        } catch {
            errorText = error.localizedDescription
            statusText = nil
        }
    }
}

#Preview {
    ContentView()
}
