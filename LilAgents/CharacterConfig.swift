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
        yOffset: -5,
        flipXOffset: 0,
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
