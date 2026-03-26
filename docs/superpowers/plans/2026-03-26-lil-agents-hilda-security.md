# Lil Agents: Hilda + Security + Per-Character Agent Binding — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Hilda (West Highland Terrier character), three-level automation profiles, and per-character AI provider binding to the lil-agents macOS dock app.

**Architecture:** Extract hardcoded character definitions into `CharacterConfig` structs. Separate runtime state into `CharacterRuntimeState` with session state machine and generation guard. Each session class maps automation profiles to its own CLI flags internally. Menu is rebuilt dynamically from config array.

**Tech Stack:** Swift, AppKit, AVFoundation, UserDefaults

---

## File Map

| File | Responsibility |
|------|---------------|
| **NEW** `LilAgents/CharacterConfig.swift` | `WalkTiming`, `CharacterConfig` struct, static built-in character definitions (Bruce, Jazz, Hilda) |
| **NEW** `LilAgents/CharacterRuntimeState.swift` | `SessionState` enum, `CharacterRuntimeState` struct, `AutomationProfile` enum with UserDefaults helpers |
| `LilAgents/AgentSession.swift` | Add `systemPrompt` and `automationProfile` params to `createSession()` |
| `LilAgents/ClaudeSession.swift` | Accept systemPrompt + automationProfile in init; conditionally add `--dangerously-skip-permissions` |
| `LilAgents/CodexSession.swift` | Accept systemPrompt + automationProfile in init; map profile to `--full-auto` / `--auto-edit` / nothing |
| `LilAgents/CopilotSession.swift` | Accept systemPrompt + automationProfile in init; conditionally add `--allow-all` |
| `LilAgents/WalkerCharacter.swift` | Init from `CharacterConfig`; hold `CharacterRuntimeState`; per-character provider; generation guard on callbacks; asset check; updated onboarding text |
| `LilAgents/LilAgentsController.swift` | Bootstrap from config array; session restart orchestration |
| `LilAgents/LilAgentsApp.swift` | Dynamic N-character menu; per-character provider submenus; Security submenu; migration logic |

---

### Task 1: CharacterConfig and WalkTiming structs

**Files:**
- Create: `LilAgents/CharacterConfig.swift`

- [ ] **Step 1: Create `CharacterConfig.swift` with data structures**

```swift
import AppKit

struct WalkTiming {
    let accelStart: Double
    let fullSpeedStart: Double
    let decelStart: Double
    let walkStop: Double
    let videoDuration: Double
}

struct CharacterConfig {
    let id: String
    let displayName: String
    let videoName: String
    let characterColor: NSColor
    let yOffset: CGFloat
    let flipXOffset: CGFloat
    let startPosition: CGFloat
    let initialPauseRange: ClosedRange<Double>
    let walkTiming: WalkTiming
    let walkAmountRange: ClosedRange<CGFloat>
    let defaultProvider: AgentProvider
    let systemPrompt: String?
    let isEnabledByDefault: Bool
}

extension CharacterConfig {
    static let bruce = CharacterConfig(
        id: "bruce",
        displayName: "Bruce",
        videoName: "walk-bruce-01",
        characterColor: NSColor(red: 0.4, green: 0.72, blue: 0.55, alpha: 1.0),
        yOffset: -3,
        flipXOffset: 0,
        startPosition: 0.3,
        initialPauseRange: 0.5...2.0,
        walkTiming: WalkTiming(accelStart: 3.0, fullSpeedStart: 3.75, decelStart: 8.0, walkStop: 8.5, videoDuration: 10.0),
        walkAmountRange: 0.4...0.65,
        defaultProvider: .claude,
        systemPrompt: nil,
        isEnabledByDefault: true
    )

    static let jazz = CharacterConfig(
        id: "jazz",
        displayName: "Jazz",
        videoName: "walk-jazz-01",
        characterColor: NSColor(red: 1.0, green: 0.4, blue: 0.0, alpha: 1.0),
        yOffset: -7,
        flipXOffset: -9,
        startPosition: 0.7,
        initialPauseRange: 8.0...14.0,
        walkTiming: WalkTiming(accelStart: 3.9, fullSpeedStart: 4.5, decelStart: 8.0, walkStop: 8.75, videoDuration: 10.0),
        walkAmountRange: 0.35...0.6,
        defaultProvider: .claude,
        systemPrompt: nil,
        isEnabledByDefault: true
    )

    static let hilda = CharacterConfig(
        id: "hilda",
        displayName: "Hilda",
        videoName: "walk-hilda-01",
        characterColor: NSColor(red: 0.9, green: 0.88, blue: 0.85, alpha: 1.0),
        yOffset: 0,    // TBD: tune after asset creation
        flipXOffset: 0, // TBD: tune after asset creation
        startPosition: 0.5,
        initialPauseRange: 4.0...8.0,
        walkTiming: WalkTiming(accelStart: 2.5, fullSpeedStart: 3.2, decelStart: 7.5, walkStop: 8.0, videoDuration: 10.0),
        walkAmountRange: 0.3...0.5,
        defaultProvider: .claude,
        systemPrompt: """
            You are Hilda, a friendly West Highland White Terrier. You are helpful, \
            professional, and knowledgeable. Occasionally use dog-related expressions \
            naturally (like "let me dig into that" or "I'll fetch that for you"), \
            but keep it subtle and never at the expense of clarity.
            """,
        isEnabledByDefault: true
    )

    static let allBuiltIn: [CharacterConfig] = [.bruce, .jazz, .hilda]
}
```

