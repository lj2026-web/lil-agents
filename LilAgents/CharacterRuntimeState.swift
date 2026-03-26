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
