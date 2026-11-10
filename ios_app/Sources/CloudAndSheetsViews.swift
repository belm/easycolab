import SwiftUI
import PhotosUI

// MARK: - Tab 1: Multimodal Creation Studio (Video+Audio, Image, Qwen3.8 Chat/API, ComfyUI)
// MARK: - Tab 2: Cloud GPU Management (Native Google OAuth + 1-Tap G4 Wake + Telemetry)

struct CloudGPUTabView: View {
    @ObservedObject var vm: IOSStudioViewModel
    @ObservedObject var langMgr = LanguageManager.shared

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 14) {
                    nativeHeadlessWakeCard
                    manualTunnelConnectCard
                    SmoothTelemetryChartCard(vm: vm)
                    if !vm.loadedModelsDetail.isEmpty {
                        residentModelsCard
                    }
                    powerAndBillingSafetyCard
                }
                .padding(14)
            }
            .scrollDismissesKeyboard(.immediately)
            .background(Color(UIColor.systemGroupedBackground))
            .navigationTitle(L("云端算力中心", "Cloud GPU Center"))
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        Task {
                            await vm.refreshOfficialColabAccountUsage()
                            if !vm.normalizedBaseURL.isEmpty {
                                await vm.checkColabStatus()
                            }
                        }
                    } label: {
                        Image(systemName: "arrow.clockwise")
                    }
                }
            }
            .sheet(isPresented: $vm.showOAuthCodeSheet) {
                oauthAuthorizationSheet
                    .presentationDetents([.medium, .large])
            }
            .confirmationDialog(
                L("确认断开并销毁账号下全部云端 Colab 实例？", "Terminate all active cloud Colab VMs on your account?"),
                isPresented: $vm.showDisconnectConfirm,
                titleVisibility: .visible
            ) {
                Button(L("彻底释放实例并停止计费 (0 CU/h)", "Terminate All VMs (0 CU/h)"), role: .destructive) {
                    Task { await vm.disconnectRemoteColab() }
                }
                Button(L("取消", "Cancel"), role: .cancel) {}
            }
        }
    }

    private static let gpuWakeOptions: [(id: String, menuLabel: String, inlineLabel: String)] = [
        ("G4", "G4 · RTX PRO 6000 (96GB VRAM)", "G4 · RTX PRO 6000 (96GB)"),
        ("H100", "H100 · SXM5 (80GB VRAM)", "H100 (80GB)"),
        ("A100", "A100 · SXM4 (80GB VRAM)", "A100 (80GB)"),
        ("L4", "L4 · Ada Lovelace (24GB VRAM)", "L4 (24GB)"),
        ("T4", "T4 · Turing (16GB VRAM)", "T4 (16GB)")
    ]

    private static func gpuInlineLabel(for id: String) -> String {
        gpuWakeOptions.first(where: { $0.id == id })?.inlineLabel ?? id
    }

    private func idleTimeoutLabel(_ mins: Int) -> String {
        mins <= 0 ? L("不休眠", "Never") : L("\(mins) 分钟", "\(mins) min")
    }

    private var nativeHeadlessWakeCard: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(spacing: 8) {
                Label(L("免网页一键唤醒部署", "1-Tap Headless Wake"), systemImage: "bolt.icloud.fill")
                    .font(.subheadline.weight(.bold))
                    .lineLimit(1)
                    .minimumScaleFactor(0.85)
                Spacer(minLength: 4)
                if vm.cliLoggedIn {
                    Menu {
                        Button(L("切换 Google 账号 (一键授权)", "Switch Account (1-Tap)")) {
                            Task { await vm.startGoogleOAuthLogin() }
                        }
                        Button(L("手动授权码 / 跨设备绑定", "Manual Code / External Browser")) {
                            vm.openManualOAuthSheet()
                        }
                        Button(L("退出账号绑定", "Sign Out"), role: .destructive) {
                            Task { await vm.logoutGoogleAccount() }
                        }
                    } label: {
                        HStack(spacing: 4) {
                            Image(systemName: "checkmark.seal.fill").foregroundColor(.green)
                            Text(vm.displayAccountLabel)
                                .lineLimit(1)
                                .truncationMode(.middle)
                        }
                        .font(.caption.weight(.semibold))
                    }
                } else {
                    HStack(spacing: 6) {
                        Button {
                            Task { await vm.startGoogleOAuthLogin() }
                        } label: {
                            HStack(spacing: 4) {
                                if vm.isAuthenticatingGoogle {
                                    ProgressView().controlSize(.mini)
                                } else {
                                    Image(systemName: "person.crop.circle.badge.plus")
                                }
                                Text(L("绑定账号", "Bind Google"))
                                    .lineLimit(1)
                            }
                            .font(.caption.weight(.bold))
                        }
                        .buttonStyle(.borderedProminent)
                        .controlSize(.small)
                        .disabled(vm.isAuthenticatingGoogle)

                        Button {
                            vm.openManualOAuthSheet()
                        } label: {
                            Image(systemName: "key.fill")
                                .font(.caption)
                        }
                        .buttonStyle(.bordered)
                        .controlSize(.small)
                        .accessibilityLabel(L("手动授权码绑定", "Manual Auth Code"))
                    }
                    .fixedSize(horizontal: true, vertical: false)
                }
            }

            // CU Balance & Burn Rate Metrics
            HStack(spacing: 10) {
                VStack(alignment: .leading, spacing: 2) {
                    Text(L("可用计算单元 (CU)", "Compute Units (CU)"))
                        .font(.caption2).foregroundColor(.secondary)
                    Text(vm.cliLoggedIn ? String(format: "%.2f CU", vm.displayRemainingCU) : "-- CU")
                        .font(.subheadline.monospacedDigit().weight(.bold))
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(10)
                .background(Color(UIColor.tertiarySystemFill))
                .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))

                VStack(alignment: .leading, spacing: 2) {
                    Text(L("实时消耗速率", "Hourly Burn Rate"))
                        .font(.caption2).foregroundColor(.secondary)
                    Text(String(format: "%.2f CU/h", vm.displayBurnRate))
                        .font(.subheadline.monospacedDigit().weight(.bold))
                        .foregroundColor(vm.displayBurnRate > 0 ? .orange : .green)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(10)
                .background(Color(UIColor.tertiarySystemFill))
                .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
            }

            HStack(spacing: 8) {
                Text(L("目标 GPU 规格", "Target GPU"))
                    .font(.caption.weight(.semibold))
                    .lineLimit(1)
                    .fixedSize(horizontal: true, vertical: false)
                Spacer(minLength: 6)
                Menu {
                    ForEach(Self.gpuWakeOptions, id: \.id) { opt in
                        Button {
                            vm.wakeGPUChoice = opt.id
                        } label: {
                            if vm.wakeGPUChoice == opt.id {
                                Label(opt.menuLabel, systemImage: "checkmark")
                            } else {
                                Text(opt.menuLabel)
                            }
                        }
                    }
                } label: {
                    HStack(spacing: 5) {
                        Text(Self.gpuInlineLabel(for: vm.wakeGPUChoice))
                            .font(.caption.weight(.semibold))
                            .lineLimit(1)
                            .minimumScaleFactor(0.85)
                        Image(systemName: "chevron.up.chevron.down")
                            .font(.system(size: 10, weight: .bold))
                    }
                    .foregroundColor(.accentColor)
                    .padding(.horizontal, 10)
                    .padding(.vertical, 6)
                    .background(Color.accentColor.opacity(0.12))
                    .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
                }
            }

            Button {
                Task { await vm.wakeColabHeadless() }
            } label: {
                HStack(spacing: 8) {
                    if vm.isWakingColab {
                        ProgressView().tint(.white)
                    } else {
                        Image(systemName: "power.circle.fill")
                    }
                    Text(vm.isWakingColab
                         ? L("正在唤醒 \(vm.wakeGPUChoice) 并部署引擎...", "Waking \(vm.wakeGPUChoice) & Deploying...")
                         : L("一键唤醒 \(vm.wakeGPUChoice) 实例并自动部署", "1-Tap Wake \(vm.wakeGPUChoice) & Auto-Deploy"))
                        .font(.subheadline.weight(.bold))
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, 13)
                .background(vm.cliLoggedIn ? Color.orange : Color.gray.opacity(0.5))
                .foregroundColor(.white)
                .clipShape(RoundedRectangle(cornerRadius: 13, style: .continuous))
            }
            .disabled(vm.isWakingColab)

            Text(vm.statusMessage)
                .font(.caption2)
                .foregroundColor(.secondary)
        }
        .padding(14)
        .background(Color(UIColor.secondarySystemGroupedBackground))
        .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
    }

    private var manualTunnelConnectCard: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 8) {
                Label(L("服务地址直连 (网页端/免费层)", "Direct Tunnel URL Connect"), systemImage: "link")
                    .font(.subheadline.weight(.semibold))
                    .lineLimit(1)
                    .minimumScaleFactor(0.85)
                Spacer(minLength: 4)
                Button {
                    if let clip = UIPasteboard.general.string?.trimmingCharacters(in: .whitespacesAndNewlines), !clip.isEmpty {
                        vm.colabServerURL = clip
                        Task { await vm.checkColabStatus() }
                    }
                } label: {
                    Label(L("粘贴并连接", "Paste & Connect"), systemImage: "doc.on.clipboard")
                        .font(.caption.weight(.semibold))
                        .lineLimit(1)
                }
                .buttonStyle(.bordered)
                .controlSize(.mini)
                .fixedSize(horizontal: true, vertical: false)
            }

            HStack(spacing: 8) {
                Group {
                    if vm.maskServerURL {
                        SecureField("https://xxxx.gradio.live", text: $vm.colabServerURL)
                            .submitLabel(.go)
                            .onSubmit {
                                dismissIOSKeyboard()
                                Task { await vm.checkColabStatus() }
                            }
                    } else {
                        TextField("https://xxxx.gradio.live", text: $vm.colabServerURL)
                            .keyboardType(.URL)
                            .textInputAutocapitalization(.never)
                            .autocorrectionDisabled()
                            .submitLabel(.go)
                            .onSubmit {
                                dismissIOSKeyboard()
                                Task { await vm.checkColabStatus() }
                            }
                    }
                }
                .font(.caption.monospaced())
                .padding(9)
                .background(Color(UIColor.tertiarySystemFill))
                .clipShape(RoundedRectangle(cornerRadius: 9, style: .continuous))

                Button {
                    dismissIOSKeyboard()
                    Task { await vm.checkColabStatus() }
                } label: {
                    Text(L("连接", "Connect"))
                        .font(.caption.weight(.bold))
                }
                .buttonStyle(.borderedProminent)
                .controlSize(.small)
            }
        }
        .padding(14)
        .background(Color(UIColor.secondarySystemGroupedBackground))
        .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
    }

    private var residentModelsCard: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Label(L("当前 GPU 显存共驻模型", "Models Resident in VRAM"), systemImage: "memorychip")
                    .font(.subheadline.weight(.semibold))
                Spacer()
                Button(L("全部卸载", "Unload All")) {
                    Task { await vm.unloadRemoteModelFromVRAM(modelId: "all") }
                }
                .font(.caption)
                .foregroundColor(.red)
            }
            ForEach(vm.loadedModelsDetail) { item in
                HStack {
                    Text(item.localizedName).font(.caption.weight(.medium))
                    if let gb = item.vram_gb, gb > 0 {
                        Text(String(format: "%.1f GB", gb))
                            .font(.caption2.monospacedDigit())
                            .foregroundColor(.secondary)
                    }
                    Spacer()
                    Button(L("卸载", "Unload")) {
                        Task { await vm.unloadRemoteModelFromVRAM(modelId: item.id) }
                    }
                    .buttonStyle(.bordered)
                    .controlSize(.mini)
                }
            }
        }
        .padding(14)
        .background(Color(UIColor.secondarySystemGroupedBackground))
        .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
    }

    private var powerAndBillingSafetyCard: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(spacing: 8) {
                Label(L("闲置省额度保护 (云端看门狗)", "Cloud Auto-Sleep Protection"), systemImage: "moon.zzz.fill")
                    .font(.subheadline.weight(.semibold))
                    .lineLimit(1)
                    .minimumScaleFactor(0.85)
                Spacer(minLength: 6)
                Menu {
                    ForEach([15, 30, 60, 0], id: \.self) { mins in
                        Button {
                            Task { await vm.updateIdleTimeoutConfig(mins) }
                        } label: {
                            if vm.idleTimeoutMinutes == mins {
                                Label(idleTimeoutLabel(mins), systemImage: "checkmark")
                            } else {
                                Text(idleTimeoutLabel(mins))
                            }
                        }
                    }
                } label: {
                    HStack(spacing: 4) {
                        Text(idleTimeoutLabel(vm.idleTimeoutMinutes))
                            .font(.caption.weight(.semibold))
                            .lineLimit(1)
                        Image(systemName: "chevron.up.chevron.down")
                            .font(.system(size: 10, weight: .bold))
                    }
                    .foregroundColor(.accentColor)
                    .padding(.horizontal, 10)
                    .padding(.vertical, 6)
                    .background(Color.accentColor.opacity(0.12))
                    .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
                    .fixedSize(horizontal: true, vertical: false)
                }
            }

            if vm.isConnected {
                HStack {
                    Text(L("在线时长: \(vm.formattedUptime)", "Uptime: \(vm.formattedUptime)"))
                    Spacer()
                    Text(vm.formattedIdleRemaining)
                }
                .font(.caption2.monospacedDigit())
                .foregroundColor(.secondary)
            }

            Text(L("提示：即使手机锁屏、切后台或没电关机，云端看门狗也会在闲置到期后自动销毁虚拟机，绝不空烧 CU。", "Even if your iPhone locks or loses power, the cloud-side watchdog automatically unassigns the VM after the idle timeout."))
                .font(.caption2)
                .foregroundColor(.secondary)

            Button(role: .destructive) {
                vm.showDisconnectConfirm = true
            } label: {
                Label(L("断开连接并彻底释放全部实例 (0 CU/h)", "Disconnect & Terminate All Cloud VMs"), systemImage: "xmark.octagon.fill")
                    .font(.subheadline.weight(.bold))
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 6)
            }
            .buttonStyle(.borderedProminent)
            .tint(.red)
        }
        .padding(14)
        .background(Color(UIColor.secondarySystemGroupedBackground))
        .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
    }

    private var oauthAuthorizationSheet: some View {
        NavigationStack {
            VStack(alignment: .leading, spacing: 14) {
                Text(L("备选绑定方式：独立浏览器 / 手动授权码", "Alternative Sign-In: Safari / Manual Code"))
                    .font(.headline)

                Text(L("方式 A：点击「跳往系统 Safari 登录」，在系统浏览器完成授权后会自动跳回本 App 完成绑定；\n方式 B：点击「复制登录链接」，在电脑或任意浏览器打开授权后，将页面显示的 4/ 开头授权码粘贴到下方。", "Option A: Tap 'Open in System Safari' — returns automatically after approval.\nOption B: Tap 'Copy Login URL', sign in on PC/any browser, and paste the 4/... code below."))
                    .font(.footnote)
                    .foregroundColor(.secondary)

                HStack(spacing: 10) {
                    Button {
                        Task { await vm.openGoogleOAuthInExternalSafari() }
                    } label: {
                        Label(L("跳往系统 Safari 登录", "Open in System Safari"), systemImage: "safari.fill")
                            .font(.caption.weight(.semibold))
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.borderedProminent)

                    Button {
                        Task { await vm.copyManualGoogleOAuthLink() }
                    } label: {
                        Label(L("复制登录链接", "Copy Login URL"), systemImage: "doc.on.doc")
                            .font(.caption.weight(.semibold))
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.bordered)
                }

                HStack {
                    TextField(L("粘贴 Google 授权码 (4/0A...)", "Paste authorization code (4/0A...)"), text: $vm.oauthCodeText)
                        .font(.caption.monospaced())
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                        .submitLabel(.done)
                        .onSubmit { dismissIOSKeyboard() }
                        .padding(10)
                        .background(Color(UIColor.tertiarySystemFill))
                        .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))

                    Button(L("粘贴", "Paste")) {
                        if let s = UIPasteboard.general.string {
                            vm.oauthCodeText = s.trimmingCharacters(in: .whitespacesAndNewlines)
                        }
                    }
                    .buttonStyle(.bordered)
                }

                Button {
                    dismissIOSKeyboard()
                    Task { await vm.submitGoogleOAuthCode() }
                } label: {
                    Text(L("验证授权码并绑定", "Verify Code & Bind"))
                        .fontWeight(.bold)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 4)
                }
                .buttonStyle(.borderedProminent)
                .disabled(vm.oauthCodeText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)

                Spacer()
            }
            .padding(20)
            .background(IOSKeyboardDismissTapInstaller())
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button(L("关闭", "Close")) { vm.showOAuthCodeSheet = false }
                }
            }
        }
    }
}