- [ ] **Step 2: Verify it compiles**

Run: `xcodebuild build -project LilAgents.xcodeproj -scheme LilAgents -quiet 2>&1 | tail -5`

Note: The project may use `.xcodeproj` or `.xcworkspace`. Check what exists first with `ls *.xcodeproj *.xcworkspace` in the project root. Adjust build command accordingly. If SPM-based, use `swift build`.

- [ ] **Step 3: Commit**

```bash
git add LilAgents/CharacterConfig.swift
git commit -m "feat: add CharacterConfig and WalkTiming data structures with built-in character definitions"
```

---

### Task 2: SessionState, CharacterRuntimeState, and AutomationProfile

**Files:**
- Create: `LilAgents/CharacterRuntimeState.swift`

- [ ] **Step 1: Create `CharacterRuntimeState.swift`**

```swift
import Foundation

// MARK: - Session State Machine

enum SessionState: Equatable {
    case idle
    case starting
    case ready
    case streaming
    case stopping
    case failed(String)
    case providerUnavailable
}

// MARK: - Character Runtime State

struct CharacterRuntimeState {
    var isVisible: Bool
    var selectedProvider: AgentProvider
    var sessionState: SessionState = .idle
    var sessionGeneration: UUID = UUID()
}

// MARK: - Automation Profile

enum AutomationProfile: String, CaseIterable {
    case safe
    case balanced
    case unattended

    var displayName: String {
        switch self {
        case .safe:       return "Safe"
        case .balanced:   return "Balanced"
        case .unattended: return "Unattended"
        }
    }

    private static let defaultsKey = "automationProfile"

    static var current: AutomationProfile {
        get {
            let raw = UserDefaults.standard.string(forKey: defaultsKey) ?? "safe"
            return AutomationProfile(rawValue: raw) ?? .safe
        }
        set {
            UserDefaults.standard.set(newValue.rawValue, forKey: defaultsKey)
        }
    }
}
```

- [ ] **Step 2: Verify it compiles**

Same build command as Task 1.

- [ ] **Step 3: Commit**

```bash
git add LilAgents/CharacterRuntimeState.swift
git commit -m "feat: add SessionState, CharacterRuntimeState, and AutomationProfile"
```

---

### Task 3: Update AgentSession and session classes for automationProfile + systemPrompt

**Files:**
- Modify: `LilAgents/AgentSession.swift:52-58` (createSession method)
- Modify: `LilAgents/ClaudeSession.swift:49-58` (launchProcess arguments)
- Modify: `LilAgents/CodexSession.swift:57-64` (send arguments)
- Modify: `LilAgents/CopilotSession.swift:59-72` (send arguments)

