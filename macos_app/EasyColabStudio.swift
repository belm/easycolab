import SwiftUI
import AppKit
import AVKit
import UniformTypeIdentifiers
import ObjectiveC.runtime

// MARK: - macOS 应用程序入口

@main
struct EasyColabApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) var appDelegate
    @ObservedObject private var i18n = LanguageManager.shared

    init() {
        Self.migrateLegacyDefaultsIfNeeded()
        SleekScrollBarInstaller.install()
    }

    private static func migrateLegacyDefaultsIfNeeded() {
        let std = UserDefaults.standard
        guard !std.bool(forKey: "migratedToEasyColabSuite") else { return }
        for suiteName in ["app.aevix.studio.macos", "com.colab.aistudio.macos", "com.minimax.h3studio.macos"] {
            if let legacy = UserDefaults(suiteName: suiteName) {
                if std.string(forKey: "colabServerURL") == nil,
                   let url = legacy.string(forKey: "colabServerURL"), !url.isEmpty {
                    std.set(url, forKey: "colabServerURL")
                }
                if std.double(forKey: "totalBudgetCU") == 0 {
                    let cu = legacy.double(forKey: "totalBudgetCU")
                    if cu > 0 { std.set(cu, forKey: "totalBudgetCU") }
                }
                if std.string(forKey: "apiAccessKey") == nil,
                   let key = legacy.string(forKey: "apiAccessKey"), !key.isEmpty {
                    std.set(key, forKey: "apiAccessKey")
                }
                if std.object(forKey: "apiKeyEnabled") == nil,
                   legacy.object(forKey: "apiKeyEnabled") != nil {
                    std.set(legacy.bool(forKey: "apiKeyEnabled"), forKey: "apiKeyEnabled")
                }
                if std.object(forKey: "qwenContextLengthK") == nil,
                   legacy.integer(forKey: "qwenContextLengthK") >= 4 {
                    std.set(legacy.integer(forKey: "qwenContextLengthK"), forKey: "qwenContextLengthK")
                }
                if std.object(forKey: "idleTimeoutMinutes") == nil,
                   legacy.object(forKey: "idleTimeoutMinutes") != nil {
                    std.set(legacy.integer(forKey: "idleTimeoutMinutes"), forKey: "idleTimeoutMinutes")
                }
                if std.string(forKey: "reasoningEffort") == nil,
                   let eff = legacy.string(forKey: "reasoningEffort"), !eff.isEmpty {
                    std.set(eff, forKey: "reasoningEffort")
                }
                if std.dictionary(forKey: "mediaElapsedSecondsMap") == nil,
                   let map = legacy.dictionary(forKey: "mediaElapsedSecondsMap") {
                    std.set(map, forKey: "mediaElapsedSecondsMap")
                }
            }
        }
        std.set(true, forKey: "migratedToEasyColabSuite")
    }

    var body: some Scene {
        WindowGroup("EasyColab") {
            MainStudioView()
                .frame(minWidth: 1300, minHeight: 860)
        }
        .defaultSize(width: 1480, height: 900)
        .windowStyle(.hiddenTitleBar)
        .commands {
            CommandGroup(after: .sidebar) {
                Button(L("切换语言 (中文 / English)", "Switch Language (中文 / English)")) {
                    LanguageManager.shared.toggle()
                }
                .keyboardShortcut("l", modifiers: [.command, .shift])
            }
            CommandGroup(replacing: .help) {
                Button(L("EasyColab 新手引导与使用指南", "EasyColab Quick Start & User Guide")) {
                    NotificationCenter.default.post(name: .openEasyColabGuide, object: nil)
                }
                .keyboardShortcut("/", modifiers: [.command, .shift])
            }
        }
    }
}

class AppDelegate: NSObject, NSApplicationDelegate {
    func applicationDidFinishLaunching(_ notification: Notification) {
        SleekScrollBarInstaller.install()
        NSApp.setActivationPolicy(.regular)
        NSApp.activate(ignoringOtherApps: true)
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
        return true
    }
}

