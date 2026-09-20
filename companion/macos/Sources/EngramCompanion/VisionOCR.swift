import CoreGraphics
import Foundation
import Vision

enum VisionOCRError: LocalizedError {
    case empty
    case failed(String)

    var errorDescription: String? {
        switch self {
        case .empty:
            return "No text could be read from the capture. Try a clearer window or use the demo fixture."
        case let .failed(message):
            return "OCR failed: \(message)"
        }
    }
}

enum VisionOCR {
    static func recognizeText(in image: CGImage) async throws -> String {
        try await withCheckedThrowingContinuation { continuation in
            let request = VNRecognizeTextRequest { request, error in
                if let error {
                    continuation.resume(throwing: VisionOCRError.failed(error.localizedDescription))
                    return
                }
                let observations = (request.results as? [VNRecognizedTextObservation]) ?? []
                let lines = observations.compactMap { $0.topCandidates(1).first?.string }
                let text = lines.joined(separator: "\n").trimmingCharacters(in: .whitespacesAndNewlines)
                if text.isEmpty {
                    continuation.resume(throwing: VisionOCRError.empty)
                } else {
                    continuation.resume(returning: text)
                }
            }
            request.recognitionLevel = .accurate
            request.usesLanguageCorrection = true
            let handler = VNImageRequestHandler(cgImage: image, options: [:])
            do {
                try handler.perform([request])
            } catch {
                continuation.resume(throwing: VisionOCRError.failed(error.localizedDescription))
            }
        }
    }
}