- [ ] **Step 1: Update `AgentProvider.createSession()` in `AgentSession.swift`**

Change the `createSession()` method (lines 52-58) to accept parameters:

```swift
func createSession(systemPrompt: String? = nil, automationProfile: AutomationProfile = .current) -> any AgentSession {
    switch self {
    case .claude:  return ClaudeSession(systemPrompt: systemPrompt, automationProfile: automationProfile)
    case .codex:   return CodexSession(systemPrompt: systemPrompt, automationProfile: automationProfile)
    case .copilot: return CopilotSession(systemPrompt: systemPrompt, automationProfile: automationProfile)
    }
}
```

Also add per-character provider storage helpers below the existing `current` property:

```swift
static func provider(forCharacter id: String) -> AgentProvider {
    let raw = UserDefaults.standard.string(forKey: "agent_\(id)") ?? "claude"
    return AgentProvider(rawValue: raw) ?? .claude
}

static func setProvider(_ provider: AgentProvider, forCharacter id: String) {
    UserDefaults.standard.set(provider.rawValue, forKey: "agent_\(id)")
}
```

- [ ] **Step 2: Update `ClaudeSession` to accept init params**

Add stored properties and init at the top of `ClaudeSession` (after line 21, below all property declarations):

```swift
private let systemPrompt: String?
private let automationProfile: AutomationProfile

init(systemPrompt: String? = nil, automationProfile: AutomationProfile = .safe) {
    self.systemPrompt = systemPrompt
    self.automationProfile = automationProfile
}
```

In `launchProcess(binaryPath:)` (lines 52-58), change the arguments array:

```swift
var args = [
    "-p",
    "--output-format", "stream-json",
    "--input-format", "stream-json",
    "--verbose"
]
if automationProfile == .unattended {
    args.append("--dangerously-skip-permissions")
}
if let prompt = systemPrompt {
    args.append(contentsOf: ["--system-prompt", prompt])
}
proc.arguments = args
```

- [ ] **Step 3: Update `CodexSession` to accept init params**

Add stored properties and init at the top of `CodexSession` (after line 21, below all property declarations):

```swift
private let systemPrompt: String?
private let automationProfile: AutomationProfile

init(systemPrompt: String? = nil, automationProfile: AutomationProfile = .safe) {
    self.systemPrompt = systemPrompt
    self.automationProfile = automationProfile
}
```

In `send(message:)` (lines 60-64), change argument construction:

```swift
let effectiveMessage: String
if isFirstTurn, let prompt = systemPrompt {
    effectiveMessage = "\(prompt)\n\n\(message)"
} else {
    effectiveMessage = message
}

var baseArgs = ["exec"]
if !isFirstTurn {
    baseArgs.append(contentsOf: ["resume", "--last"])
}
baseArgs.append(contentsOf: ["--json", "--skip-git-repo-check"])
switch automationProfile {
case .unattended:
    baseArgs.append("--full-auto")
case .balanced:
    baseArgs.append("--auto-edit") // allows file edits, prompts for shell commands
case .safe:
    break // no auto flags; may hang if Codex prompts interactively — known limitation
}
baseArgs.append(effectiveMessage)
proc.arguments = baseArgs
```

- [ ] **Step 4: Update `CopilotSession` to accept init params**

Add stored properties and init at the top of `CopilotSession` (after line 22, below all property declarations):

```swift
private let systemPrompt: String?
private let automationProfile: AutomationProfile

init(systemPrompt: String? = nil, automationProfile: AutomationProfile = .safe) {
    self.systemPrompt = systemPrompt
    self.automationProfile = automationProfile
}
```

In `send(message:)` (lines 62-72), change argument construction:

```swift
let effectiveMessage: String
if isFirstTurn, let prompt = systemPrompt {
    effectiveMessage = "\(prompt)\n\n\(message)"
} else {
    effectiveMessage = message
}

var args = ["-p", effectiveMessage]
if !isFirstTurn {
    args.insert("--continue", at: 0)
}
if useJsonOutput {
    args.append(contentsOf: ["--output-format", "json"])
} else {
    args.append("-s")
}
if automationProfile == .unattended {
    args.append("--allow-all")
}
proc.arguments = args
```