// MARK: - Tab 4: Live Cloud Console & Settings

struct ConsoleAndSettingsTabView: View {
    @ObservedObject var vm: IOSStudioViewModel
    @ObservedObject var langMgr = LanguageManager.shared
    @State private var showCustomOAuthSheet = false
    @State private var showPrivacyPolicySheet = false
    @State private var customOAuthInput = ""
    @State private var shareNotebookURL: IdentifiableURL? = nil

    var body: some View {
        NavigationStack {
            List {
                Section(L("云端实时终端日志", "Live Cloud Terminal")) {
                    VStack(alignment: .leading, spacing: 8) {
                        ScrollView {
                            LazyVStack(alignment: .leading, spacing: 4) {
                                ForEach(Array(vm.liveConsoleLines.suffix(80).enumerated()), id: \.offset) { _, line in
                                    Text(localizeServerText(line))
                                        .font(.system(size: 11, design: .monospaced))
                                        .foregroundColor(Color(red: 0.78, green: 0.92, blue: 0.84))
                                        .frame(maxWidth: .infinity, alignment: .leading)
                                }
                            }
                            .padding(10)
                        }
                        .frame(height: 200)
                        .background(Color(red: 0.07, green: 0.09, blue: 0.12))
                        .clipShape(RoundedRectangle(cornerRadius: 11, style: .continuous))

                        HStack {
                            Button {
                                UIPasteboard.general.string = vm.liveConsoleLines.joined(separator: "\n")
                                vm.showToast(L("已复制终端日志", "Copied console logs"))
                            } label: {
                                Label(L("复制日志", "Copy"), systemImage: "doc.on.doc")
                                    .font(.caption)
                            }
                            .buttonStyle(.bordered)
                            Spacer()
                            Button {
                                vm.liveConsoleLines = [L("已清空终端日志。", "Cleared console logs.")]
                            } label: {
                                Label(L("清空", "Clear"), systemImage: "trash")
                                    .font(.caption)
                            }
                            .buttonStyle(.bordered)
                        }
                    }
                    .listRowInsets(EdgeInsets(top: 10, leading: 12, bottom: 10, trailing: 12))
                }

                Section(L("偏好设置", "Preferences")) {
                    Toggle(L("生成后自动存入系统相册", "Auto-Save Outputs to iPhone Photos"), isOn: $vm.autoSaveToPhotos)
                    Toggle(L("录屏/截图隐私打码模式", "Privacy Mask (Hide URLs & Email)"), isOn: $vm.maskServerURL)
                    HStack {
                        Text(L("界面语言 / Language", "Language"))
                        Spacer()
                        Picker("", selection: $langMgr.lang) {
                            Text("简体中文").tag(AppLanguage.zh)
                            Text("English").tag(AppLanguage.en)
                        }
                        .pickerStyle(.segmented)
                        .frame(width: 165)
                    }
                }

                Section(L("高级与凭证配置", "Advanced & Credentials")) {
                    VStack(alignment: .leading, spacing: 4) {
                        Text("Hugging Face Token (Optional)")
                            .font(.caption).foregroundColor(.secondary)
                        SecureField("hf_xxxxxxxxxxxxxxxx", text: $vm.hfToken)
                            .font(.caption.monospaced())
                            .submitLabel(.done)
                            .onSubmit { dismissIOSKeyboard() }
                    }

                    Button {
                        showCustomOAuthSheet = true
                    } label: {
                        HStack {
                            Label(L("自定义 Google OAuth 客户端 JSON", "Custom Google OAuth Client JSON"), systemImage: "key.fill")
                            Spacer()
                            Text(vm.hasCustomOAuth ? L("自定义", "Custom") : L("默认内置", "Default"))
                                .font(.caption)
                                .foregroundColor(.secondary)
                        }
                    }

                    if let nbURL = vm.exportableNotebookURL() {
                        Button {
                            shareNotebookURL = IdentifiableURL(url: nbURL)
                        } label: {
                            Label(L("导出 EasyColab_Server.ipynb (供免费版网页运行)", "Export EasyColab_Server.ipynb"), systemImage: "square.and.arrow.up")
                        }
                    }

                    Button {
                        vm.showOnboardingSheet = true
                    } label: {
                        Label(L("重新查看新手引导", "View Quick Start Guide"), systemImage: "sparkles.rectangle.stack")
                    }
                }

                Section(L("隐私、数据安全与合规", "Privacy, Data Safety & Terms")) {
                    Button {
                        showPrivacyPolicySheet = true
                    } label: {
                        Label(L("隐私政策与用户使用条款", "Privacy Policy & Terms of Use"), systemImage: "hand.raised.shield.fill")
                    }

                    Text(L("EasyColab 连接您选择的云端服务。Google OAuth 凭证保存在设备钥匙串及受设备文件保护的应用支持文件中；您可在「云算力」页解绑并清除本地授权凭证。", "EasyColab connects to your chosen cloud service. Google OAuth credentials are stored in the device Keychain and a device-protected app support file. You can unbind and clear local credentials in the Cloud tab."))
                        .font(.caption2)
                        .foregroundColor(.secondary)
                }
            }
            .scrollDismissesKeyboard(.immediately)
            .navigationTitle(L("终端与设置", "Console & Settings"))
            .navigationBarTitleDisplayMode(.inline)
            .sheet(isPresented: $showPrivacyPolicySheet) {
                NavigationStack {
                    ScrollView {
                        VStack(alignment: .leading, spacing: 14) {
                            Text(L("1. 零数据收集与零中转服务器", "1. Zero Data Collection & Zero Middleman Servers"))
                                .font(.headline)
                            Text(L("EasyColab 是一款纯本地运行的客户端工具，不设任何开发者后端服务器，不接入任何广告或第三方追踪 SDK，亦不建立平台自有账号体系。", "EasyColab is a pure client-side studio with no developer backend servers, no ads, no third-party analytics SDKs, and no proprietary account database."))
                                .font(.subheadline).foregroundColor(.secondary)

                            Text(L("2. 云端 AI 推理与数据传输流向", "2. Cloud AI Data Transmission"))
                                .font(.headline)
                            Text(L("当您连接 Google Colab 实例发起生视频、生图或多模态对话时，您输入的提示词与主动选择的参考图片仅通过 HTTPS 加密通道直连发送至您本人控制的云端虚拟机处理，生成的作品直接回传保存在您的设备本地。", "Prompts and selected reference photos are transmitted directly over HTTPS solely to your own connected Google Colab runtime. Generated media is saved locally on your device."))
                                .font(.subheadline).foregroundColor(.secondary)

                            Text(L("3. Google 授权凭证与相册权限", "3. Google OAuth & Photo Library Permissions"))
                                .font(.headline)
                            Text(L("若您选择使用 Google 账号授权管理云端实例，OAuth 凭证保存在设备钥匙串及受设备文件保护的应用支持文件中；您可在「云算力」页解绑并清除本地授权凭证。相册权限用于选取参考图及将生成的作品写入系统相册。", "If you authorize Google access, OAuth credentials are stored in the device Keychain and a device-protected app support file. You can unbind and clear local credentials in the Cloud tab. Photo access is used to select reference images and save generated media."))
                                .font(.subheadline).foregroundColor(.secondary)

                            Text(L("4. AI 生成内容责任与独立声明", "4. AI Content Safety & Non-Affiliation"))
                                .font(.headline)
                            Text(L("请勿使用本工具生成违法、侵权或不当内容；您可在预览卡片点击旗标按钮随时标记并彻底清除异常生成结果。EasyColab 为独立开发的客户端工具，与 Google LLC 无隶属或背书关系。", "Do not generate unlawful or harmful content; you can flag and purge any unwanted AI output directly from the preview card. EasyColab is an independent client and is not affiliated with Google LLC."))
                                .font(.subheadline).foregroundColor(.secondary)
                        }
                        .padding(20)
                    }
                    .navigationTitle(L("隐私政策与条款", "Privacy & Terms"))
                    .navigationBarTitleDisplayMode(.inline)
                    .toolbar {
                        ToolbarItem(placement: .confirmationAction) {
                            Button(L("完成", "Done")) { showPrivacyPolicySheet = false }
                        }
                    }
                }
            }
            .sheet(isPresented: $showCustomOAuthSheet) {
                NavigationStack {
                    VStack(alignment: .leading, spacing: 14) {
                        Text(L("粘贴你自己的 Google Cloud OAuth 桌面客户端 JSON（留空保存即可恢复默认内置配置）：", "Paste your own Google OAuth Desktop JSON (leave empty to restore default):"))
                            .font(.footnote)
                            .foregroundColor(.secondary)
                        TextEditor(text: $customOAuthInput)
                            .font(.caption.monospaced())
                            .frame(height: 180)
                            .padding(8)
                            .background(Color(UIColor.tertiarySystemFill))
                            .clipShape(RoundedRectangle(cornerRadius: 10))
                        Button {
                            dismissIOSKeyboard()
                            Task {
                                let msg = await vm.saveCustomOAuthConfigJSON(customOAuthInput)
                                vm.showToast(msg)
                                showCustomOAuthSheet = false
                            }
                        } label: {
                            Text(L("保存配置", "Save Config"))
                                .fontWeight(.bold)
                                .frame(maxWidth: .infinity)
                        }
                        .buttonStyle(.borderedProminent)
                        Spacer()
                    }
                    .padding(20)
                    .background(IOSKeyboardDismissTapInstaller())
                    .navigationTitle("OAuth JSON")
                    .navigationBarTitleDisplayMode(.inline)
                    .toolbar {
                        ToolbarItem(placement: .cancellationAction) {
                            Button(L("取消", "Cancel")) { showCustomOAuthSheet = false }
                        }
                    }
                }
            }
            .sheet(item: $shareNotebookURL) { wrapped in
                ActivityShareSheet(items: [wrapped.url])
            }
        }
    }
}

