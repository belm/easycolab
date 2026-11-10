import SwiftUI
import UIKit
import AuthenticationServices
import AVKit
import Photos

// MARK: - iOS / iPadOS Studio ViewModel

enum AppTab: Int, Hashable {
    case create = 0
    case cloud = 1
    case gallery = 2
    case settings = 3
}

@MainActor
final class IOSStudioViewModel: ObservableObject {
    @Published var selectedTab: AppTab = .create

    // Privacy Mask & Server URL
    @Published var maskServerURL: Bool = UserDefaults.standard.bool(forKey: "maskServerURL") {
        didSet { UserDefaults.standard.set(maskServerURL, forKey: "maskServerURL") }
    }
    @Published var colabServerURL: String = UserDefaults.standard.string(forKey: "colabServerURL") ?? "" {
        didSet { UserDefaults.standard.set(colabServerURL, forKey: "colabServerURL") }
    }
    @Published var hfToken: String = UserDefaults.standard.string(forKey: "hfToken") ?? "" {
        didSet { UserDefaults.standard.set(hfToken, forKey: "hfToken") }
    }
    @Published var autoSaveToPhotos: Bool = {
        if UserDefaults.standard.object(forKey: "autoSaveToPhotos") == nil { return true }
        return UserDefaults.standard.bool(forKey: "autoSaveToPhotos")
    }() {
        didSet { UserDefaults.standard.set(autoSaveToPhotos, forKey: "autoSaveToPhotos") }
    }

    // In-app Safari Browser Sheet
    @Published var activeSafariURL: URL? = nil
    @Published var showAIConsentAlert: Bool = false
    @Published var hasAcceptedCloudAIConsent: Bool = true
    var pendingAfterConsent: (() -> Void)? = nil
    @Published var showOnboardingSheet: Bool = !UserDefaults.standard.bool(forKey: "hasSeenIOSOnboardingV1") {
        didSet {
            if !showOnboardingSheet {
                UserDefaults.standard.set(true, forKey: "hasSeenIOSOnboardingV1")
            }
        }
    }

    // Native Google OAuth & Cloud Billing State
    @Published var cliLoggedIn: Bool = false
    @Published var isAuthenticatingGoogle: Bool = false
    @Published var accountEmail: String = ""
    @Published var showOAuthCodeSheet: Bool = false
    @Published var oauthCodeText: String = ""
    @Published var officialCUBalance: Double? = nil
    @Published var officialBurnRate: Double? = nil
    @Published var activeVMCount: Int = 0
    @Published var hasCustomOAuth: Bool = false
    @Published var wakeGPUChoice: String = {
        let saved = UserDefaults.standard.string(forKey: "wakeGPUChoiceV2") ?? "G4"
        return ["G4", "H100", "A100", "L4", "T4"].contains(saved) ? saved : "G4"
    }() {
        didSet { UserDefaults.standard.set(wakeGPUChoice, forKey: "wakeGPUChoiceV2") }
    }
    @Published var isWakingColab: Bool = false
    @Published var showDisconnectConfirm: Bool = false

    // Remote GPU & Telemetry State
    @Published var isConnected: Bool = false
    @Published var gpuName: String = L("未连接 Colab 服务端", "Colab Server Disconnected") {
        didSet { let c = stripEmoji(gpuName); if c != gpuName { gpuName = c } }
    }
    @Published var vramFreeGB: Double = 0.0
    @Published var vramTotalGB: Double = 0.0
    @Published var vramUsedGB: Double = 0.0
    @Published var ramTotalGB: Double = 0.0
    @Published var ramUsedGB: Double = 0.0
    @Published var ramFreeGB: Double = 0.0
    @Published var diskTotalGB: Double = 0.0
    @Published var diskUsedGB: Double = 0.0
    @Published var diskFreeGB: Double = 0.0
    @Published var driveTotalGB: Double = 0.0
    @Published var driveUsedGB: Double = 0.0
    @Published var driveFreeGB: Double = 0.0
    @Published var vramHistoryPct: [Double] = []
    @Published var ramHistoryPct: [Double] = []
    @Published var diskHistoryPct: [Double] = []
    @Published var combinedTelemetryChartMode: Bool = true

    // Active Model & VRAM Residency
    @Published var selectedModelId: String = "minimax_h3"
    @Published var customModels: [OpenModelSpec] = []
    @Published var showAddCustomModelSheet: Bool = false
    @Published var customRepoIdInput: String = ""
    @Published var customIncludePatternInput: String = ""
    @Published var customDisplayNameInput: String = ""
    @Published var customModalityHint: String = "auto"
    @Published var isRegisteringCustomModel: Bool = false
    @Published var customModelBannerMessage: String = ""
    @Published var trendingHFModels: [HFTrendingModelItem] = []
    @Published var trendingHFCategory: String = "all"
    @Published var isLoadingTrendingHF: Bool = false
    @Published var activeHFModelDetail: HFModelDetailInfo? = nil
    @Published var isLoadingHFModelDetail: Bool = false
    @Published var showHFModelDetailSheet: Bool = false
    @Published var loadedModelId: String? = nil
    @Published var loadedModelIds: [String] = []
    @Published var loadedModelsDetail: [LoadedModelSummary] = []
    @Published var modelLoaded: Bool = false
    @Published var isUnloadingModel: Bool = false
    @Published var currentModelName: String = L("未加载", "Not Loaded")

    @Published var uptimeSeconds: Int = 0
    @Published var cuBurnRatePerHour: Double = 0.0
    @Published var sessionCUUsed: Double = 0.0
    @Published var idleTimeoutMinutes: Int = {
        if UserDefaults.standard.object(forKey: "idleTimeoutMinutes") == nil { return 30 }
        let saved = UserDefaults.standard.integer(forKey: "idleTimeoutMinutes")
        return [0, 15, 30, 60].contains(saved) ? saved : 30
    }() {
        didSet { UserDefaults.standard.set(idleTimeoutMinutes, forKey: "idleTimeoutMinutes") }
    }
    @Published var idleRemainingSeconds: Int = 1800
    @Published var drivePersisted: Bool = false
    @Published var liveConsoleLines: [String] = [
        L("欢迎使用 EasyColab iOS 多模态云端工作台", "Welcome to EasyColab iOS Multimodal Cloud Studio"),
        L("纯 Swift 原生直连 Google Colab G4 (96GB)，支持一键免网页唤醒、生视频/生图自动存相册与闲置省额度保护。", "Pure-Swift native Colab G4 (96GB) client — 1-tap headless wake, auto-save to Photos & idle CU protection.")
    ] {
        didSet { let c = liveConsoleLines.map(stripEmoji); if c != liveConsoleLines { liveConsoleLines = c } }
    }

