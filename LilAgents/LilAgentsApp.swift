import SwiftUI
import AppKit
import Sparkle

@main
struct LilAgentsApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) var appDelegate

    var body: some Scene {
        Settings { EmptyView() }
    }
}

class AppDelegate: NSObject, NSApplicationDelegate {
    var controller: LilAgentsController?
    var statusItem: NSStatusItem?
    let updaterController = SPUStandardUpdaterController(startingUpdater: true, updaterDelegate: nil, userDriverDelegate: nil)

    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.accessory)
        controller = LilAgentsController()
        controller?.start()
        setupMenuBar()
    }

    func applicationWillTerminate(_ notification: Notification) {
        controller?.characters.forEach { $0.session?.terminate() }
    }

    // MARK: - Menu Bar

    func setupMenuBar() {
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.squareLength)
        if let button = statusItem?.button {
            button.image = NSImage(named: "MenuBarIcon") ?? NSImage(systemSymbolName: "figure.walk", accessibilityDescription: "lil agents")
        }

        let menu = NSMenu()

        // Character submenus (built dynamically)
        if let characters = controller?.characters {
            for (index, char) in characters.enumerated() {
                let charItem = NSMenuItem(title: char.config.displayName, action: nil, keyEquivalent: index < 9 ? "\(index + 1)" : "")
                let charMenu = NSMenu()

                // Show/Hide toggle
                let toggleItem = NSMenuItem(title: "Show/Hide", action: #selector(toggleCharacter(_:)), keyEquivalent: "")
                toggleItem.representedObject = char
                toggleItem.state = char.window?.isVisible == true ? .on : .off
                charMenu.addItem(toggleItem)

                // Status line (non-actionable)
                let statusText: String
                switch char.runtimeState.sessionState {
                case .idle:       statusText = "Status: Idle"
                case .starting:   statusText = "Status: Starting"
                case .ready:      statusText = "Status: Ready"
                case .streaming:  statusText = "Status: Streaming"
                case .stopping:   statusText = "Status: Stopping"
                case .failed(let msg):
                    statusText = msg == "Asset missing" ? "Status: Asset Missing" : "Status: Failed"
                case .providerUnavailable:
                    statusText = "Status: Provider Unavailable"
                }
                let statusMenuItem = NSMenuItem(title: statusText, action: nil, keyEquivalent: "")
                statusMenuItem.isEnabled = false
                charMenu.addItem(statusMenuItem)

                charMenu.addItem(NSMenuItem.separator())

                // Provider selection
                for provider in AgentProvider.allCases {
                    let providerItem = NSMenuItem(title: provider.displayName, action: #selector(switchCharacterProvider(_:)), keyEquivalent: "")
                    providerItem.representedObject = ["character": char, "provider": provider] as [String: Any]
                    providerItem.state = char.runtimeState.selectedProvider == provider ? .on : .off
                    charMenu.addItem(providerItem)
                }

                charItem.submenu = charMenu
                menu.addItem(charItem)
            }
        }

        menu.addItem(NSMenuItem.separator())

        // Security submenu
        let securityItem = NSMenuItem(title: "Security", action: nil, keyEquivalent: "")
        let securityMenu = NSMenu()
        for profile in AutomationProfile.allCases {
            let item = NSMenuItem(title: profile.displayName, action: #selector(switchAutomationProfile(_:)), keyEquivalent: "")
            item.representedObject = profile
            item.state = profile == AutomationProfile.current ? .on : .off
            securityMenu.addItem(item)
        }
        securityItem.submenu = securityMenu
        menu.addItem(securityItem)

        // Sounds
        let soundItem = NSMenuItem(title: "Sounds", action: #selector(toggleSounds(_:)), keyEquivalent: "")
        soundItem.state = WalkerCharacter.soundsEnabled ? .on : .off
        menu.addItem(soundItem)

        // Theme submenu (unchanged logic)
        let themeItem = NSMenuItem(title: "Style", action: nil, keyEquivalent: "")
        let themeMenu = NSMenu()
        for (i, theme) in PopoverTheme.allThemes.enumerated() {
            let item = NSMenuItem(title: theme.name, action: #selector(switchTheme(_:)), keyEquivalent: "")
            item.tag = i
            item.state = i == 0 ? .on : .off
            themeMenu.addItem(item)
        }
        themeItem.submenu = themeMenu
        menu.addItem(themeItem)

        // Display submenu (unchanged logic)
        let displayItem = NSMenuItem(title: "Display", action: nil, keyEquivalent: "")
        let displayMenu = NSMenu()
        displayMenu.delegate = self
        let autoItem = NSMenuItem(title: "Auto (Main Display)", action: #selector(switchDisplay(_:)), keyEquivalent: "")
        autoItem.tag = -1
        autoItem.state = .on
        displayMenu.addItem(autoItem)
        displayMenu.addItem(NSMenuItem.separator())
        for (i, screen) in NSScreen.screens.enumerated() {
            let item = NSMenuItem(title: screen.localizedName, action: #selector(switchDisplay(_:)), keyEquivalent: "")
            item.tag = i
            item.state = .off
            displayMenu.addItem(item)
        }
        displayItem.submenu = displayMenu
        menu.addItem(displayItem)

        menu.addItem(NSMenuItem.separator())

        let updateItem = NSMenuItem(title: "Check for Updates…", action: #selector(SPUStandardUpdaterController.checkForUpdates(_:)), keyEquivalent: "")
        updateItem.target = updaterController
        menu.addItem(updateItem)

        menu.addItem(NSMenuItem.separator())

        let quitItem = NSMenuItem(title: "Quit", action: #selector(quitApp), keyEquivalent: "q")
        menu.addItem(quitItem)

        statusItem?.menu = menu
    }

    // MARK: - Menu Actions

    @objc func switchTheme(_ sender: NSMenuItem) {
        let idx = sender.tag
        guard idx < PopoverTheme.allThemes.count else { return }
        PopoverTheme.current = PopoverTheme.allThemes[idx]

        if let themeMenu = sender.menu {
            for item in themeMenu.items {
                item.state = item.tag == idx ? .on : .off
            }
        }

        controller?.characters.forEach { char in
            let wasOpen = char.isIdleForPopover
            if wasOpen { char.popoverWindow?.orderOut(nil) }
            char.popoverWindow = nil
            char.terminalView = nil
            char.thinkingBubbleWindow = nil
            if wasOpen {
                char.createPopoverWindow()
                if let session = char.session, !session.history.isEmpty {
                    char.terminalView?.replayHistory(session.history)
                }
                char.updatePopoverPosition()
                char.popoverWindow?.orderFrontRegardless()
                char.popoverWindow?.makeKey()
                if let terminal = char.terminalView {
                    char.popoverWindow?.makeFirstResponder(terminal.inputField)
                }
            }
        }
    }

    @objc func switchDisplay(_ sender: NSMenuItem) {
        let idx = sender.tag
        controller?.pinnedScreenIndex = idx

        if let displayMenu = sender.menu {
            for item in displayMenu.items {
                item.state = item.tag == idx ? .on : .off
            }
        }
    }

    @objc func toggleCharacter(_ sender: NSMenuItem) {
        guard let char = sender.representedObject as? WalkerCharacter else { return }
        if char.window.isVisible {
            char.window.orderOut(nil)
            char.queuePlayer.pause()
            char.runtimeState.isVisible = false
            sender.state = .off
        } else {
            char.window.orderFrontRegardless()
            char.runtimeState.isVisible = true
            sender.state = .on
        }
    }

    @objc func switchCharacterProvider(_ sender: NSMenuItem) {
        guard let info = sender.representedObject as? [String: Any],
              let char = info["character"] as? WalkerCharacter,
              let provider = info["provider"] as? AgentProvider else { return }

        char.switchProvider(to: provider)

        // Update checkmarks in submenu
        if let charMenu = sender.menu {
            for item in charMenu.items {
                if let itemInfo = item.representedObject as? [String: Any],
                   itemInfo["character"] as? WalkerCharacter === char {
                    let itemProvider = itemInfo["provider"] as? AgentProvider
                    item.state = itemProvider == provider ? .on : .off
                }
            }
        }
    }

    @objc func switchAutomationProfile(_ sender: NSMenuItem) {
        guard let profile = sender.representedObject as? AutomationProfile else { return }

        if profile == .unattended {
            let alert = NSAlert()
            alert.messageText = "Enable Unattended Mode?"
            alert.informativeText = "This gives AI agents the highest level of autonomous execution. They can run commands and modify files without asking for confirmation."
            alert.alertStyle = .warning
            alert.addButton(withTitle: "Enable")
            alert.addButton(withTitle: "Cancel")
            if alert.runModal() != .alertFirstButtonReturn {
                return
            }
        }

        AutomationProfile.current = profile

        // Update checkmarks
        if let securityMenu = sender.menu {
            for item in securityMenu.items {
                item.state = (item.representedObject as? AutomationProfile) == profile ? .on : .off
            }
        }

        // Restart all active sessions with new profile
        controller?.characters.forEach { $0.restartSession() }
    }

    @objc func toggleDebug(_ sender: NSMenuItem) {
        guard let debugWin = controller?.debugWindow else { return }
        if debugWin.isVisible {
            debugWin.orderOut(nil)
            sender.state = .off
        } else {
            debugWin.orderFrontRegardless()
            sender.state = .on
        }
    }

    @objc func toggleSounds(_ sender: NSMenuItem) {
        WalkerCharacter.soundsEnabled.toggle()
        sender.state = WalkerCharacter.soundsEnabled ? .on : .off
    }

    @objc func quitApp() {
        NSApp.terminate(nil)
    }
}

extension AppDelegate: NSMenuDelegate {}