// MARK: - Custom HuggingFace Repository Import Sheet

struct AddCustomHFModelSheet: View {
    @ObservedObject var vm: IOSStudioViewModel
    @ObservedObject var langMgr = LanguageManager.shared
    @Environment(\.dismiss) private var dismiss
    @State private var searchQueryText: String = ""

    private let trendingTabs: [(id: String, zh: String, en: String)] = [
        ("all", "综合热榜", "Trending"),
        ("gguf", "GGUF 量化", "GGUF"),
        ("llm", "对话/视觉", "LLM/VLM"),
        ("image_video", "生图/视频", "Image/Video"),
    ]

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    VStack(alignment: .leading, spacing: 6) {
                        HStack(spacing: 8) {
                            Image(systemName: "shippingbox.and.arrow.backward.fill")
                                .font(.title3)
                                .foregroundColor(.accentColor)
                            Text(L("导入自定义 HuggingFace 模型仓库", "Import Custom HuggingFace Repository"))
                                .font(.headline)
                        }
                        Text(L("支持从下方实时拉取 HuggingFace 热门趋势或在线搜索模型一键填入（含参数量与 Colab 显存部署评估）。若为受限模型 (Gated Repo)，请填写 HF Token 并同意协议。", "Pick from live HuggingFace trending or search models below (with parameter count & Colab VRAM fit). For gated repos, enter your HF Token and accept the license."))
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                    .padding(14)
                    .background(Color(UIColor.secondarySystemGroupedBackground))
                    .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))

                    VStack(alignment: .leading, spacing: 12) {
                        VStack(alignment: .leading, spacing: 8) {
                            HStack {
                                Image(systemName: "flame.fill")
                                    .foregroundColor(.orange)
                                    .font(.caption)
                                Text(L("HuggingFace 实时热榜与搜索", "Live HuggingFace Trending & Search"))
                                    .font(.caption.weight(.bold))
                                Spacer()
                                Button {
                                    Task { await vm.fetchTrendingHFModels(category: vm.trendingHFCategory, searchQuery: searchQueryText, forceRefresh: true) }
                                } label: {
                                    HStack(spacing: 4) {
                                        if vm.isLoadingTrendingHF {
                                            ProgressView().scaleEffect(0.7)
                                        } else {
                                            Image(systemName: "arrow.clockwise")
                                                .font(.caption2.weight(.bold))
                                        }
                                        Text(L("刷新", "Refresh"))
                                            .font(.caption2.weight(.semibold))
                                    }
                                    .foregroundColor(.accentColor)
                                }
                                .buttonStyle(.plain)
                            }

                            HStack(spacing: 6) {
                                Image(systemName: "magnifyingglass")
                                    .font(.caption)
                                    .foregroundColor(.secondary)
                                TextField(L("搜索 HF 模型 (如 Qwen3 GGUF / DeepSeek 9B)...", "Search HF models (e.g. Qwen3 GGUF / DeepSeek 9B)..."), text: $searchQueryText)
                                    .textInputAutocapitalization(.never)
                                    .autocorrectionDisabled()
                                    .font(.caption)
                                    .submitLabel(.search)
                                    .onSubmit {
                                        dismissIOSKeyboard()
                                        Task { await vm.fetchTrendingHFModels(category: vm.trendingHFCategory, searchQuery: searchQueryText, forceRefresh: true) }
                                    }
                                if !searchQueryText.isEmpty {
                                    Button {
                                        searchQueryText = ""
                                        Task { await vm.fetchTrendingHFModels(category: vm.trendingHFCategory, searchQuery: "", forceRefresh: false) }
                                    } label: {
                                        Image(systemName: "xmark.circle.fill")
                                            .font(.caption)
                                            .foregroundColor(.secondary)
                                    }
                                    .buttonStyle(.plain)
                                }
                                Button {
                                    dismissIOSKeyboard()
                                    Task { await vm.fetchTrendingHFModels(category: vm.trendingHFCategory, searchQuery: searchQueryText, forceRefresh: true) }
                                } label: {
                                    Text(L("搜索", "Search"))
                                        .font(.caption2.weight(.bold))
                                        .padding(.horizontal, 8)
                                        .padding(.vertical, 5)
                                        .background(Color.accentColor)
                                        .foregroundColor(.white)
                                        .clipShape(Capsule())
                                }
                                .buttonStyle(.plain)
                            }
                            .padding(.horizontal, 10)
                            .padding(.vertical, 6)
                            .background(Color(UIColor.tertiarySystemFill))
                            .clipShape(RoundedRectangle(cornerRadius: 9, style: .continuous))

                            ScrollView(.horizontal, showsIndicators: false) {
                                HStack(spacing: 6) {
                                    ForEach(trendingTabs, id: \.id) { tab in
                                        let isSel = vm.trendingHFCategory == tab.id
                                        Button {
                                            Task { await vm.fetchTrendingHFModels(category: tab.id, searchQuery: searchQueryText, forceRefresh: false) }
                                        } label: {
                                            Text(L(tab.zh, tab.en))
                                                .font(.caption2.weight(isSel ? .bold : .medium))
                                                .padding(.horizontal, 10)
                                                .padding(.vertical, 5)
                                                .background(isSel ? Color.accentColor : Color(UIColor.tertiarySystemFill))
                                                .foregroundColor(isSel ? .white : .primary)
                                                .clipShape(Capsule())
                                        }
                                        .buttonStyle(.plain)
                                    }
                                }
                            }

                            if vm.trendingHFModels.isEmpty {
                                HStack(spacing: 8) {
                                    if vm.isLoadingTrendingHF {
                                        ProgressView().scaleEffect(0.8)
                                        Text(L("正在从 HuggingFace 实时拉取模型及参数量/显存评估...", "Fetching models, parameter counts & Colab VRAM fit..."))
                                            .font(.caption2)
                                            .foregroundColor(.secondary)
                                    } else {
                                        Text(L("未找到匹配模型，可点击「刷新」或更换搜索词。", "No models found. Tap 'Refresh' or try another keyword."))
                                            .font(.caption2)
                                            .foregroundColor(.secondary)
                                    }
                                }
                                .padding(.vertical, 6)
                            } else {
                                ScrollView(.horizontal, showsIndicators: false) {
                                    HStack(spacing: 8) {
                                        ForEach(vm.trendingHFModels) { item in
                                            let isSelected = vm.customRepoIdInput == item.repo_id
                                            Button {
                                                vm.customRepoIdInput = item.repo_id
                                                vm.customIncludePatternInput = item.suggested_pattern
                                                vm.customDisplayNameInput = item.name
                                                vm.customModalityHint = item.modality
                                            } label: {
                                                VStack(alignment: .leading, spacing: 4) {
                                                    HStack(spacing: 4) {
                                                        if item.is_gated {
                                                            Image(systemName: "lock.fill")
                                                                .font(.system(size: 9))
                                                                .foregroundColor(.orange)
                                                        }
                                                        Text(item.name)
                                                            .font(.caption.weight(.bold))
                                                            .lineLimit(1)
                                                        Spacer(minLength: 2)
                                                        if let pLabel = item.param_label, !pLabel.isEmpty {
                                                            Text(pLabel)
                                                                .font(.system(size: 9, weight: .heavy, design: .rounded))
                                                                .padding(.horizontal, 5)
                                                                .padding(.vertical, 1.5)
                                                                .background(Color.purple.opacity(0.16))
                                                                .foregroundColor(.purple)
                                                                .clipShape(Capsule())
                                                        }
                                                    }
                                                    Text(item.repo_id)
                                                        .font(.system(size: 10, design: .monospaced))
                                                        .foregroundColor(.secondary)
                                                        .lineLimit(1)
                                                    HStack(spacing: 6) {
                                                        Text(item.is_gguf ? "GGUF" : item.pipeline_tag)
                                                            .font(.system(size: 9, weight: .semibold))
                                                            .padding(.horizontal, 5)
                                                            .padding(.vertical, 2)
                                                            .background(Color.accentColor.opacity(0.15))
                                                            .foregroundColor(.accentColor)
                                                            .clipShape(Capsule())
                                                        if item.likes > 0 {
                                                            HStack(spacing: 2) {
                                                                Image(systemName: "heart.fill")
                                                                    .font(.system(size: 8))
                                                                Text("\(item.likes)")
                                                                    .font(.system(size: 9))
                                                            }
                                                            .foregroundColor(.secondary)
                                                        }
                                                    }
                                                    HStack(spacing: 4) {
                                                        Circle()
                                                            .fill(item.deployBadgeColor)
                                                            .frame(width: 5.5, height: 5.5)
                                                        Text(item.localizedDeployLabel)
                                                            .font(.system(size: 9.5, weight: .semibold))
                                                            .foregroundColor(item.deployBadgeColor)
                                                            .lineLimit(1)
                                                        Spacer(minLength: 2)
                                                        Button {
                                                            vm.customRepoIdInput = item.repo_id
                                                            vm.customIncludePatternInput = item.suggested_pattern
                                                            vm.customDisplayNameInput = item.name
                                                            vm.customModalityHint = item.modality
                                                            Task { await vm.fetchHFModelDetail(repoId: item.repo_id) }
                                                        } label: {
                                                            HStack(spacing: 2) {
                                                                Image(systemName: "info.circle.fill")
                                                                    .font(.system(size: 9))
                                                                Text(L("详情", "Info"))
                                                                    .font(.system(size: 9, weight: .bold))
                                                            }
                                                            .padding(.horizontal, 5)
                                                            .padding(.vertical, 2)
                                                            .background(Color.accentColor.opacity(0.15))
                                                            .foregroundColor(.accentColor)
                                                            .clipShape(Capsule())
                                                        }
                                                        .buttonStyle(.plain)
                                                    }
                                                }
                                                .padding(.horizontal, 10)
                                                .padding(.vertical, 8)
                                                .frame(width: 215, alignment: .leading)
                                                .background(isSelected ? Color.accentColor.opacity(0.15) : Color(UIColor.tertiarySystemFill))
                                                .overlay(
                                                    RoundedRectangle(cornerRadius: 10, style: .continuous)
                                                        .stroke(isSelected ? Color.accentColor : Color.clear, lineWidth: 1.5)
                                                )
                                                .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
                                            }
                                            .buttonStyle(.plain)
                                        }
                                    }
                                }
                            }
                        }

                        VStack(alignment: .leading, spacing: 5) {
                            HStack {
                                Text(L("1. HuggingFace 仓库地址 (Repo ID)", "1. HuggingFace Repo ID"))
                                    .font(.caption.weight(.bold))
                                Spacer()
                                Button {
                                    dismissIOSKeyboard()
                                    Task { await vm.fetchHFModelDetail(repoId: vm.customRepoIdInput) }
                                } label: {
                                    Label(L("查看模型详情与分片", "Inspect Details & Shards"), systemImage: "doc.text.magnifyingglass")
                                        .font(.caption2.weight(.semibold))
                                }
                                .disabled(vm.customRepoIdInput.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                            }
                            TextField(L("从上方实时热榜点选，或输入 owner/repo", "Pick from live trending above or enter owner/repo"), text: $vm.customRepoIdInput)
                                .textInputAutocapitalization(.never)
                                .autocorrectionDisabled()
                                .submitLabel(.done)
                                .onSubmit { dismissIOSKeyboard() }
                                .font(.subheadline.monospaced())
                                .padding(11)
                                .background(Color(UIColor.tertiarySystemFill))
                                .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
                        }

                        VStack(alignment: .leading, spacing: 5) {
                            Text(L("2. 文件名 / 通配符过滤 (Include Pattern，可选)", "2. Filename / Wildcard Filter (Optional)"))
                                .font(.caption.weight(.bold))
                            TextField(L("留空自动优选；或填 *Q4_K_M*.gguf / *IQ2_XS*.gguf", "Leave blank for auto, or e.g. *Q4_K_M*.gguf"), text: $vm.customIncludePatternInput)
                                .textInputAutocapitalization(.never)
                                .autocorrectionDisabled()
                                .submitLabel(.done)
                                .onSubmit { dismissIOSKeyboard() }
                                .font(.subheadline.monospaced())
                                .padding(11)
                                .background(Color(UIColor.tertiarySystemFill))
                                .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
                            Text(L("支持多通配符逗号分隔；GGUF 仓库会自动附带同目录 mmproj 视觉投影器与 MTP 加速头。", "Supports comma-separated wildcards; GGUF repos automatically include matching mmproj & MTP files."))
                                .font(.caption2)
                                .foregroundColor(.secondary)
                        }

                        HStack(spacing: 10) {
                            VStack(alignment: .leading, spacing: 5) {
                                Text(L("3. 自定义显示名称 (可选)", "3. Display Name (Optional)"))
                                    .font(.caption.weight(.bold))
                                TextField(L("留空默认用仓库名", "Default: repo name"), text: $vm.customDisplayNameInput)
                                    .submitLabel(.done)
                                    .onSubmit { dismissIOSKeyboard() }
                                    .font(.subheadline)
                                    .padding(11)
                                    .background(Color(UIColor.tertiarySystemFill))
                                    .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
                            }

                            VStack(alignment: .leading, spacing: 5) {
                                Text(L("4. 模型类别", "4. Modality"))
                                    .font(.caption.weight(.bold))
                                Picker("", selection: $vm.customModalityHint) {
                                    Text(L("自动识别", "Auto")).tag("auto")
                                    Text(L("对话/视觉 LLM", "LLM / VLM")).tag("llm_vlm")
                                    Text(L("图像生成", "Image")).tag("image")
                                    Text(L("音视频生成", "Video")).tag("video_audio")
                                }
                                .pickerStyle(.menu)
                                .frame(maxWidth: .infinity)
                                .padding(.vertical, 5)
                                .background(Color(UIColor.tertiarySystemFill))
                                .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
                            }
                        }

                        VStack(alignment: .leading, spacing: 6) {
                            HStack {
                                Image(systemName: "key.fill")
                                    .foregroundColor(.orange)
                                    .font(.caption2)
                                Text(L("5. HuggingFace Token (受限/需登录模型必填，自动保存)", "5. HuggingFace Token (Required for Gated/Private Repos)"))
                                    .font(.caption.weight(.bold))
                            }
                            SecureField("hf_xxxxxxxxxxxxxxxxxxxxxxxx", text: $vm.hfToken)
                                .textInputAutocapitalization(.never)
                                .autocorrectionDisabled()
                                .submitLabel(.done)
                                .onSubmit { dismissIOSKeyboard() }
                                .font(.subheadline.monospaced())
                                .padding(11)
                                .background(Color(UIColor.tertiarySystemFill))
                                .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
                            HStack(spacing: 12) {
                                if let tokURL = URL(string: "https://huggingface.co/settings/tokens") {
                                    Link(destination: tokURL) {
                                        Label(L("获取 HF Token", "Get HF Token"), systemImage: "key.horizontal")
                                            .font(.caption2.weight(.semibold))
                                    }
                                }
                                let cleanRepo = vm.customRepoIdInput.trimmingCharacters(in: .whitespacesAndNewlines)
                                let repoPageStr = cleanRepo.contains("/") ? "https://huggingface.co/\(cleanRepo)" : "https://huggingface.co/models?sort=trending"
                                if let repoURL = URL(string: repoPageStr) {
                                    Link(destination: repoURL) {
                                        Label(L("打开模型主页同意协议", "Open Repo & Accept License"), systemImage: "safari")
                                            .font(.caption2.weight(.semibold))
                                    }
                                }
                            }
                        }
                    }
                    .padding(14)
                    .background(Color(UIColor.secondarySystemGroupedBackground))
                    .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))

                    if !vm.customModelBannerMessage.isEmpty {
                        Text(vm.customModelBannerMessage)
                            .font(.caption)
                            .foregroundColor(.secondary)
                            .padding(.horizontal, 4)
                    }

                    VStack(spacing: 10) {
                        Button {
                            dismissIOSKeyboard()
                            Task { await vm.registerCustomHFModel(autoDownload: false) }
                        } label: {
                            HStack {
                                if vm.isRegisteringCustomModel {
                                    ProgressView().tint(.white).padding(.trailing, 4)
                                }
                                Image(systemName: "plus.circle.fill")
                                Text(L("添加到模型中心", "Add to Model Center"))
                                    .fontWeight(.bold)
                            }
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 13)
                            .background(Color.accentColor)
                            .foregroundColor(.white)
                            .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
                        }
                        .disabled(vm.isRegisteringCustomModel)

                        if vm.isConnected {
                            Button {
                                dismissIOSKeyboard()
                                Task { await vm.registerCustomHFModel(autoDownload: true) }
                            } label: {
                                HStack {
                                    Image(systemName: "arrow.down.circle.fill")
                                    Text(L("添加并立即启动 8 线程云端下载", "Add & Start 8-Thread Cloud Download"))
                                        .fontWeight(.semibold)
                                }
                                .frame(maxWidth: .infinity)
                                .padding(.vertical, 12)
                                .background(Color.accentColor.opacity(0.14))
                                .foregroundColor(.accentColor)
                                .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
                            }
                            .disabled(vm.isRegisteringCustomModel)
                        }
                    }

                    if !vm.customModels.isEmpty {
                        VStack(alignment: .leading, spacing: 10) {
                            Text(L("已添加的自定义模型 (\(vm.customModels.count))", "Added Custom Models (\(vm.customModels.count))"))
                                .font(.caption.weight(.bold))
                                .foregroundColor(.secondary)

                            ForEach(vm.customModels) { item in
                                HStack(spacing: 10) {
                                    Image(systemName: item.icon)
                                        .foregroundColor(.accentColor)
                                        .frame(width: 24)
                                    VStack(alignment: .leading, spacing: 2) {
                                        Text(item.name)
                                            .font(.subheadline.weight(.semibold))
                                        Text(item.repoId + (item.includePattern.isEmpty ? "" : " · \(item.includePattern)"))
                                            .font(.caption2.monospaced())
                                            .foregroundColor(.secondary)
                                            .lineLimit(1)
                                    }
                                    Spacer()
                                    Button {
                                        vm.switchSelectedModel(item)
                                        dismiss()
                                    } label: {
                                        Text(L("选用", "Select"))
                                            .font(.caption.weight(.bold))
                                            .padding(.horizontal, 10)
                                            .padding(.vertical, 5)
                                            .background(Color.accentColor.opacity(0.14))
                                            .foregroundColor(.accentColor)
                                            .clipShape(Capsule())
                                    }
                                    .buttonStyle(.plain)

                                    Button(role: .destructive) {
                                        Task { await vm.removeCustomHFModel(item) }
                                    } label: {
                                        Image(systemName: "trash")
                                            .font(.caption)
                                            .foregroundColor(.red)
                                            .padding(6)
                                    }
                                    .buttonStyle(.plain)
                                }
                                .padding(10)
                                .background(Color(UIColor.secondarySystemGroupedBackground))
                                .clipShape(RoundedRectangle(cornerRadius: 11, style: .continuous))
                            }
                        }
                    }
                }
                .padding(16)
            }
            .scrollDismissesKeyboard(.immediately)
            .background(Color(UIColor.systemGroupedBackground))
            .background(IOSKeyboardDismissTapInstaller())
            .navigationTitle(L("自定义 HF 模型", "Custom HF Model"))
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button(L("关闭", "Close")) { dismiss() }
                }
            }
            .task {
                if vm.trendingHFModels.isEmpty {
                    await vm.fetchTrendingHFModels()
                }
            }
            .sheet(isPresented: $vm.showHFModelDetailSheet) {
                HFModelDetailIOSSheet(vm: vm)
            }
        }
    }
}