    // Model Weights State
    @Published var modelFiles: [ModelFileItem] = OPEN_MODEL_CATALOG[0].defaultFiles
    @Published var downloadedCount: Int = 0
    @Published var totalFileCount: Int = OPEN_MODEL_CATALOG[0].defaultFiles.count
    @Published var allDownloaded: Bool = false
    @Published var totalDiskSizeGB: Double = 0.0
    @Published var isDownloadingWeights: Bool = false
    @Published var isLoadingModel: Bool = false
    @Published var modelTaskProgress: Double = 0.0
    @Published var selectedOffload: String = "disk"

    // ComfyUI Cloud State
    @Published var comfyRunning: Bool = false
    @Published var comfyStarting: Bool = false
    @Published var comfySyncingDrive: Bool = false
    @Published var comfyDownloadingWeight: Bool = false
    @Published var comfyInstallingPackId: String = ""
    @Published var comfyPresetPacks: [ComfyPresetPackItem] = DEFAULT_COMFY_PRESET_PACKS
    @Published var comfyProgress: Double = 0.0
    @Published var comfyStatusMessage: String = L("尚未启动云端 ComfyUI 工作台", "Cloud ComfyUI Studio Not Started")
    @Published var comfyPublicURL: String = ""
    @Published var comfyQueueRunning: Int = 0
    @Published var comfyQueuePending: Int = 0
    @Published var comfyPersistenceLabel: String = L("Google Drive 自动软链持久化", "Google Drive Auto-Symlink Persistence")
    @Published var comfyCustomNodesCount: Int = 0
    @Published var comfyModelsCount: Int = 0
    @Published var comfyWorkflowsCount: Int = 0
    @Published var comfyRecentOutputs: [ComfyOutputMediaItem] = []
    @Published var comfyUnloadOthersOnStart: Bool = false
    @Published var comfyWeightSourceInput: String = ""
    @Published var comfyWeightFilenameInput: String = ""
    @Published var comfyWeightSubfolder: String = "diffusion_models"
    @Published var comfyPullingOutputRelPath: String? = nil

    // Generation Parameters
    @Published var taskModeId: String = "t2va"
    @Published var visualPrompt: String = PRESET_TEMPLATES[0].visual
    @Published var negativePrompt: String = ""
    @Published var soundscapePrompt: String = PRESET_TEMPLATES[0].soundscape
    @Published var musicPrompt: String = PRESET_TEMPLATES[0].music
    @Published var firstFrameImage: UIImage? = nil
    @Published var lastFrameImage: UIImage? = nil
    @Published var selectedVideoResolution: ResolutionOption = VIDEO_RESOLUTIONS[0]
    @Published var selectedImageResolution: ResolutionOption = IMAGE_RESOLUTIONS[0]
    @Published var numFrames: Double = 124
    @Published var inferenceSteps: Double = 35
    @Published var fps: Double = 24
    @Published var seed: Int = 42
    @Published var randomizeSeed: Bool = true
    @Published var batchCount: Int = 1
    @Published var denoisingStrength: Double = 0.70

    // Qwen3.8 LLM/VLM & API Gateway
    @Published var contextLengthK: Int = {
        let saved = UserDefaults.standard.integer(forKey: "qwenContextLengthK")
        return (4...256).contains(saved) ? saved : 32
    }() {
        didSet { UserDefaults.standard.set(contextLengthK.clamped(to: 4...256), forKey: "qwenContextLengthK") }
    }
    @Published var loadedContextLengthTokens: Int = 0
    @Published var enableThinking: Bool = true {
        didSet {
            if enableThinking {
                temperature = 1.0; topP = 0.95; presencePenalty = 0.0
            } else {
                temperature = 0.7; topP = 0.80; presencePenalty = 1.5
            }
        }
    }
    @Published var reasoningEffort: String = "medium"
    @Published var maxNewTokens: Double = 8192
    @Published var temperature: Double = 1.0
    @Published var topP: Double = 0.95
    @Published var presencePenalty: Double = 0.0
    @Published var chatHistory: [ChatTurnItem] = []

    @Published var apiKeyEnabled: Bool = {
        if UserDefaults.standard.object(forKey: "apiKeyEnabled") == nil { return true }
        return UserDefaults.standard.bool(forKey: "apiKeyEnabled")
    }() {
        didSet {
            UserDefaults.standard.set(apiKeyEnabled, forKey: "apiKeyEnabled")
            Task { await syncApiKeyToColab() }
        }
    }
    @Published var apiAccessKey: String = {
        if let saved = UserDefaults.standard.string(forKey: "apiAccessKey"), !saved.isEmpty { return saved }
        let gen = "sk-colab-" + UUID().uuidString.replacingOccurrences(of: "-", with: "").prefix(20).lowercased()
        UserDefaults.standard.set(gen, forKey: "apiAccessKey")
        return gen
    }() {
        didSet { UserDefaults.standard.set(apiAccessKey, forKey: "apiAccessKey") }
    }
    @Published var apiRequestCount: Int = 0

    // Active Job & Media Preview
    @Published var isGenerating: Bool = false
    @Published var progressValue: Double = 0.0
    @Published var currentJobElapsed: Double = 0.0
    @Published var lastCompletedElapsed: Double? = nil
    @Published var statusMessage: String = L("就绪：可在「云算力」页绑定账号一键唤醒 G4，或粘贴已有 gradio.live 地址连接。", "Ready: Bind Google account in Cloud tab for 1-tap G4 wake, or paste an active gradio.live URL.") {
        didSet { let c = stripEmoji(statusMessage); if c != statusMessage { statusMessage = c } }
    }
    @Published var toastBanner: String? = nil

    @Published var currentMediaURL: URL? = nil
    @Published var currentPreviewImage: UIImage? = nil
    @Published var player: AVPlayer? = nil
    @Published var localMediaItems: [LocalMediaItem] = []
    @Published var mediaElapsedMap: [String: Double] = (UserDefaults.standard.dictionary(forKey: "mediaElapsedSecondsMap") as? [String: Double]) ?? [:] {
        didSet { UserDefaults.standard.set(mediaElapsedMap, forKey: "mediaElapsedSecondsMap") }
    }

    // Background / Lock-screen Resilience State
    var pendingJobId: String? = UserDefaults.standard.string(forKey: "pendingIOSJobId") {
        didSet { UserDefaults.standard.set(pendingJobId, forKey: "pendingIOSJobId") }
    }
    var pendingAssistantIndex: Int? = nil
    var activeGenerationToken = UUID()
    var bgTaskId: UIBackgroundTaskIdentifier = .invalid
    var heartbeatTask: Task<Void, Never>? = nil
    var generationTimerTask: Task<Void, Never>? = nil
    var generationStartedAt: Date? = nil
    var consecutiveStatusFailures: Int = 0
    var lastTelemetrySampleDate: Date = .distantPast
    var remoteContextSynced = false
    var remoteIdleSynced = false
    var remoteApiKeySynced = false
    var languageObserver: NSObjectProtocol? = nil

