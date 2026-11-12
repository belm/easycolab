import SwiftUI

// MARK: - 4-Step Interactive Onboarding Sheet for iOS / iPadOS

struct IOSOnboardingSheet: View {
    @ObservedObject var vm: IOSStudioViewModel
    @ObservedObject var langMgr = LanguageManager.shared
    @State private var page: Int = 0

    var body: some View {
        NavigationStack {
            VStack(spacing: 18) {
                TabView(selection: $page) {
                    onboardingPage(
                        icon: "bolt.horizontal.icloud.fill",
                        tint: .orange,
                        title: L("1. 随身掌控 96GB 云端算力", "1. 96GB Cloud GPU in Your Pocket"),
                        desc: L("纯 Swift 原生直连 Google Colab G4 (RTX PRO 6000 · 96GB 显存 + 176GB 内存)，无需打开电脑或网页，手机端零发热一键唤醒部署。", "Pure-Swift native connection to Google Colab G4 (96GB VRAM + 176GB RAM) — 1-tap headless wake with zero phone battery drain.")
                    )
                    .tag(0)

                    onboardingPage(
                        icon: "shippingbox.and.arrow.backward.fill",
                        tint: .blue,
                        title: L("2. 四大旗舰开源引擎 & 自定义 HF 导入", "2. 4 Flagship Engines & Custom HF Import"),
                        desc: L("内置 MiniMax-H3 立体声有声视频、MiniMax-H3-Image 4K 直出、Qwen-Image-2.1 与 Z-Image-Turbo 海报修图、Qwen3.8-27B 256K 视觉推理 + API 网关及 ComfyUI 云盘持久化，更支持输入任意 HuggingFace Repo ID 一键导入。", "Built-in MiniMax-H3 stereo audio-video, MiniMax-H3-Image 4K, Qwen-Image-2.1 & Z-Image-Turbo, Qwen3.8-27B 256K vision chat + API, Drive-persisted ComfyUI, plus 1-click custom HuggingFace repo import.")
                    )
                    .tag(1)

                    onboardingPage(
                        icon: "photo.on.rectangle.angled",
                        tint: .green,
                        title: L("3. 自动存相册 & 锁屏断点续传", "3. Auto-Save to Photos & Lock Resilience"),
                        desc: L("生成任务异步运行在云端，渲染期间锁屏或切回微信互不影响；回到 App 自动同步进度并将高清 MP4 / PNG 存入 iPhone 系统相册。", "Jobs run asynchronously in the cloud — lock your screen freely and return anytime to auto-pull finished MP4/PNGs to iPhone Photos.")
                    )
                    .tag(2)

                    onboardingPage(
                        icon: "moon.zzz.fill",
                        tint: .purple,
                        title: L("4. 双重省额度安全护栏", "4. Dual CU Billing Protection"),
                        desc: L("云端内置 30 分钟闲置自动销毁看门狗，即使手机没电关机也绝不空耗 CU；用完更可在「云算力」页一键彻底释放全部实例归零计费。", "Built-in 30-min cloud auto-shutdown watchdog ensures zero wasted CU even if your phone loses signal or battery.")
                    )
                    .tag(3)
                }
                .tabViewStyle(.page(indexDisplayMode: .always))
                .indexViewStyle(.page(backgroundDisplayMode: .always))

                HStack(spacing: 12) {
                    if page < 3 {
                        Button {
                            withAnimation { page += 1 }
                        } label: {
                            Text(L("下一步", "Next"))
                                .fontWeight(.bold)
                                .frame(maxWidth: .infinity)
                                .padding(.vertical, 13)
                                .background(Color.accentColor)
                                .foregroundColor(.white)
                                .clipShape(RoundedRectangle(cornerRadius: 13, style: .continuous))
                        }
                    } else {
                        Button {
                            vm.showOnboardingSheet = false
                            vm.selectedTab = .cloud
                        } label: {
                            Text(L("前往绑定 / 连接云算力", "Go to Cloud GPU Setup"))
                                .fontWeight(.bold)
                                .frame(maxWidth: .infinity)
                                .padding(.vertical, 13)
                                .background(Color.orange)
                                .foregroundColor(.white)
                                .clipShape(RoundedRectangle(cornerRadius: 13, style: .continuous))
                        }
                    }
                }
                .padding(.horizontal, 22)
                .padding(.bottom, 16)
            }
            .navigationTitle("EasyColab iOS")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button(langMgr.isEN ? "中文" : "EN") {
                        LanguageManager.shared.toggle()
                    }
                    .font(.caption.weight(.bold))
                }
                ToolbarItem(placement: .topBarTrailing) {
                    Button(L("跳过", "Skip")) {
                        vm.showOnboardingSheet = false
                    }
                }
            }
        }
    }

    private func onboardingPage(icon: String, tint: Color, title: String, desc: String) -> some View {
        VStack(spacing: 18) {
            Spacer()
            ZStack {
                Circle()
                    .fill(tint.opacity(0.14))
                    .frame(width: 96, height: 96)
                Image(systemName: icon)
                    .font(.system(size: 40, weight: .semibold))
                    .foregroundColor(tint)
            }
            Text(title)
                .font(.title3.weight(.bold))
                .multilineTextAlignment(.center)
            Text(desc)
                .font(.subheadline)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 28)
            Spacer()
        }
    }
}