- [ ] **Step 5: Verify it compiles**

Same build command. There will be warnings about unused `AgentProvider.current` — that's expected, we'll clean it up in Task 6.

- [ ] **Step 6: Commit**

```bash
git add LilAgents/AgentSession.swift LilAgents/ClaudeSession.swift LilAgents/CodexSession.swift LilAgents/CopilotSession.swift
git commit -m "feat: add automationProfile and systemPrompt support to all session classes"
```

---

### Task 4: Refactor WalkerCharacter to use CharacterConfig

**Files:**
- Modify: `LilAgents/WalkerCharacter.swift`

This is the largest task. We need to:
1. Change init to accept `CharacterConfig`
2. Add `CharacterRuntimeState` and generation guard
3. Use per-character provider instead of global
4. Add asset existence check
5. Update onboarding text

- [ ] **Step 1: Replace init and stored properties**

Replace lines 4-60 of `WalkerCharacter.swift`. The character config fields replace the scattered `var` declarations:

```swift
class WalkerCharacter {
    let config: CharacterConfig
    var runtimeState: CharacterRuntimeState

    var window: NSWindow!
    var playerLayer: AVPlayerLayer!
    var queuePlayer: AVQueuePlayer!
    var looper: AVPlayerLooper!

    let videoWidth: CGFloat = 1080
    let videoHeight: CGFloat = 1920
    let displayHeight: CGFloat = 200
    var displayWidth: CGFloat { displayHeight * (videoWidth / videoHeight) }

    // Walk timing derived from config
    var videoDuration: CFTimeInterval { config.walkTiming.videoDuration }
    var accelStart: CFTimeInterval { config.walkTiming.accelStart }
    var fullSpeedStart: CFTimeInterval { config.walkTiming.fullSpeedStart }
    var decelStart: CFTimeInterval { config.walkTiming.decelStart }
    var walkStop: CFTimeInterval { config.walkTiming.walkStop }
    var walkAmountRange: ClosedRange<CGFloat> { config.walkAmountRange }
    var yOffset: CGFloat { config.yOffset }
    var flipXOffset: CGFloat { config.flipXOffset }
    var characterColor: NSColor { config.characterColor }

    // Walk state
    var playCount = 0
    var walkStartTime: CFTimeInterval = 0
    var positionProgress: CGFloat = 0.0
    var isWalking = false
    var isPaused = true
    var pauseEndTime: CFTimeInterval = 0
    var goingRight = true
    var walkStartPos: CGFloat = 0.0
    var walkEndPos: CGFloat = 0.0
    var currentTravelDistance: CGFloat = 500.0
    var walkStartPixel: CGFloat = 0.0
    var walkEndPixel: CGFloat = 0.0

    // Onboarding
    var isOnboarding = false

    // Popover state
    var isIdleForPopover = false
    var popoverWindow: NSWindow?
    var terminalView: TerminalView?
    var session: (any AgentSession)?
    var clickOutsideMonitor: Any?
    var escapeKeyMonitor: Any?
    var currentStreamingText = ""
    weak var controller: LilAgentsController?
    var themeOverride: PopoverTheme?
    var isAgentBusy: Bool { session?.isBusy ?? false }
    var thinkingBubbleWindow: NSWindow?

    init(config: CharacterConfig) {
        self.config = config
        self.runtimeState = CharacterRuntimeState(
            isVisible: config.isEnabledByDefault,
            selectedProvider: AgentProvider.provider(forCharacter: config.id)
        )
        self.positionProgress = config.startPosition
    }
```

- [ ] **Step 2: Add asset check to `setup()`**

At the top of `setup()` (line 64), add asset existence check:

```swift
func setup() -> Bool {
    guard let videoURL = Bundle.main.url(forResource: config.videoName, withExtension: "mov") else {
        print("Video \(config.videoName) not found — character \(config.id) disabled")
        runtimeState.sessionState = .failed("Asset missing")
        return false
    }
    // ... rest of setup unchanged ...
    return true
}
```