    let localSaveDir: URL = {
        let docs = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first!
        let dir = docs.appendingPathComponent("EasyColab", isDirectory: true)
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        return dir
    }()

    var normalizedBaseURL: String {
        var raw = colabServerURL.trimmingCharacters(in: .whitespacesAndNewlines)
        while raw.hasSuffix("/") { raw.removeLast() }
        return raw
    }

    var allAvailableModels: [OpenModelSpec] {
        OPEN_MODEL_CATALOG + customModels
    }

    var activeModelSpec: OpenModelSpec {
        allAvailableModels.first(where: { $0.id == selectedModelId }) ?? OPEN_MODEL_CATALOG[0]
    }

    var activeModeItem: TaskModeItem {
        activeModelSpec.modes.first(where: { $0.id == taskModeId }) ?? activeModelSpec.modes[0]
    }

    var isSelectedModelLoadedInVRAM: Bool {
        loadedModelIds.contains(selectedModelId) || (modelLoaded && loadedModelId == selectedModelId)
    }

    var contextLengthTokens: Int {
        contextLengthK.clamped(to: 4...256) * 1024
    }

    var displayAccountLabel: String {
        guard cliLoggedIn else { return L("未绑定", "Unbound") }
        let raw = accountEmail.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !raw.isEmpty else { return L("已授权", "Authorized") }
        if maskServerURL, let atIdx = raw.firstIndex(of: "@") {
            return "\(raw[..<atIdx].prefix(2))•••\(raw[atIdx...])"
        }
        return raw
    }

    var displayRemainingCU: Double {
        officialCUBalance ?? 0.0
    }

    var displayBurnRate: Double {
        if let rate = officialBurnRate, rate > 0 || !isConnected { return rate }
        return cuBurnRatePerHour
    }

    var formattedUptime: String {
        let h = uptimeSeconds / 3600
        let m = (uptimeSeconds % 3600) / 60
        let s = uptimeSeconds % 60
        return String(format: "%02d:%02d:%02d", h, m, s)
    }

    var formattedIdleRemaining: String {
        if idleTimeoutMinutes <= 0 || idleRemainingSeconds < 0 {
            return L("已关闭自动休眠", "Auto-sleep off")
        }
        let m = idleRemainingSeconds / 60
        let s = idleRemainingSeconds % 60
        return L("\(m)分\(String(format: "%02d", s))秒后释放", "Auto-stop in \(m)m \(String(format: "%02d", s))s")
    }

    func maskedURLDisplay(_ rawURL: String) -> String {
        let trimmed = rawURL.trimmingCharacters(in: .whitespacesAndNewlines)
        guard maskServerURL, !trimmed.isEmpty else { return trimmed }
        if let u = URL(string: trimmed), let scheme = u.scheme, let host = u.host {
            let parts = host.split(separator: ".")
            let suffix = parts.count >= 2 ? parts.suffix(2).joined(separator: ".") : host
            return "\(scheme)://••••••••.\(suffix)"
        }
        return "https://••••••••"
    }

    init() {
        loadSavedCustomModels()
        refreshLocalMedia()
        startBackgroundTelemetryLoop()
        languageObserver = NotificationCenter.default.addObserver(
            forName: .easyColabLanguageDidChange,
            object: nil,
            queue: .main
        ) { [weak self] _ in
            Task { @MainActor [weak self] in
                self?.objectWillChange.send()
            }
        }
        Task {
            hasCustomOAuth = await ColabNativeBridge.shared.hasCustomOAuthConfig()
            await refreshOfficialColabAccountUsage()
            if let savedJob = pendingJobId, !savedJob.isEmpty, !normalizedBaseURL.isEmpty {
                await resumePendingJobIfNeeded()
            }
        }
    }

    deinit {
        if let languageObserver {
            NotificationCenter.default.removeObserver(languageObserver)
        }
    }

    func showToast(_ message: String) {
        toastBanner = message
        Task {
            try? await Task.sleep(nanoseconds: 2_800_000_000)
            if toastBanner == message {
                toastBanner = nil
            }
        }
    }

    // MARK: - iOS Background Task & Foreground Resume

    func beginIOSBackgroundExecution(name: String) {
        endIOSBackgroundExecution()
        bgTaskId = UIApplication.shared.beginBackgroundTask(withName: name) { [weak self] in
            Task { @MainActor in
                self?.endIOSBackgroundExecution()
            }
        }
    }

    func endIOSBackgroundExecution() {
        if bgTaskId != .invalid {
            UIApplication.shared.endBackgroundTask(bgTaskId)
            bgTaskId = .invalid
        }
    }

    func handleSceneBecameActive() {
        startBackgroundTelemetryLoop()
        // Auto-fill Google OAuth code if user just copied it from Safari!
        if showOAuthCodeSheet && oauthCodeText.isEmpty,
           let clip = UIPasteboard.general.string?.trimmingCharacters(in: .whitespacesAndNewlines),
           clip.hasPrefix("4/") && clip.count > 20 && !clip.contains(" ") {
            oauthCodeText = clip
        }
        Task {
            if !normalizedBaseURL.isEmpty {
                await checkColabStatus(silent: true)
            }
            if cliLoggedIn {
                await refreshOfficialColabAccountUsage()
            }
            await resumePendingJobIfNeeded()
        }
    }

    func resumePendingJobIfNeeded() async {
        guard let jobId = pendingJobId, !jobId.isEmpty, !normalizedBaseURL.isEmpty else { return }
        guard !isGenerating else { return }
        let token = UUID()
        activeGenerationToken = token
        isGenerating = true
        startLiveGenerationTimer()
        await pollColabJob(baseURL: normalizedBaseURL, jobId: jobId, assistantRowIndex: pendingAssistantIndex, token: token)
    }

    // MARK: - Bundled Resources Lookup & App Store AI Data Consent

    func bundledResourceURL(_ filename: String) -> URL? {
        if let res = Bundle.main.resourceURL {
            let candidate = res.appendingPathComponent(filename)
            if FileManager.default.fileExists(atPath: candidate.path) {
                return candidate
            }
        }
        let bundleCandidate = Bundle.main.bundleURL.appendingPathComponent(filename)
        if FileManager.default.fileExists(atPath: bundleCandidate.path) {
            return bundleCandidate
        }
        return nil
    }