// MARK: - Root Container & App Entry Point

struct EasyColabIOSRootView: View {
    @StateObject private var vm = IOSStudioViewModel()
    @ObservedObject private var langMgr = LanguageManager.shared
    @ObservedObject private var kbObserver = IOSKeyboardObserver.shared
    @Environment(\.scenePhase) private var scenePhase

    var body: some View {
        ZStack(alignment: .top) {
            TabView(selection: $vm.selectedTab) {
                CreateTabView(vm: vm)
                    .tabItem {
                        Label(L("创作台", "Create"), systemImage: "wand.and.stars")
                    }
                    .tag(AppTab.create)

                CloudGPUTabView(vm: vm)
                    .tabItem {
                        Label(L("云算力", "Cloud GPU"), systemImage: "icloud.and.arrow.up.fill")
                    }
                    .badge(vm.isConnected ? "ON" : nil)
                    .tag(AppTab.cloud)

                GalleryTabView(vm: vm)
                    .tabItem {
                        Label(L("作品库", "Gallery"), systemImage: "photo.stack.fill")
                    }
                    .tag(AppTab.gallery)

                ConsoleAndSettingsTabView(vm: vm)
                    .tabItem {
                        Label(L("终端与设置", "Settings"), systemImage: "terminal.fill")
                    }
                    .tag(AppTab.settings)
            }

            if let toast = vm.toastBanner {
                Text(toast)
                    .font(.caption.weight(.bold))
                    .padding(.horizontal, 16)
                    .padding(.vertical, 9)
                    .background(.ultraThinMaterial)
                    .clipShape(Capsule())
                    .shadow(color: .black.opacity(0.12), radius: 8, y: 4)
                    .padding(.top, 8)
                    .transition(.move(edge: .top).combined(with: .opacity))
                    .animation(.spring(response: 0.32, dampingFraction: 0.8), value: vm.toastBanner)
            }
        }
        .background(IOSKeyboardDismissTapInstaller())
        .onChange(of: vm.selectedTab) { _ in
            dismissIOSKeyboard()
        }
        .sheet(isPresented: $vm.showOnboardingSheet) {
            IOSOnboardingSheet(vm: vm)
        }
        .sheet(item: Binding(
            get: { vm.activeSafariURL.map { IdentifiableURL(url: $0) } },
            set: { if $0 == nil { vm.activeSafariURL = nil } }
        )) { wrapped in
            SafariSheetView(url: wrapped.url)
                .ignoresSafeArea()
        }
        .onOpenURL { incomingURL in
            Task { await vm.handleIncomingOAuthURL(incomingURL) }
        }
        .alert(
            L("云端 AI 数据传输说明", "Cloud AI Data Disclosure"),
            isPresented: $vm.showAIConsentAlert
        ) {
            Button(L("同意并继续", "Agree & Continue")) {
                vm.confirmCloudAIConsent()
            }
            Button(L("取消", "Cancel"), role: .cancel) {}
        } message: {
            Text(L(
                "为完成多模态推理，您输入的提示词与主动选择的参考图片将通过 HTTPS 加密直连发送至您个人连接的 Google Colab 云端 GPU 实例处理。EasyColab 无任何开发者中转服务器，不会收集、存储或向第三方共享您的内容。",
                "To run multimodal inference, your prompts and selected reference photos are sent directly over HTTPS solely to your own connected Google Colab GPU runtime. EasyColab operates zero middleman servers and never collects or shares your data."
            ))
        }
        .onChange(of: scenePhase) { newPhase in
            if newPhase == .active {
                vm.handleSceneBecameActive()
            }
        }
    }
}

@main
struct EasyColabIOSApp: App {
    var body: some Scene {
        WindowGroup {
            EasyColabIOSRootView()
        }
    }
}
