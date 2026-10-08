import Foundation
import CoreGraphics
let allowed = CGPreflightScreenCaptureAccess()
let entries = CGWindowListCopyWindowInfo([.optionAll, .excludeDesktopElements], kCGNullWindowID) as? [[String: Any]] ?? []
let windows = entries.compactMap { item -> [String: Any]? in
    let owner = item[kCGWindowOwnerName as String] as? String ?? ""
    guard owner == "Books" || owner == "图书" else { return nil }
    return ["owner": owner, "windowId": item[kCGWindowNumber as String] ?? 0, "bounds": item[kCGWindowBounds as String] ?? [:], "layer": item[kCGWindowLayer as String] ?? 0, "onScreen": item[kCGWindowIsOnscreen as String] ?? false]
}
let data = try JSONSerialization.data(withJSONObject: ["screenCaptureAuthorized": allowed, "booksWindows": windows], options: [.sortedKeys])
print(String(data: data, encoding: .utf8)!)