struct HFModelDetailIOSSheet: View {
    @ObservedObject var vm: IOSStudioViewModel
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 14) {
                    if vm.isLoadingHFModelDetail {
                        VStack(spacing: 12) {
                            ProgressView()
                            Text(L("正在从 HuggingFace 解析模型详情与分片体积...", "Inspecting HuggingFace model metadata & shards..."))
                                .font(.caption)
                                .foregroundColor(.secondary)
                        }
                        .frame(maxWidth: .infinity, minHeight: 220)
                    } else if let d = vm.activeHFModelDetail {
                        VStack(alignment: .leading, spacing: 8) {
                            HStack(spacing: 6) {
                                if d.is_gated {
                                    Image(systemName: "lock.fill")
                                        .foregroundColor(.orange)
                                }
                                Text(d.name)
                                    .font(.headline)
                                if !d.param_label.isEmpty {
                                    Text(d.param_label)
                                        .font(.caption2.weight(.heavy))
                                        .padding(.horizontal, 6)
                                        .padding(.vertical, 2)
                                        .background(Color.purple.opacity(0.16))
                                        .foregroundColor(.purple)
                                        .clipShape(Capsule())
                                }
                            }
                            Text(d.repo_id)
                                .font(.caption.monospaced())
                                .foregroundColor(.secondary)
                            HStack(spacing: 5) {
                                Circle()
                                    .fill(d.deployBadgeColor)
                                    .frame(width: 6, height: 6)
                                Text(d.localizedDeployLabel)
                                    .font(.caption.weight(.bold))
                                    .foregroundColor(d.deployBadgeColor)
                            }
                            Text("Arch: \(d.architecture.isEmpty ? d.pipeline_tag : d.architecture)\(d.context_length > 0 ? " · \(d.context_length / 1024)K" : "")  |  License: \(stripEmojiCharacters(d.license))  |  Likes: \(d.likes)")
                                .font(.caption2)
                                .foregroundColor(.secondary)
                            if let hfURL = URL(string: "https://huggingface.co/\(d.repo_id)") {
                                Link(destination: hfURL) {
                                    Label(L("在浏览器打开 HuggingFace 模型主页", "Open Model Page on HuggingFace"), systemImage: "safari")
                                        .font(.caption.weight(.semibold))
                                }
                            }
                        }
                        .padding(14)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .background(Color(UIColor.secondarySystemGroupedBackground))
                        .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))

                        VStack(alignment: .leading, spacing: 8) {
                            Label(L("权重与量化文件清单 (点击即可选用该文件)", "Weight & Quant Shards (Tap to Select)"), systemImage: "shippingbox.fill")
                                .font(.caption.weight(.bold))
                            if d.weight_files.isEmpty {
                                Text(L("未列出单独的顶层 .gguf/.safetensors 分片，添加后将按完整仓库拉取。", "No top-level .gguf/.safetensors shards listed."))
                                    .font(.caption2)
                                    .foregroundColor(.secondary)
                            } else {
                                ForEach(d.weight_files) { wf in
                                    Button {
                                        vm.customRepoIdInput = d.repo_id
                                        vm.customIncludePatternInput = wf.filename
                                        vm.customDisplayNameInput = d.name
                                        vm.customModalityHint = d.modality
                                        dismiss()
                                    } label: {
                                        HStack {
                                            VStack(alignment: .leading, spacing: 2) {
                                                Text(wf.filename)
                                                    .font(.caption2.monospaced())
                                                    .lineLimit(1)
                                                    .truncationMode(.middle)
                                                Text("\(String(format: "%.2f GB", wf.size_gb)) · \(wf.localizedFit)")
                                                    .font(.caption2.weight(.semibold))
                                                    .foregroundColor(wf.fitColor)
                                            }
                                            Spacer()
                                            Text(L("选用", "Select"))
                                                .font(.caption2.weight(.bold))
                                                .padding(.horizontal, 10)
                                                .padding(.vertical, 5)
                                                .background(Color.accentColor)
                                                .foregroundColor(.white)
                                                .clipShape(Capsule())
                                        }
                                        .padding(10)
                                        .background(Color(UIColor.tertiarySystemFill))
                                        .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
                                    }
                                    .buttonStyle(.plain)
                                }
                            }
                        }
                        .padding(14)
                        .background(Color(UIColor.secondarySystemGroupedBackground))
                        .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))

                        if !d.readme_excerpt.isEmpty {
                            VStack(alignment: .leading, spacing: 6) {
                                Label(L("模型说明摘要 (README)", "README Excerpt"), systemImage: "doc.text.fill")
                                    .font(.caption.weight(.bold))
                                HFMarkdownExcerptIOSView(markdown: d.readme_excerpt)
                            }
                            .padding(14)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .background(Color(UIColor.secondarySystemGroupedBackground))
                            .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
                        }
                    }
                }
                .padding(16)
            }
            .background(Color(UIColor.systemGroupedBackground))
            .navigationTitle(L("模型详情", "Model Details"))
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button(L("关闭", "Close")) { dismiss() }
                }
            }
        }
    }
}

