# Lil Agents: Hilda + Security + Per-Character Agent Binding

**Date:** 2026-03-26
**Status:** Approved (V1.1 — incorporates V2 review insights)
**Approach:** Structured refactor (Option B)

## Summary

Three changes to the lil-agents macOS dock companion app:

1. **Security**: Three-level automation profile (safe / balanced / unattended) replacing the current full-auto-only behavior
2. **Hilda**: New West Highland White Terrier character with light dog personality
3. **Per-character agent binding**: Each character independently selects its AI backend

---

## 1. CharacterConfig + RuntimeState

Extract hardcoded character definitions from `LilAgentsController.start()` into declarative config. Separate immutable config from mutable runtime state.

```swift
struct WalkTiming {
    let accelStart: Double
    let fullSpeedStart: Double
    let decelStart: Double
    let walkStop: Double
    let videoDuration: Double   // walk cycle length in seconds (default 10.0)
}

struct CharacterConfig {
    let id: String              // "bruce", "jazz", "hilda"
    let displayName: String
    let videoName: String       // bundle .mov filename without extension
    let characterColor: NSColor
    let yOffset: CGFloat
    let flipXOffset: CGFloat
    let startPosition: CGFloat  // maps to initial positionProgress (0.0~1.0)
    let initialPauseRange: ClosedRange<Double>
    let walkTiming: WalkTiming
    let walkAmountRange: ClosedRange<CGFloat>
    let defaultProvider: AgentProvider
    let systemPrompt: String?   // optional personality injection
    let isEnabledByDefault: Bool
}
```

Runtime state is held separately per character (not in config):

```swift
struct CharacterRuntimeState {
    var isVisible: Bool
    var selectedProvider: AgentProvider
    var sessionState: SessionState
    var sessionGeneration: UUID    // see Section 4
}
```

### Default configs

- **Bruce**: `walk-bruce-01`, green `(0.4, 0.72, 0.55)`, yOffset -3, flipXOffset 0, position 0.3, initialPause 0.5–2.0s, timing 3.0/3.75/8.0/8.5 (videoDuration 10.0), range 0.4–0.65, defaultProvider .claude, no system prompt
- **Jazz**: `walk-jazz-01`, orange `(1.0, 0.4, 0.0)`, yOffset -7, flipXOffset -9, position 0.7, initialPause 8.0–14.0s, timing 3.9/4.5/8.0/8.75 (videoDuration 10.0), range 0.35–0.6, defaultProvider .claude, no system prompt
- **Hilda**: `walk-hilda-01`, warm white `(0.9, 0.88, 0.85)`, yOffset TBD (depends on asset), flipXOffset TBD, position 0.5, initialPause 4.0–8.0s, timing 2.5/3.2/7.5/8.0 (videoDuration 10.0), range 0.3–0.5, defaultProvider .claude, system prompt for dog personality

Note: Bruce and Jazz values preserved exactly from existing code. Hilda's yOffset/flipXOffset depend on walk video asset and must be tuned after creation.

`LilAgentsController.start()` becomes: iterate over configs, create `WalkerCharacter` for each (skipping characters whose video asset is missing).

---

## 2. Automation Profile (Security)

### Three-level model

```swift
enum AutomationProfile: String, CaseIterable {
    case safe        // default — no dangerous flags; provider handles confirmations
    case balanced    // reduced friction; e.g. Codex uses --auto-edit
    case unattended  // maximum autonomy; passes all auto-approve flags
}
```

Stored in UserDefaults key `automationProfile`, default `.safe`. Global, not per-character.

### Why three levels instead of two

A binary restricted/fullAuto model doesn't map well across providers. Codex has `--auto-edit` (a middle ground), and future providers may have similar intermediate modes. Three levels let each provider map to whatever they actually support.

### Provider mapping

| Session | safe | balanced | unattended |
|---------|------|----------|------------|
| ClaudeSession | no extra flags | no extra flags | `--dangerously-skip-permissions` |
| CodexSession | no `--full-auto` (may require interactive — see caveat) | `--auto-edit` if available, else same as safe | `--full-auto` |
| CopilotSession | no `--allow-all` | no `--allow-all` | `--allow-all` |

Each session class handles its own mapping internally. Controller code never touches CLI flags.

**Codex caveat:** Codex without `--full-auto` may prompt for interactive confirmation, which the app can't handle (no stdin pipe). If Codex in safe mode hangs, fall back to balanced behavior for Codex only, with a note in the menu status.

### Breaking change

The current app runs all agents in full-auto mode. After upgrade, default becomes `safe`. First launch after upgrade shows a one-time notice:

> "Security defaults have changed. Agents now start in Safe mode. You can change this under Security in the menu."

Tracked via `didShowAutomationMigrationNotice` bool in UserDefaults.

### Menu

```
Security ▸
  Safe ✓
  Balanced
  Unattended
```

Switching to Unattended shows a warning alert before applying.

---

## 3. Per-Character Agent Binding

Each character stores its own `AgentProvider` in UserDefaults with key `agent_{id}`.

Menu structure changes from flat to hierarchical:

```
Bruce ▸
  Show/Hide
  ─────────
  Status: Ready
  Provider: Claude ✓
  Provider: Codex
  Provider: Copilot
Jazz ▸
  Show/Hide
  ─────────
  Status: Ready
  Provider: Claude
  Provider: Codex ✓
  Provider: Copilot
Hilda ▸
  Show/Hide
  ─────────
  Status: Asset Missing
  Provider: Claude
  Provider: Codex
  Provider: Copilot
─────────
Security ▸
🔊 Sounds
🎨 Theme ▸
🖥 Display ▸
```

Status line reflects: Ready / Starting / Streaming / Stopping / Failed / Provider Unavailable / Asset Missing.

---

## 4. Session Lifecycle

### State machine

```swift
enum SessionState: Equatable {
    case idle
    case starting
    case ready
    case streaming
    case stopping
    case failed(String)
}
```

### Generation guard

Each session restart increments `sessionGeneration` (a UUID). All async callbacks carry the generation they belong to. UI updates are silently discarded if the callback's generation doesn't match the current one.

This prevents: old subprocess output corrupting new session state, rapid provider switching causing duplicate sessions, late callbacks updating wrong UI.

### Provider switch flow

1. Persist new provider to UserDefaults
2. Mark state as `.stopping`
3. Terminate old session
4. Increment `sessionGeneration`
5. Create new session with new provider + current automation profile
6. Mark state as `.starting`
7. On success → `.ready`; on failure → `.failed(message)`

Same flow applies when global automation profile changes (all active sessions restart).

---

## 5. Hilda Character

**Identity:** West Highland White Terrier named Hilda.

**Video:** `walk-hilda-01.mov` — pixel art style matching Bruce and Jazz. Same 1080×1920 format, looping walk cycle. Must be created/sourced separately.

**Asset gating:** If `walk-hilda-01.mov` is missing from the bundle:
- Hilda still appears in config and menu
- Menu shows status "Asset Missing"
- No walker window or session is created
- No crash or hidden failure

**Walk behavior:** Shorter stride, faster cadence. Timing: 2.5/3.2/7.5/8.0. Walk range 0.3–0.5.

**Color:** Warm white `(0.9, 0.88, 0.85)` for popover accent theming.

**Personality (system prompt):**
```
You are Hilda, a friendly West Highland White Terrier. You are helpful,
professional, and knowledgeable. Occasionally use dog-related expressions
naturally (like "let me dig into that" or "I'll fetch that for you"),
but keep it subtle and never at the expense of clarity.
```

**Prompt injection:** Claude uses `--system-prompt` CLI flag. Codex/Copilot prepend the prompt to the first user message. Each session class handles this internally.

---

## 6. Migration

On first launch after upgrade (detected via absence of `didMigrateV2` key):

1. Read legacy global provider from UserDefaults
2. Set `agent_bruce` and `agent_jazz` to legacy provider value
3. Set `agent_hilda` to `.claude` (default)
4. Set `automationProfile` to `.safe`
5. Set `didMigrateV2 = true`
6. Show one-time upgrade notice about security default change

---

## 7. Files Changed

| File | Change |
|------|--------|
| **NEW** `CharacterConfig.swift` | CharacterConfig, WalkTiming, built-in character definitions |
| **NEW** `CharacterRuntimeState.swift` | CharacterRuntimeState, SessionState enum, AutomationProfile enum with UserDefaults helpers |
| `WalkerCharacter.swift` | Init takes CharacterConfig; holds runtime state; session creation uses per-character provider; asset existence check; onboarding text updated to include Hilda |
| `AgentSession.swift` | `AgentProvider.createSession()` gains `systemPrompt: String?` and `automationProfile: AutomationProfile` parameters |
| `ClaudeSession.swift` | Init accepts systemPrompt + automationProfile; conditionally includes `--dangerously-skip-permissions`; uses `--system-prompt` flag for personality |
| `CodexSession.swift` | Init accepts systemPrompt + automationProfile; maps profile to `--full-auto` / `--auto-edit` / nothing; prepends system prompt to message |
| `CopilotSession.swift` | Init accepts systemPrompt + automationProfile; conditionally includes `--allow-all`; prepends system prompt to message |
| `LilAgentsController.swift` | Dynamic character bootstrap from config array; session restart orchestration with generation guard; `wireSession()` uses per-character provider name |
| `LilAgentsApp.swift` | Dynamic N-character menu via `NSMenuItem.representedObject`; per-character provider submenus with status line; Security submenu; remove hardcoded toggleChar1/toggleChar2 |
| `ShellEnvironment.swift` | No change |

---

## 8. Out of Scope

- App sandbox enablement (would break CLI subprocess launching)
- Environment variable filtering
- Custom character editor / user-importable characters
- Video asset creation (Hilda's walk video must be provided separately)
- Per-character automation profiles (global only for this iteration)
- ProviderCapabilities abstraction (3 providers, handle differences directly in session classes)
- AgentProviderAdapter protocol (unnecessary indirection for current scale)
- Conversation persistence across provider switches