    func bundledServerEngineData() -> Data? {
        for name in ["easycolab_engine.txt", "app.py"] {
            if let url = bundledResourceURL(name), let data = try? Data(contentsOf: url), !data.isEmpty {
                return data
            }
        }
        return nil
    }

    func exportableNotebookURL() -> URL? {
        if let direct = bundledResourceURL("EasyColab_Server.ipynb") {
            return direct
        }
        if let jsonRes = bundledResourceURL("easycolab_notebook.json") {
            let dst = FileManager.default.temporaryDirectory.appendingPathComponent("EasyColab_Server.ipynb")
            try? FileManager.default.removeItem(at: dst)
            if (try? FileManager.default.copyItem(at: jsonRes, to: dst)) != nil {
                return dst
            }
        }
        return nil
    }

    func confirmCloudAIConsent() {
        hasAcceptedCloudAIConsent = true
        let action = pendingAfterConsent
        pendingAfterConsent = nil
        action?()
    }

    func reportAndPurgeMedia(_ url: URL) {
        if let item = localMediaItems.first(where: { $0.url == url }) {
            deleteLocalMedia(item)
        } else {
            if currentMediaURL == url {
                player?.pause()
                player = nil
                currentPreviewImage = nil
                currentMediaURL = nil
            }
            try? FileManager.default.removeItem(at: url)
            refreshLocalMedia()
        }
        UINotificationFeedbackGenerator().notificationOccurred(.warning)
        showToast(L("已标记并彻底清除该异常生成结果", "Flagged and permanently removed AI output"))
    }

    // MARK: - Native OAuth & Headless Wake

    func refreshOfficialColabAccountUsage() async {
        let res = await ColabNativeBridge.shared.fetchAuthStatus()
        cliLoggedIn = res.loggedIn
        if !res.email.isEmpty {
            accountEmail = res.email
        } else if !res.loggedIn {
            accountEmail = ""
        }
        if let bal = res.paidBalance { officialCUBalance = bal }
        if let rate = res.burnRateHourly { officialBurnRate = rate }
        activeVMCount = res.activeAssignments
        if res.activeAssignments == 0 && !isConnected && (!loadedModelsDetail.isEmpty || vramTotalGB > 0) {
            resetStaleRemoteRuntimeState(reason: L("云端实例当前未运行，已清理旧显存记录。", "No active cloud runtime detected; cleared stale VRAM state."))
        }
    }

    func startGoogleOAuthLogin() async {
        guard !isAuthenticatingGoogle else { return }
        activeSafariURL = nil
        if showOAuthCodeSheet {
            showOAuthCodeSheet = false
            try? await Task.sleep(nanoseconds: 280_000_000)
        }

        do {
            let sessionReq = try await ColabNativeBridge.shared.generateAuthSession(preferCustomScheme: true)
            guard let callbackScheme = sessionReq.callbackScheme else {
                // Custom Web-type OAuth client without reverse iOS scheme -> open manual fallback sheet
                oauthCodeText = ""
                showOAuthCodeSheet = true
                await UIApplication.shared.open(sessionReq.authURL)
                statusMessage = L("已在系统 Safari 打开 Google 授权页，复制授权码后返回粘贴。", "Opened Google sign-in in Safari. Copy the code and paste it back.")
                return
            }

            isAuthenticatingGoogle = true
            statusMessage = L("正在拉起系统 Google 安全登录窗口（支持直接复用手机 Safari 已登录账号）...", "Launching native Google Sign-In (shares iPhone Safari session)...")
            defer { isAuthenticatingGoogle = false }

            let callbackURL = try await GoogleWebAuthCoordinator.shared.authenticate(
                url: sessionReq.authURL,
                callbackScheme: callbackScheme
            )
            await completeOAuthExchange(rawInput: callbackURL.absoluteString, redirectURI: sessionReq.redirectURI)
        } catch {
            if let authErr = error as? ASWebAuthenticationSessionError, authErr.code == .canceledLogin {
                statusMessage = L("已取消 Google 登录；如需在电脑或独立浏览器登录，可点「手动授权码」。", "Google sign-in canceled. Tap 'Manual Code' if signing in from another browser.")
                return
            }
            statusMessage = L("系统登录窗口未完成 (\(error.localizedDescription))，可尝试「手动授权码」模式。", "Sign-in interrupted (\(error.localizedDescription)). Try 'Manual Code' mode.")
        }
    }

    func openManualOAuthSheet() {
        activeSafariURL = nil
        oauthCodeText = ""
        showOAuthCodeSheet = true
    }

    func openGoogleOAuthInExternalSafari() async {
        do {
            // Uses reverse client ID scheme so standalone Safari automatically jumps back into EasyColab on completion!
            let req = try await ColabNativeBridge.shared.generateAuthSession(preferCustomScheme: true)
            await UIApplication.shared.open(req.authURL)
            statusMessage = L("已跳往系统 Safari 独立登录，点击允许后将自动跳回 App 完成绑定。", "Opened in Safari. Tap Allow to return to EasyColab automatically.")
        } catch {
            statusMessage = error.localizedDescription
        }
    }

    func copyManualGoogleOAuthLink() async {
        do {
            let url = try await ColabNativeBridge.shared.generateAuthURL()
            UIPasteboard.general.string = url.absoluteString
            showToast(L("已复制登录链接！可在任意浏览器打开后粘贴授权码", "Copied OAuth URL! Open in any browser & paste code"))
        } catch {
            statusMessage = error.localizedDescription
        }
    }

    func handleIncomingOAuthURL(_ url: URL) async {
        guard url.scheme?.hasPrefix("com.googleusercontent.apps.") == true else { return }
        await completeOAuthExchange(rawInput: url.absoluteString, redirectURI: nil)
    }

    func submitGoogleOAuthCode() async {
        let code = oauthCodeText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !code.isEmpty else { return }
        await completeOAuthExchange(rawInput: code, redirectURI: nil)
    }

    func completeOAuthExchange(rawInput: String, redirectURI: String?) async {
        statusMessage = L("正在验证 Google 授权并同步 CU 算力余额...", "Verifying Google authorization & syncing CU balance...")
        let res = await ColabNativeBridge.shared.exchangeAuthCode(rawInput, redirectURI: redirectURI)
        if res.loggedIn {
            cliLoggedIn = true
            accountEmail = res.email
            officialCUBalance = res.paidBalance
            officialBurnRate = res.burnRateHourly
            activeVMCount = res.activeAssignments
            showOAuthCodeSheet = false
            oauthCodeText = ""
            UINotificationFeedbackGenerator().notificationOccurred(.success)
            let balStr = String(format: "%.2f", res.paidBalance ?? 0)
            statusMessage = L("账号绑定成功 (\(displayAccountLabel)) · 余额 \(balStr) CU", "Account bound (\(displayAccountLabel)) · Balance \(balStr) CU")
            showToast(L("已绑定 Google 账号 · \(balStr) CU", "Google Bound · \(balStr) CU"))
        } else {
            UINotificationFeedbackGenerator().notificationOccurred(.error)
            let errMsg = res.error ?? L("请重新获取", "try again")
            statusMessage = L("Google 授权未通过: \(errMsg)", "Google authorization failed: \(errMsg)")
            showToast(L("授权失败: \(errMsg)", "Auth failed: \(errMsg)"))
        }
    }

