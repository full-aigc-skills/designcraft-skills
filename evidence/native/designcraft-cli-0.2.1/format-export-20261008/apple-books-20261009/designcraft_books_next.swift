import AppKit
import CoreGraphics
import ApplicationServices
let apps = NSRunningApplication.runningApplications(withBundleIdentifier: "com.apple.iBooksX")
guard AXIsProcessTrusted(), apps.count == 1, let app = apps.first else { fatalError("Books accessibility preflight unavailable") }
let source = CGEventSource(stateID: .hidSystemState)
let down = CGEvent(keyboardEventSource: source, virtualKey: 124, keyDown: true)!
let up = CGEvent(keyboardEventSource: source, virtualKey: 124, keyDown: false)!
down.postToPid(app.processIdentifier)
up.postToPid(app.processIdentifier)
print("Books right-arrow posted")