struct HFMarkdownExcerptIOSView: View {
    let markdown: String

    private var blocks: [String] {
        cleanHFReadmeExcerpt(markdown)
            .components(separatedBy: .newlines)
            .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
            .filter { !$0.isEmpty }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 5) {
            ForEach(Array(blocks.enumerated()), id: \.offset) { idx, line in
                if line.hasPrefix("#") {
                    let titleText = line.drop(while: { $0 == "#" || $0 == " " })
                    Text(renderHFInlineMarkdown(String(titleText)))
                        .font(.caption.weight(.bold))
                        .foregroundColor(.primary)
                        .padding(.top, idx == 0 ? 0 : 2)
                } else if idx == 0 && line.count <= 60 && !line.hasSuffix(".") && !line.hasSuffix("。") && !line.hasPrefix("**") {
                    Text(renderHFInlineMarkdown(line))
                        .font(.caption.weight(.bold))
                        .foregroundColor(.primary)
                } else if line.hasPrefix("- ") || line.hasPrefix("* ") || line.hasPrefix("+ ") {
                    let itemText = String(line.dropFirst(2)).trimmingCharacters(in: .whitespaces)
                    HStack(alignment: .firstTextBaseline, spacing: 5) {
                        Text("•")
                            .font(.caption2.weight(.bold))
                            .foregroundColor(.secondary)
                        Text(renderHFInlineMarkdown(itemText))
                            .font(.caption2)
                            .foregroundColor(.secondary)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                } else if line.hasPrefix(">") {
                    let quoteText = String(line.drop(while: { $0 == ">" || $0 == " " }))
                    HStack(alignment: .top, spacing: 6) {
                        RoundedRectangle(cornerRadius: 1.5)
                            .fill(Color.accentColor.opacity(0.45))
                            .frame(width: 2.5)
                        Text(renderHFInlineMarkdown(quoteText))
                            .font(.caption2)
                            .foregroundColor(.secondary)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                } else {
                    Text(renderHFInlineMarkdown(line))
                        .font(.caption2)
                        .foregroundColor(.secondary)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}