    func logoutGoogleAccount() async {
        await ColabNativeBridge.shared.logout()
        cliLoggedIn = false
        accountEmail = ""
        officialCUBalance = nil
        officialBurnRate = nil
        activeVMCount = 0
        colabServerURL = ""
        resetStaleRemoteRuntimeState(reason: L("已退出 Google 账号绑定。", "Signed out of Google account."))
    }

    func saveCustomOAuthConfigJSON(_ raw: String) async -> String {
        do {
            let saved = try await ColabNativeBridge.shared.saveCustomOAuthJSON(raw)
            hasCustomOAuth = saved
            return saved
                ? L("已保存自定义 Google OAuth 配置", "Saved custom Google OAuth config")
                : L("已恢复默认 OAuth 配置", "Restored default OAuth config")
        } catch {
            return error.localizedDescription
        }
    }

    func wakeColabHeadless() async {
        guard cliLoggedIn else {
            statusMessage = L("请先绑定 Google 账号后再使用免网页一键唤醒。", "Please bind your Google account before headless 1-tap wake.")
            selectedTab = .cloud
            return
        }
        if !hasAcceptedCloudAIConsent {
            pendingAfterConsent = { [weak self] in
                Task { await self?.wakeColabHeadless() }
            }
            showAIConsentAlert = true
            return
        }
        guard let appPyData = bundledServerEngineData() else {
            statusMessage = L("未找到内置云端服务组件资源文件。", "Missing bundled cloud server engine resource.")
            return
        }

        isWakingColab = true
        beginIOSBackgroundExecution(name: "EasyColabWake")
        defer {
            isWakingColab = false
            endIOSBackgroundExecution()
        }

        let gpu = wakeGPUChoice
        liveConsoleLines = [L("[原生唤醒] 正在请求分配 \(gpu) 实例并自动部署服务端...", "[Native Wake] Provisioning \(gpu) VM & deploying server engine...")]
        statusMessage = liveConsoleLines[0]

        do {
            let tunnelURL = try await ColabNativeBridge.shared.wakeAndDeploy(gpuType: gpu, appPyData: appPyData) { [weak self] line in
                Task { @MainActor [weak self] in
                    guard let self else { return }
                    let clean = stripEmoji(line)
                    guard !clean.isEmpty else { return }
                    self.liveConsoleLines.append(clean)
                    self.statusMessage = localizeServerText(clean)
                }
            }
            colabServerURL = tunnelURL
            liveConsoleLines.append(L("成功建立加密隧道: \(maskedURLDisplay(tunnelURL))", "Public tunnel active: \(maskedURLDisplay(tunnelURL))"))
            UINotificationFeedbackGenerator().notificationOccurred(.success)
            showToast(L("\(gpu) 实例已唤醒就绪！", "\(gpu) Runtime Ready!"))
            await refreshOfficialColabAccountUsage()
            await checkColabStatus()
        } catch {
            UINotificationFeedbackGenerator().notificationOccurred(.error)
            let msg = error.localizedDescription
            liveConsoleLines.append(L("唤醒失败: \(msg)", "Wake failed: \(msg)"))
            statusMessage = L("唤醒失败: \(msg)", "Wake failed: \(msg)")
            await refreshOfficialColabAccountUsage()
        }
    }

    func disconnectRemoteColab() async {
        statusMessage = L("正在释放全部云端 Colab 实例并归零计费...", "Terminating all cloud Colab VMs & stopping billing...")
        let base = normalizedBaseURL
        if !base.isEmpty, let url = URL(string: "\(base)/minimax_api/disconnect") {
            var req = URLRequest(url: url)
            req.httpMethod = "POST"
            req.timeoutInterval = 8
            _ = try? await URLSession.shared.data(for: req)
        }
        if cliLoggedIn {
            let res = await ColabNativeBridge.shared.stopAll()
            officialCUBalance = res.paidBalance ?? officialCUBalance
            officialBurnRate = res.burnRateHourly ?? 0.0
            activeVMCount = res.activeAssignments
            statusMessage = res.message ?? L("已彻底释放全部云端实例，计费归零。", "All cloud instances terminated (0 CU/h).")
            showToast(L("已释放实例 · 0.00 CU/h", "Instances Terminated · 0 CU/h"))
        } else {
            statusMessage = L("已向服务端发送释放关机指令。", "Sent shutdown command to cloud runtime.")
        }
        pendingJobId = nil
        resetStaleRemoteRuntimeState(reason: "")
        UINotificationFeedbackGenerator().notificationOccurred(.success)
    }

    // MARK: - Telemetry & Model Management

    func recordTelemetrySample() {
        let now = Date()
        guard now.timeIntervalSince(lastTelemetrySampleDate) >= 0.85 else { return }
        lastTelemetrySampleDate = now
        let maxSamples = 40

        if vramTotalGB > 0 {
            let pct = (vramUsedGB / vramTotalGB).clamped(to: 0...1)
            vramHistoryPct = vramHistoryPct.isEmpty ? Array(repeating: pct, count: 12) : Array((vramHistoryPct + [pct]).suffix(maxSamples))
        }
        if ramTotalGB > 0 {
            let pct = (ramUsedGB / ramTotalGB).clamped(to: 0...1)
            ramHistoryPct = ramHistoryPct.isEmpty ? Array(repeating: pct, count: 12) : Array((ramHistoryPct + [pct]).suffix(maxSamples))
        }
        if diskTotalGB > 0 {
            let pct = (diskUsedGB / diskTotalGB).clamped(to: 0...1)
            diskHistoryPct = diskHistoryPct.isEmpty ? Array(repeating: pct, count: 12) : Array((diskHistoryPct + [pct]).suffix(maxSamples))
        }
    }

