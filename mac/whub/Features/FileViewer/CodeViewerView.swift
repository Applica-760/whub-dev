import AppKit
import SwiftUI

struct CodeViewerView: NSViewRepresentable {
    let fileURL: URL

    func makeNSView(context: Context) -> NSScrollView {
        let scrollView = NSTextView.scrollableTextView()
        guard let textView = scrollView.documentView as? NSTextView else {
            fatalError("Expected NSTextView")
        }
        textView.isEditable = false
        textView.font = .monospacedSystemFont(ofSize: 13, weight: .regular)
        textView.textContainerInset = NSSize(width: 12, height: 12)
        return scrollView
    }

    func updateNSView(_ scrollView: NSScrollView, context: Context) {
        guard let textView = scrollView.documentView as? NSTextView else { return }
        let source = (try? String(contentsOf: fileURL, encoding: .utf8)) ?? "Unable to display this file"
        guard textView.string != source else { return }
        textView.textStorage?.setAttributedString(highlighted(source))
    }

    private func highlighted(_ source: String) -> NSAttributedString {
        let result = NSMutableAttributedString(
            string: source,
            attributes: [
                .font: NSFont.monospacedSystemFont(ofSize: 13, weight: .regular),
                .foregroundColor: NSColor.labelColor,
            ]
        )
        apply("\\b(?:\(keywords))\\b", color: .systemPurple, to: result)
        apply(#"\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'"#, color: .systemRed, to: result)
        apply("(?m)//.*$|#.*$", color: .secondaryLabelColor, to: result)
        return result
    }

    private var keywords: String {
        switch fileURL.pathExtension.lowercased() {
        case "py": "and|as|assert|async|await|break|class|continue|def|del|elif|else|except|False|finally|for|from|global|if|import|in|is|lambda|None|nonlocal|not|or|pass|raise|return|True|try|while|with|yield"
        default: "actor|as|associatedtype|await|break|case|catch|class|continue|default|defer|do|else|enum|extension|fallthrough|false|for|func|guard|if|import|in|init|let|nil|operator|protocol|repeat|return|self|some|struct|switch|throw|throws|true|try|typealias|var|where|while"
        }
    }

    private func apply(_ pattern: String, color: NSColor, to string: NSMutableAttributedString) {
        let range = NSRange(location: 0, length: string.length)
        let expression = try? NSRegularExpression(pattern: pattern)
        expression?.enumerateMatches(in: string.string, range: range) { match, _, _ in
            guard let match else { return }
            string.addAttribute(.foregroundColor, value: color, range: match.range)
        }
    }
}
