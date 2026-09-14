import QuickLookUI
import SwiftUI

private let codeFileExtensions = ["py", "swift"]

struct FileViewerView: View {
    let fileURL: URL?

    var body: some View {
        WidgetFrame {
            if let fileURL {
                if codeFileExtensions.contains(fileURL.pathExtension.lowercased()) {
                    CodeViewerView(fileURL: fileURL)
                } else {
                    QuickLookPreviewView(fileURL: fileURL)
                }
            } else {
                Text("Select a file")
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            }
        }
    }
}

private struct QuickLookPreviewView: NSViewRepresentable {
    let fileURL: URL

    func makeNSView(context: Context) -> QLPreviewView {
        let previewView = QLPreviewView(frame: .zero, style: .normal)!
        previewView.previewItem = fileURL as NSURL
        return previewView
    }

    func updateNSView(_ previewView: QLPreviewView, context: Context) {
        previewView.previewItem = fileURL as NSURL
    }
}

#Preview {
    FileViewerView(fileURL: nil)
}