    func applyLiveTelemetrySnapshot(_ snap: LiveTelemetrySnapshot) {
        if let g = snap.gpu_name, !g.isEmpty { gpuName = g }
        if let vf = snap.vram_free_gb { vramFreeGB = vf }
        if let vt = snap.vram_total_gb { vramTotalGB = vt }
        if let vu = snap.vram_used_gb { vramUsedGB = vu }
        if let cr = snap.cu_burn_rate_per_hour { cuBurnRatePerHour = cr }
        if let rt = snap.ram_total_gb, rt > 0 { ramTotalGB = rt }
        if let ru = snap.ram_used_gb { ramUsedGB = ru }
        if let rf = snap.ram_free_gb { ramFreeGB = rf }
        if let dt = snap.disk_total_gb, dt > 0 { diskTotalGB = dt }
        if let du = snap.disk_used_gb { diskUsedGB = du }
        if let df = snap.disk_free_gb { diskFreeGB = df }
        if let gt = snap.drive_total_gb, gt > 0 { driveTotalGB = gt }
        if let gu = snap.drive_used_gb { driveUsedGB = gu }
        if let gf = snap.drive_free_gb { driveFreeGB = gf }
        recordTelemetrySample()
    }

    func resetStaleRemoteRuntimeState(reason: String) {
        stopLiveGenerationTimer()
        isConnected = false
        modelLoaded = false
        loadedModelId = nil
        loadedModelIds = []
        loadedModelsDetail = []
        isGenerating = false
        isLoadingModel = false
        isDownloadingWeights = false
        isUnloadingModel = false
        comfyRunning = false
        comfyStarting = false
        comfyDownloadingWeight = false
        comfyInstallingPackId = ""
        comfyPublicURL = ""
        progressValue = 0.0
        modelTaskProgress = 0.0
        vramUsedGB = 0.0; vramFreeGB = 0.0; vramTotalGB = 0.0
        ramTotalGB = 0.0; ramUsedGB = 0.0; ramFreeGB = 0.0
        diskTotalGB = 0.0; diskUsedGB = 0.0; diskFreeGB = 0.0
        vramHistoryPct = []; ramHistoryPct = []; diskHistoryPct = []
        lastTelemetrySampleDate = .distantPast
        cuBurnRatePerHour = 0.0
        remoteContextSynced = false; remoteIdleSynced = false; remoteApiKeySynced = false
        gpuName = L("未连接 Colab 服务端", "Colab Server Disconnected")
        if !reason.isEmpty { statusMessage = reason }
    }

    func switchSelectedModel(_ spec: OpenModelSpec) {
        guard selectedModelId != spec.id else { return }
        UIImpactFeedbackGenerator(style: .light).impactOccurred()
        selectedModelId = spec.id
        taskModeId = spec.modes[0].id
        inferenceSteps = spec.defaultSteps
        modelFiles = spec.defaultFiles
        downloadedCount = 0
        totalFileCount = spec.defaultFiles.count
        allDownloaded = false
        totalDiskSizeGB = 0.0
        modelLoaded = loadedModelIds.contains(spec.id) || (loadedModelId == spec.id)

        if let sample = PRESET_TEMPLATES.first(where: { $0.category == spec.modality || (spec.modality == .video && $0.category == .videoAudio) }) {
            visualPrompt = sample.visual
            soundscapePrompt = sample.soundscape
            musicPrompt = sample.music
        }

        if spec.modality != .comfyUI && isConnected {
            Task { await notifyRemoteSelectModel(spec.id) }
        }
    }

    func notifyRemoteSelectModel(_ modelId: String) async {
        let base = normalizedBaseURL
        guard !base.isEmpty, let url = URL(string: "\(base)/minimax_api/select_model") else { return }
        do {
            var req = URLRequest(url: url)
            req.httpMethod = "POST"
            req.setValue("application/json", forHTTPHeaderField: "Content-Type")
            req.httpBody = try JSONSerialization.data(withJSONObject: ["model_id": modelId])
            let (data, _) = try await URLSession.shared.data(for: req)
            let decoded = try JSONDecoder().decode(ColabStatusResponse.self, from: data)
            applyStatusResponse(decoded)
        } catch {}
    }

    func applyStatusResponse(_ decoded: ColabStatusResponse) {
        isConnected = true
        gpuName = decoded.gpu_name ?? "Colab GPU"
        vramFreeGB = decoded.vram_free_gb ?? 0.0
        vramTotalGB = decoded.vram_total_gb ?? 0.0
        vramUsedGB = decoded.vram_used_gb ?? 0.0
        ramTotalGB = decoded.ram_total_gb ?? ramTotalGB
        ramUsedGB = decoded.ram_used_gb ?? ramUsedGB
        ramFreeGB = decoded.ram_free_gb ?? ramFreeGB
        diskTotalGB = decoded.disk_total_gb ?? diskTotalGB
        diskUsedGB = decoded.disk_used_gb ?? diskUsedGB
        diskFreeGB = decoded.disk_free_gb ?? diskFreeGB
        driveTotalGB = decoded.drive_total_gb ?? driveTotalGB
        driveUsedGB = decoded.drive_used_gb ?? driveUsedGB
        driveFreeGB = decoded.drive_free_gb ?? driveFreeGB
        recordTelemetrySample()

        loadedModelId = decoded.loaded_model_id
        if let ids = decoded.loaded_model_ids {
            loadedModelIds = ids
        } else if let single = decoded.loaded_model_id, decoded.model_loaded == true {
            loadedModelIds = [single]
        } else if decoded.any_model_loaded == false {
            loadedModelIds = []
        }
        if let details = decoded.loaded_models_detail {
            loadedModelsDetail = details.map {
                var c = $0; c.name = stripEmoji($0.name); return c
            }
        } else if decoded.any_model_loaded == false {
            loadedModelsDetail = []
        }
        modelLoaded = loadedModelIds.contains(selectedModelId) || (decoded.model_loaded ?? false)
        currentModelName = decoded.current_model ?? L("未加载", "Not Loaded")
        loadedContextLengthTokens = decoded.loaded_context_length ?? 0

        if !remoteContextSynced {
            remoteContextSynced = true
            if let rCtx = decoded.context_length, rCtx != contextLengthTokens {
                Task { await syncContextLengthToColab() }
            }
        }

        if let files = decoded.files, !files.isEmpty { modelFiles = files }
        downloadedCount = decoded.downloaded_count ?? downloadedCount
        totalFileCount = decoded.total_count ?? activeModelSpec.defaultFiles.count
        allDownloaded = decoded.all_downloaded ?? (downloadedCount == totalFileCount && totalFileCount > 0)
        totalDiskSizeGB = decoded.total_size_gb ?? totalDiskSizeGB
        drivePersisted = decoded.drive_persisted ?? false
        isDownloadingWeights = decoded.is_downloading ?? false
        isLoadingModel = decoded.is_loading_vram ?? false
        if let p = decoded.task_progress { modelTaskProgress = p }

        uptimeSeconds = decoded.uptime_seconds ?? uptimeSeconds
        cuBurnRatePerHour = decoded.cu_burn_rate_per_hour ?? cuBurnRatePerHour
        sessionCUUsed = decoded.session_cu_used ?? sessionCUUsed
        idleRemainingSeconds = decoded.idle_remaining_seconds ?? idleRemainingSeconds

        if !remoteIdleSynced {
            remoteIdleSynced = true
            if let rIdle = decoded.idle_timeout_minutes, rIdle != idleTimeoutMinutes {
                Task { await updateIdleTimeoutConfig(idleTimeoutMinutes) }
            }
        }

        apiRequestCount = decoded.api_request_count ?? apiRequestCount
        if apiKeyEnabled && !(decoded.api_key_enabled ?? false) && !remoteApiKeySynced {
            remoteApiKeySynced = true
            Task { await syncApiKeyToColab() }
        }
        if let lines = decoded.console_lines, !lines.isEmpty {
            liveConsoleLines = lines
        }

        if let cf = decoded.comfyui {
            comfyRunning = cf.is_running ?? false
            comfyStarting = cf.is_starting ?? false
            comfySyncingDrive = cf.is_syncing_drive ?? false
            comfyDownloadingWeight = cf.is_downloading_weight ?? false
            comfyInstallingPackId = cf.installing_pack_id ?? ""
            comfyProgress = cf.progress ?? 0.0
            if let sm = cf.status_message, !sm.isEmpty { comfyStatusMessage = stripEmoji(sm) }
            comfyPublicURL = cf.public_url ?? ""
            comfyQueueRunning = cf.queue_running ?? 0
            comfyQueuePending = cf.queue_pending ?? 0
            if let pl = cf.persistence_label, !pl.isEmpty { comfyPersistenceLabel = pl }
            comfyCustomNodesCount = cf.custom_nodes_count ?? 0
            comfyModelsCount = cf.models_count ?? 0
            comfyWorkflowsCount = cf.workflows_count ?? 0
            if let outs = cf.recent_outputs { comfyRecentOutputs = outs }
            if let packs = cf.preset_packs, !packs.isEmpty {
                comfyPresetPacks = packs
            }
        }

        if let serverCustoms = decoded.custom_models {
            mergeRemoteCustomModels(serverCustoms)
        }
    }