Note: change return type from `Void` to `Bool`. The rest of setup() stays the same, just remove the early `return` and add `return true` at the end.

- [ ] **Step 3: Update `openPopover()` to use per-character provider**

In `openPopover()` (around line 196-201), replace the session creation block:

```swift
// OLD:
if session == nil {
    let newSession = AgentProvider.current.createSession()
    session = newSession
    wireSession(newSession)
    newSession.start()
}

// NEW:
if session == nil {
    runtimeState.sessionState = .starting
    let provider = runtimeState.selectedProvider
    let newSession = provider.createSession(
        systemPrompt: config.systemPrompt,
        automationProfile: AutomationProfile.current
    )
    session = newSession
    wireSession(newSession)
    newSession.start()
    runtimeState.sessionState = .ready
}
```

Also update `wireSession` callbacks to track streaming state (see Step 4).

- [ ] **Step 4: Update `wireSession` to use per-character provider name and generation guard**

Replace the `wireSession` method (lines 339-369):

```swift
private func wireSession(_ session: any AgentSession, providerName: String? = nil) {
    let name = providerName ?? runtimeState.selectedProvider.displayName
    let generation = runtimeState.sessionGeneration

    session.onText = { [weak self] text in
        guard let self = self, self.runtimeState.sessionGeneration == generation else { return }
        self.runtimeState.sessionState = .streaming
        self.currentStreamingText += text
        self.terminalView?.appendStreamingText(text)
    }

    session.onTurnComplete = { [weak self] in
        guard let self = self, self.runtimeState.sessionGeneration == generation else { return }
        self.runtimeState.sessionState = .ready
        self.terminalView?.endStreaming()
        self.playCompletionSound()
        self.showCompletionBubble()
    }

    session.onError = { [weak self] text in
        guard let self = self, self.runtimeState.sessionGeneration == generation else { return }
        self.runtimeState.sessionState = .failed(text)
        self.terminalView?.appendError(text)
    }

    session.onToolUse = { [weak self] toolName, input in
        guard let self = self, self.runtimeState.sessionGeneration == generation else { return }
        let summary = self.formatToolInput(input)
        self.terminalView?.appendToolUse(toolName: toolName, summary: summary)
    }

    session.onToolResult = { [weak self] summary, isError in
        guard let self = self, self.runtimeState.sessionGeneration == generation else { return }
        self.terminalView?.appendToolResult(summary: summary, isError: isError)
    }

    session.onProcessExit = { [weak self] in
        guard let self = self, self.runtimeState.sessionGeneration == generation else { return }
        self.terminalView?.endStreaming()
        self.terminalView?.appendError("\(name) session ended.")
    }
}
```

- [ ] **Step 5: Add provider switch method**

Add this method to `WalkerCharacter`:

```swift
func switchProvider(to provider: AgentProvider) {
    guard provider != runtimeState.selectedProvider else { return }

    // 1. Persist
    AgentProvider.setProvider(provider, forCharacter: config.id)

    // 2. Stop old session
    runtimeState.sessionState = .stopping
    session?.terminate()
    session = nil

    // 3. Invalidate old callbacks
    runtimeState.sessionGeneration = UUID()
    runtimeState.selectedProvider = provider

    // 4. Clear UI
    if isIdleForPopover {
        closePopover()
    }
    popoverWindow?.orderOut(nil)
    popoverWindow = nil
    terminalView = nil
    thinkingBubbleWindow?.orderOut(nil)
    thinkingBubbleWindow = nil

    runtimeState.sessionState = .idle
}

func restartSession() {
    session?.terminate()
    session = nil
    runtimeState.sessionGeneration = UUID()

    if isIdleForPopover {
        closePopover()
    }
    popoverWindow?.orderOut(nil)
    popoverWindow = nil
    terminalView = nil
    thinkingBubbleWindow?.orderOut(nil)
    thinkingBubbleWindow = nil

    runtimeState.sessionState = .idle
}
```

- [ ] **Step 6: Update onboarding text**

In `openOnboardingPopover()` (around line 139-147), update the welcome message:

