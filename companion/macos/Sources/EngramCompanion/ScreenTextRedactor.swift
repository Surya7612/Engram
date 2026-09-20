import Foundation

enum ScreenTextRedactor {
    private static let patterns: [NSRegularExpression] = {
        let raw = [
            #"\bsk-[A-Za-z0-9_\-]{10,}\b"#,
            #"\bghp_[A-Za-z0-9]{20,}\b"#,
            #"\bgithub_pat_[A-Za-z0-9_]{20,}\b"#,
            #"(?i)\bBearer\s+[A-Za-z0-9\-._~+/]+=*\b"#,
            #"(?i)\b(api[_-]?key|secret|password|token)\s*[:=]\s*\S+"#,
        ]
        return raw.compactMap { try? NSRegularExpression(pattern: $0) }
    }()

    static func redact(_ text: String) -> String {
        var output = text
        for pattern in patterns {
            let range = NSRange(output.startIndex..<output.endIndex, in: output)
            output = pattern.stringByReplacingMatches(
                in: output,
                options: [],
                range: range,
                withTemplate: "[REDACTED]"
            )
        }
        return output
    }
}