    // MARK: - Multimodal Inference & Job Polling

    func startLiveGenerationTimer() {
        generationTimerTask?.cancel()
        generationStartedAt = Date()
        currentJobElapsed = 0.0
        generationTimerTask = Task { [weak self] in
            while !Task.isCancelled {
                try? await Task.sleep(nanoseconds: 250_000_000)
                guard let self, self.isGenerating, let started = self.generationStartedAt else { break }
                let el = Date().timeIntervalSince(started)
                if el > self.currentJobElapsed { self.currentJobElapsed = el }
            }
        }
    }

    func stopLiveGenerationTimer() {
        generationTimerTask?.cancel()
        generationTimerTask = nil
        generationStartedAt = nil
    }

    func cancelCurrentGeneration() async {
        activeGenerationToken = UUID()
        pendingJobId = nil
        stopLiveGenerationTimer()
        endIOSBackgroundExecution()
        isGenerating = false
        progressValue = 0.0
        statusMessage = L("正在中断云端 GPU 推理任务...", "Aborting cloud GPU inference...")
        let base = normalizedBaseURL
        guard !base.isEmpty, let url = URL(string: "\(base)/minimax_api/cancel") else { return }
        var req = URLRequest(url: url)
        req.httpMethod = "POST"
        req.timeoutInterval = 12
        if let (data, _) = try? await URLSession.shared.data(for: req),
           let dec = try? JSONDecoder().decode(ColabStatusResponse.self, from: data) {
            applyStatusResponse(dec)
        }
        statusMessage = L("已停止当前生成任务。", "Stopped current generation job.")
    }

    func startGeneration() async {
        let promptTrimmed = visualPrompt.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !promptTrimmed.isEmpty else {
            statusMessage = L("请先输入提示词或对话内容！", "Please enter a prompt first!")
            return
        }
        if (taskModeId == "fl2va" || taskModeId == "i2i_edit") && firstFrameImage == nil && lastFrameImage == nil {
            statusMessage = L("请先从手机相册选择至少 1 张参考图片。", "Please select at least 1 reference photo first.")
            return
        }
        if !hasAcceptedCloudAIConsent {
            pendingAfterConsent = { [weak self] in
                Task { await self?.startGeneration() }
            }
            showAIConsentAlert = true
            return
        }

        await checkColabStatus(silent: true)
        guard isConnected else {
            statusMessage = L("尚未连接云端 Colab，请先前往「云算力」页唤醒或连接。", "Not connected to Colab. Wake or connect in Cloud tab first.")
            return
        }
        guard isSelectedModelLoadedInVRAM else {
            statusMessage = allDownloaded
                ? L("请先点击上方「加载到显存」装载模型。", "Tap 'Load to VRAM' above first.")
                : L("请先点击「下载权重」并「加载到显存」。", "Tap 'Download Weights' and 'Load to VRAM' first.")
            return
        }

        let base = normalizedBaseURL
        guard let submitURL = URL(string: "\(base)/minimax_api/generate") else { return }

        UIImpactFeedbackGenerator(style: .medium).impactOccurred()
        let myToken = UUID()
        activeGenerationToken = myToken
        isGenerating = true
        progressValue = 0.0
        currentJobElapsed = 0.0
        beginIOSBackgroundExecution(name: "EasyColabGenerate")
        startLiveGenerationTimer()

        let resOpt = activeModelSpec.modality == .image ? selectedImageResolution : selectedVideoResolution
        var chatPayload: [[String: String]] = []
        var assistantIdx: Int? = nil

        if activeModelSpec.modality == .llmVLM {
            let hasImg = (taskModeId == "vlm" && (firstFrameImage != nil || lastFrameImage != nil))
            chatHistory.append(ChatTurnItem(role: "user", content: promptTrimmed, hasImage: hasImg))
            chatPayload = chatHistory.map { ["role": $0.role, "content": $0.content] }
            chatHistory.append(ChatTurnItem(role: "assistant", content: "", thinking: ""))
            assistantIdx = chatHistory.count - 1
            pendingAssistantIndex = assistantIdx
            visualPrompt = ""
        } else {
            pendingAssistantIndex = nil
        }

        do {
            var req = URLRequest(url: submitURL)
            req.httpMethod = "POST"
            req.setValue("application/json", forHTTPHeaderField: "Content-Type")
            req.timeoutInterval = 30

            var payload: [String: Any] = [
                "model_id": selectedModelId,
                "task_mode": taskModeId,
                "visual_prompt": promptTrimmed,
                "negative_prompt": negativePrompt,
                "soundscape_prompt": soundscapePrompt,
                "music_prompt": musicPrompt,
                "width": resOpt.width,
                "height": resOpt.height,
                "num_frames": Int(numFrames),
                "num_inference_steps": Int(inferenceSteps),
                "fps": Int(fps),
                "seed": seed,
                "randomize_seed": randomizeSeed,
                "batch_count": activeModelSpec.modality == .llmVLM ? 1 : batchCount,
                "denoising_strength": denoisingStrength,
                "enable_thinking": enableThinking,
                "max_new_tokens": Int(maxNewTokens),
                "context_length": contextLengthTokens,
                "temperature": temperature,
                "top_p": topP,
                "top_k": 20,
                "min_p": 0.0,
                "presence_penalty": presencePenalty,
                "repeat_penalty": 1.0,
                "reasoning_effort": reasoningEffort
            ]
            if !chatPayload.isEmpty { payload["chat_messages"] = chatPayload }
            if ["fl2va", "i2v", "i2i_edit", "vlm"].contains(taskModeId) {
                if let img1 = firstFrameImage, let jpg = img1.jpegData(compressionQuality: 0.90) {
                    payload["first_frame_base64"] = jpg.base64EncodedString()
                }
                if let img2 = lastFrameImage, let jpg = img2.jpegData(compressionQuality: 0.90) {
                    payload["last_frame_base64"] = jpg.base64EncodedString()
                }
            }

            req.httpBody = try JSONSerialization.data(withJSONObject: payload)
            let (data, _) = try await URLSession.shared.data(for: req)
            guard activeGenerationToken == myToken else { return }
            let job = try JSONDecoder().decode(ColabJobResponse.self, from: data)

            if job.status == "failed" {
                stopLiveGenerationTimer()
                endIOSBackgroundExecution()
                isGenerating = false
                statusMessage = localizeServerText(job.message)
                if let idx = assistantIdx, idx < chatHistory.count {
                    chatHistory[idx].content = localizeServerText(job.message)
                }
                return
            }

            pendingJobId = job.job_id
            await pollColabJob(baseURL: base, jobId: job.job_id, assistantRowIndex: assistantIdx, token: myToken)
        } catch {
            guard activeGenerationToken == myToken else { return }
            stopLiveGenerationTimer()
            endIOSBackgroundExecution()
            isGenerating = false
            statusMessage = L("提交生成任务失败: \(error.localizedDescription)", "Failed to submit job: \(error.localizedDescription)")
        }
    }