```swift
let welcome = """
hey! we're bruce, jazz, and hilda — your lil dock agents.

click any of us to open an AI chat. we'll walk around while you work and let you know when we're thinking.

check the menu bar icon (top right) for themes, sounds, and more options.

click anywhere outside to dismiss, then click us again to start chatting.
"""
```

- [ ] **Step 7: Set initial pause from config**

Remove the line `self.positionProgress = config.startPosition` from init (it's already there from Step 1). The `pauseEndTime` is set by the controller in Task 5 using `config.initialPauseRange`.

- [ ] **Step 8: Verify it compiles**

Build will likely fail because `LilAgentsController` still uses old init. That's expected — we fix it in Task 5.

- [ ] **Step 9: Commit**

```bash
git add LilAgents/WalkerCharacter.swift
git commit -m "feat: refactor WalkerCharacter to use CharacterConfig with per-character provider and generation guard"
```

---

### Task 5: Refactor LilAgentsController to use CharacterConfig array

**Files:**
- Modify: `LilAgents/LilAgentsController.swift:10-49`

- [ ] **Step 1: Replace `start()` method**

Replace the entire `start()` method (lines 10-50):

```swift
func start() {
    for config in CharacterConfig.allBuiltIn {
        let char = WalkerCharacter(config: config)
        if char.setup() {
            char.pauseEndTime = CACurrentMediaTime() + Double.random(in: config.initialPauseRange)
            characters.append(char)
        }
    }

    characters.forEach { $0.controller = self }

    setupDebugLine()
    startDisplayLink()

    if !UserDefaults.standard.bool(forKey: Self.onboardingKey) {
        triggerOnboarding()
    }
}
```

- [ ] **Step 2: Verify it compiles**

Build will still have issues in `LilAgentsApp.swift` due to hardcoded menu — that's Task 6. But the controller + character code should compile.

- [ ] **Step 3: Commit**

```bash
git add LilAgents/LilAgentsController.swift
git commit -m "feat: refactor controller to bootstrap characters from CharacterConfig array"
```

---

### Task 6: Refactor menu to dynamic N-character structure with Security submenu

**Files:**
- Modify: `LilAgents/LilAgentsApp.swift` (entire `setupMenuBar` and action methods)

- [ ] **Step 1: Replace `setupMenuBar()` and character toggle methods**

Replace the entire `setupMenuBar()` method and remove `toggleChar1`/`toggleChar2`. Add dynamic menu building:

```swift
func setupMenuBar() {
    statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.squareLength)
    if let button = statusItem?.button {
        button.image = NSImage(named: "MenuBarIcon") ?? NSImage(systemSymbolName: "figure.walk", accessibilityDescription: "lil agents")
    }

    let menu = NSMenu()
    menu.delegate = self

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
            let statusItem = NSMenuItem(title: statusText, action: nil, keyEquivalent: "")
            statusItem.isEnabled = false
            charMenu.addItem(statusItem)

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
```

- [ ] **Step 2: Replace toggle and provider switch actions**

Remove `toggleChar1`, `toggleChar2`, and `switchProvider`. Add these:

```swift
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
```

- [ ] **Step 3: Update `switchTheme` to iterate all characters**

The existing `switchTheme` method (lines 113-143) already iterates `controller?.characters.forEach`, so it works for N characters. No change needed.

- [ ] **Step 4: Verify it compiles**

Run build command. Fix any compilation errors.

- [ ] **Step 5: Commit**

```bash
git add LilAgents/LilAgentsApp.swift
git commit -m "feat: dynamic N-character menu with per-character provider and Security submenu"
```

---

### Task 7: Migration logic for existing users

**Files:**
- Modify: `LilAgents/LilAgentsApp.swift` (in `applicationDidFinishLaunching`)

- [ ] **Step 1: Add migration in `applicationDidFinishLaunching`**

Add migration logic before `controller?.start()`:

```swift
func applicationDidFinishLaunching(_ notification: Notification) {
    NSApp.setActivationPolicy(.accessory)

    // Migrate from V1 if needed
    if !UserDefaults.standard.bool(forKey: "didMigrateV2") {
        let legacyProvider = AgentProvider.current // reads old global "selectedProvider"
        AgentProvider.setProvider(legacyProvider, forCharacter: "bruce")
        AgentProvider.setProvider(legacyProvider, forCharacter: "jazz")
        AgentProvider.setProvider(.claude, forCharacter: "hilda")
        AutomationProfile.current = .safe
        UserDefaults.standard.set(true, forKey: "didMigrateV2")

        // Show one-time notice after a delay so the app is visible
        DispatchQueue.main.asyncAfter(deadline: .now() + 3.0) {
            let alert = NSAlert()
            alert.messageText = "Security Defaults Updated"
            alert.informativeText = "Agents now start in Safe mode by default. You can change this under Security in the menu bar."
            alert.alertStyle = .informational
            alert.addButton(withTitle: "OK")
            alert.runModal()
        }
    }

    controller = LilAgentsController()
    controller?.start()
    setupMenuBar()
}
```

- [ ] **Step 2: Verify it compiles**

Run build command.

- [ ] **Step 3: Commit**

```bash
git add LilAgents/LilAgentsApp.swift
git commit -m "feat: add V1 to V2 migration for per-character providers and safe automation default"
```

---

### Task 8: Clean up legacy global provider usage

**Files:**
- Modify: `LilAgents/AgentSession.swift` (remove or deprecate `AgentProvider.current`)

- [ ] **Step 1: Remove `AgentProvider.current` static property**

The old global `current` property (lines 8-18 of AgentSession.swift) is no longer the primary mechanism. Keep it for migration read but mark it as legacy:

```swift
/// Legacy: used only for migration from V1. New code should use per-character provider.
static var current: AgentProvider {
    get {
        let raw = UserDefaults.standard.string(forKey: defaultsKey) ?? "claude"
        return AgentProvider(rawValue: raw) ?? .claude
    }
    set {
        UserDefaults.standard.set(newValue.rawValue, forKey: defaultsKey)
    }
}
```

- [ ] **Step 2: Verify full build succeeds clean**

Run build command. Ensure zero errors.

- [ ] **Step 3: Commit**

```bash
git add LilAgents/AgentSession.swift
git commit -m "chore: mark global AgentProvider.current as legacy, used only for migration"
```

---

### Task 9: End-to-end verification

- [ ] **Step 1: Build and run the app**

```bash
# Build
xcodebuild build -project LilAgents.xcodeproj -scheme LilAgents -quiet

# Or if workspace-based:
# xcodebuild build -workspace LilAgents.xcworkspace -scheme LilAgents -quiet
```

- [ ] **Step 2: Manual verification checklist**

Verify the following by running the app:

1. Bruce and Jazz appear and walk as before (Hilda won't appear without video asset)
2. Menu shows Bruce, Jazz, Hilda submenus with provider selection
3. Hilda submenu shows status indicating asset is missing
4. Security submenu shows Safe/Balanced/Unattended with Safe checked
5. Switching a character's provider clears its popover and session
6. Switching to Unattended shows warning alert
7. Clicking a character opens popover with correct provider
8. Sounds toggle still works
9. Theme switching still works
10. Display switching still works

- [ ] **Step 3: Final commit if any fixes were needed**

```bash
git add -A
git commit -m "fix: address issues found during end-to-end verification"
```

---

## Notes for implementer

1. **Hilda's video asset (`walk-hilda-01.mov`) is NOT included.** The app will gracefully skip Hilda if the asset is missing. When the asset is created, add it to the Xcode project's bundle resources and tune `yOffset`/`flipXOffset` in `CharacterConfig.hilda`.

2. **Build system:** Check if the project uses `.xcodeproj`, `.xcworkspace`, or SPM. Adjust build commands accordingly. The project has a Sparkle dependency which may require a workspace or SPM setup.

3. **`AgentProvider` must be `Equatable`** for the menu state checks. It already conforms via `RawRepresentable` (String raw value).

4. **The `representedObject` pattern** uses `[String: Any]` dictionary because `NSMenuItem.representedObject` is `Any?`. This is standard AppKit pattern for dynamic menus.
