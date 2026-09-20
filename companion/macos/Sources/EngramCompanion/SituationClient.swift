import Foundation

enum FixtureText {
    static var paymentWorkerDatadog: String {
        if let url = Bundle.module.url(forResource: "payment-worker-datadog", withExtension: "txt"),
           let text = try? String(contentsOf: url, encoding: .utf8)
        {
            return text
        }
        return """
        Datadog APM · Production · payment-worker
        Service: payment-worker
        Endpoint: POST /settlements
        Error: TimeoutException
        P95 latency ↑ 2.4s (baseline 180ms)
        """
    }
}

struct SituationResponseDTO: Decodable {
    let service: String
    let question: String
    let answer: String
    let ephemeral: Bool
    let note: String
    let entities: [EntityDTO]
    let evidence: [EvidenceDTO]
}

struct EntityDTO: Decodable, Identifiable {
    var id: String { "\(kind)-\(value)" }
    let kind: String
    let value: String
}

struct EvidenceDTO: Decodable, Identifiable {
    var id: String { artifact_id }
    let artifact_type: String
    let artifact_id: String
    let label: String
    let snippet: String
}

enum SituationClientError: LocalizedError {
    case badURL
    case http(Int, String)
    case decode

    var errorDescription: String? {
        switch self {
        case .badURL:
            return "Invalid API base URL."
        case let .http(code, body):
            return "API error \(code): \(body)"
        case .decode:
            return "Could not decode Engram response."
        }
    }
}

struct SituationClient {
    var apiBase: String

    func explain(screenText: String, question: String) async throws -> SituationResponseDTO {
        let trimmed = apiBase.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        guard let url = URL(string: "\(trimmed)/situation") else {
            throw SituationClientError.badURL
        }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        let payload: [String: Any] = [
            "screen_text": screenText,
            "question": question,
            "mode": "adaptive",
        ]
        request.httpBody = try JSONSerialization.data(withJSONObject: payload)
        let (data, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse else {
            throw SituationClientError.decode
        }
        guard (200 ..< 300).contains(http.statusCode) else {
            let body = String(data: data, encoding: .utf8) ?? ""
            throw SituationClientError.http(http.statusCode, body)
        }
        do {
            return try JSONDecoder().decode(SituationResponseDTO.self, from: data)
        } catch {
            throw SituationClientError.decode
        }
    }
}