    func pollColabJob(baseURL: String, jobId: String, assistantRowIndex: Int?, token: UUID) async {
        defer { endIOSBackgroundExecution() }
        guard let pollURL = URL(string: "\(baseURL)/minimax_api/job/\(jobId)") else {
            isGenerating = false
            return
        }
        var downloadedFilenames = Set<String>()
        var consecutiveErrors = 0
        let intervalNs: UInt64 = assistantRowIndex != nil ? 650_000_000 : 1_000_000_000

        while isGenerating && activeGenerationToken == token {
            try? await Task.sleep(nanoseconds: intervalNs)
            guard isGenerating && activeGenerationToken == token else { break }
            do {
                var req = URLRequest(url: pollURL)
                req.timeoutInterval = 30
                let (data, resp) = try await URLSession.shared.data(for: req)
                guard isGenerating && activeGenerationToken == token else { break }
                let code = (resp as? HTTPURLResponse)?.statusCode ?? 0
                if code == 404 {
                    consecutiveErrors += 2
                    if consecutiveErrors >= 8 {
                        pendingJobId = nil
                        isGenerating = false
                        stopLiveGenerationTimer()
                        break
                    }
                    continue
                }
                guard code == 200 else {
                    consecutiveErrors += 1
                    if consecutiveErrors >= 14 { isGenerating = false; stopLiveGenerationTimer(); break }
                    continue
                }
                consecutiveErrors = 0
                let job = try JSONDecoder().decode(ColabJobResponse.self, from: data)
                if let tl = job.telemetry { applyLiveTelemetrySnapshot(tl) }
                if job.status != "completed" {
                    progressValue = min(0.98, max(0.0, job.progress))
                }
                statusMessage = localizeServerText(job.message)
                if let el = job.elapsed, el >= 0 { currentJobElapsed = max(currentJobElapsed, el) }
                if let s = job.seed { seed = s }
                if let lines = job.console_lines, !lines.isEmpty { liveConsoleLines = lines }

                if let idx = assistantRowIndex, idx < chatHistory.count {
                    if let th = job.thinking_output { chatHistory[idx].thinking = th }
                    if let ans = job.text_output { chatHistory[idx].content = ans }
                }

                if let items = job.completed_videos {
                    for item in items where !downloadedFilenames.contains(item.filename) {
                        if let dlURL = URL(string: "\(baseURL)\(item.video_url)") {
                            downloadedFilenames.insert(item.filename)
                            await downloadMediaToLocal(from: dlURL, filename: item.filename, elapsedSeconds: item.elapsed ?? job.elapsed)
                        }
                    }
                }

                if job.status == "completed" {
                    let finalEl = job.elapsed ?? currentJobElapsed
                    lastCompletedElapsed = finalEl
                    if let fname = job.filename, !downloadedFilenames.contains(fname),
                       let path = job.video_url, let dlURL = URL(string: "\(baseURL)\(path)") {
                        downloadedFilenames.insert(fname)
                        progressValue = 0.99
                        await downloadMediaToLocal(from: dlURL, filename: fname, elapsedSeconds: finalEl)
                    }
                    pendingJobId = nil
                    stopLiveGenerationTimer()
                    isGenerating = false
                    progressValue = 1.0
                    UINotificationFeedbackGenerator().notificationOccurred(.success)
                    await checkColabStatus(silent: true)
                    break
                } else if job.status == "failed" {
                    if let idx = assistantRowIndex, idx < chatHistory.count, chatHistory[idx].content.isEmpty {
                        chatHistory[idx].content = localizeServerText(job.message)
                    }
                    pendingJobId = nil
                    stopLiveGenerationTimer()
                    isGenerating = false
                    progressValue = 0.0
                    UINotificationFeedbackGenerator().notificationOccurred(.error)
                    break
                }
            } catch {
                consecutiveErrors += 1
                // Keep pendingJobId alive on transient iOS background network suspension!
                if consecutiveErrors >= 20 {
                    stopLiveGenerationTimer()
                    isGenerating = false
                    break
                }
            }
        }
    }

}
