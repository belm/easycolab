import SwiftUI
import AppKit
import AVKit
import UniformTypeIdentifiers
import ObjectiveC.runtime

// MARK: - 新手入门引导与分步使用指南弹窗

extension Notification.Name {
    static let openEasyColabGuide = Notification.Name("EasyColab.OpenOnboardingGuide")
}

private struct GuideStepMeta: Identifiable {
    let id: Int
    let badgeZh: String
    let badgeEn: String
    let titleZh: String
    let titleEn: String
    let subtitleZh: String
    let subtitleEn: String
    let icon: String

    var badge: String { L(badgeZh, badgeEn) }
    var title: String { L(titleZh, titleEn) }
    var subtitle: String { L(subtitleZh, subtitleEn) }
}

private let ONBOARDING_STEPS: [GuideStepMeta] = [
    GuideStepMeta(
        id: 0,
        badgeZh: "第 1 步",
        badgeEn: "Step 1",
        titleZh: "连接云端 96GB 显卡",
        titleEn: "Connect Cloud 96GB GPU",
        subtitleZh: "绑定账号 · 一键唤醒 G4 实例",
        subtitleEn: "Bind Google · 1-Click Wake G4 VM",
        icon: "bolt.horizontal.circle.fill"
    ),
    GuideStepMeta(
        id: 1,
        badgeZh: "第 2 步",
        badgeEn: "Step 2",
        titleZh: "下载与加载开源模型",
        titleEn: "Download & Load Open Models",
        subtitleZh: "云盘永久保存 · 大内存热备共驻",
        subtitleEn: "Drive Persistence · Co-Resident VRAM",
        icon: "square.stack.3d.up.fill"
    ),
    GuideStepMeta(
        id: 2,
        badgeZh: "第 3 步",
        badgeEn: "Step 3",
        titleZh: "四大模式快速上手",
        titleEn: "4 Creative Studio Modes",
        subtitleZh: "有声视频 · ComfyUI · 对话 · 生图",
        subtitleEn: "Video+Audio · ComfyUI · Chat · Image",
        icon: "sparkles.rectangle.stack.fill"
    ),
    GuideStepMeta(
        id: 3,
        badgeZh: "第 4 步",
        badgeEn: "Step 4",
        titleZh: "作品保存与省额度秘籍",
        titleEn: "Output Saving & CU Tips",
        subtitleZh: "自动回传本地 · 防忘关机自动释放",
        subtitleEn: "Auto Local Sync · Idle Auto-Release",
        icon: "checkmark.shield.fill"
    )
]

typealias ColabGuideSheetView = ColabGuideSheet

struct ColabGuideSheet: View {
    @ObservedObject var vm: StudioViewModel
    @ObservedObject private var i18n = LanguageManager.shared
    @Environment(\.dismiss) private var dismiss
    @Environment(\.colorScheme) private var colorScheme
    @State private var currentStep: Int = 0

    private func revealServerNotebookInFinder() {
        let fm = FileManager.default
        if let repo = LocalRuntimePaths.repoRootIfPresent {
            let repoNb = repo.appendingPathComponent("EasyColab_Server.ipynb")
            if fm.fileExists(atPath: repoNb.path) {
                NSWorkspace.shared.activateFileViewerSelecting([repoNb])
                return
            }
        }
        let bundledPath = LocalRuntimePaths.resolveBundledOrRepoFile("EasyColab_Server.ipynb")
        if fm.fileExists(atPath: bundledPath),
           let downloadsDir = fm.urls(for: .downloadsDirectory, in: .userDomainMask).first {
            let dest = downloadsDir.appendingPathComponent("EasyColab_Server.ipynb")
            try? fm.removeItem(at: dest)
            try? fm.copyItem(atPath: bundledPath, toPath: dest.path)
            if fm.fileExists(atPath: dest.path) {
                NSWorkspace.shared.activateFileViewerSelecting([dest])
                return
            }
        }
    }

    private func completeAndClose() {
        UserDefaults.standard.set(true, forKey: "hasSeenOnboardingGuide_v1")
        dismiss()
    }

    private func jumpToModel(_ modelId: String) {
        if let spec = OPEN_MODEL_CATALOG.first(where: { $0.id == modelId }) {
            vm.switchSelectedModel(spec)
        }
        completeAndClose()
    }

    var body: some View {
        let palette = StudioPalette(colorScheme: colorScheme)
        HStack(spacing: 0) {
            // 左侧步骤导航栏
            VStack(alignment: .leading, spacing: 14) {
                HStack(spacing: 9) {
                    ZStack {
                        RoundedRectangle(cornerRadius: 8, style: .continuous)
                            .fill(
                                LinearGradient(
                                    colors: [
                                        Color(red: 0.10, green: 0.28, blue: 0.68),
                                        Color(red: 0.16, green: 0.48, blue: 0.92)
                                    ],
                                    startPoint: .topLeading,
                                    endPoint: .bottomTrailing
                                )
                            )
                        Image(systemName: "sparkles")
                            .font(.system(size: 14, weight: .bold))
                            .foregroundStyle(.white)
                    }
                    .frame(width: 30, height: 30)

                    VStack(alignment: .leading, spacing: 1.5) {
                        Text(L("EasyColab 指南", "EasyColab Guide"))
                            .font(.system(size: 14, weight: .bold, design: .rounded))
                        Text(L("3 分钟零基础快速上手", "Get started in 3 minutes"))
                            .font(.system(size: 11))
                            .foregroundStyle(.secondary)
                    }
                }
                .padding(.bottom, 4)

                VStack(spacing: 7) {
                    ForEach(ONBOARDING_STEPS) { step in
                        let selected = currentStep == step.id
                        Button {
                            withAnimation(.easeInOut(duration: 0.16)) {
                                currentStep = step.id
                            }
                        } label: {
                            HStack(alignment: .center, spacing: 10) {
                                Image(systemName: step.icon)
                                    .font(.system(size: 16, weight: .semibold))
                                    .foregroundStyle(selected ? Color.accentColor : Color.secondary)
                                    .frame(width: 22)

                                VStack(alignment: .leading, spacing: 2) {
                                    Text("\(step.badge) · \(step.title)")
                                        .font(.system(size: 12.5, weight: selected ? .bold : .semibold))
                                        .foregroundStyle(selected ? Color.primary : Color.primary.opacity(0.82))
                                    Text(step.subtitle)
                                        .font(.system(size: 10.5))
                                        .foregroundStyle(.secondary)
                                        .lineLimit(1)
                                }
                                Spacer(minLength: 0)
                            }
                            .padding(.horizontal, 10)
                            .padding(.vertical, 9)
                            .background(
                                RoundedRectangle(cornerRadius: 9, style: .continuous)
                                    .fill(selected ? Color.accentColor.opacity(colorScheme == .dark ? 0.20 : 0.12) : Color.clear)
                            )
                            .overlay(
                                RoundedRectangle(cornerRadius: 9, style: .continuous)
                                    .strokeBorder(selected ? Color.accentColor.opacity(0.45) : Color.clear, lineWidth: 1)
                            )
                            .contentShape(Rectangle())
                        }
                        .buttonStyle(.plain)
                    }
                }

                Spacer()

                // 左下角实时连接体检卡片
                VStack(alignment: .leading, spacing: 7) {
                    Text(L("当前环境状态", "Environment Status"))
                        .font(.system(size: 10.5, weight: .semibold))
                        .foregroundStyle(.secondary)

                    HStack(spacing: 6) {
                        StatusDot(color: vm.cliLoggedIn ? .green : .orange)
                        Text(vm.cliLoggedIn
                             ? L("Google 账号：已绑定", "Google Account: Connected")
                             : L("Google 账号：待绑定", "Google Account: Unbound"))
                            .font(.system(size: 11, weight: .medium))
                    }

                    HStack(spacing: 6) {
                        StatusDot(color: vm.isConnected ? .green : .secondary.opacity(0.5))
                        Text(vm.isConnected
                             ? L("云端算力：\(vm.displayGpuName)", "Cloud GPU: \(vm.displayGpuName)")
                             : L("云端算力：尚未唤醒连接", "Cloud GPU: Not Connected"))
                            .font(.system(size: 11, weight: .medium))
                            .lineLimit(1)
                    }
                }
                .padding(11)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(
                    RoundedRectangle(cornerRadius: 9, style: .continuous)
                        .fill(palette.sidebarCardFill)
                )
                .overlay(
                    RoundedRectangle(cornerRadius: 9, style: .continuous)
                        .strokeBorder(palette.cardBorder, lineWidth: 0.8)
                )
            }
            .padding(18)
            .frame(width: 232)
            .frame(maxHeight: .infinity)
            .background(palette.sidebarBackground)

            Rectangle()
                .fill(palette.splitDivider)
                .frame(width: 1)

            // 右侧主引导内容区
            VStack(alignment: .leading, spacing: 0) {
                // 顶部标题栏
                HStack(alignment: .top) {
                    let meta = ONBOARDING_STEPS[currentStep]
                    VStack(alignment: .leading, spacing: 5) {
                        Text("STEP 0\(currentStep + 1) / 04")
                            .font(.system(size: 10.5, weight: .bold, design: .monospaced))
                            .foregroundStyle(Color.accentColor)
                            .padding(.horizontal, 7)
                            .padding(.vertical, 2.5)
                            .background(Capsule().fill(Color.accentColor.opacity(0.12)))

                        Text(meta.title)
                            .font(.system(size: 20, weight: .bold))
                        Text(meta.subtitle)
                            .font(.system(size: 12.5))
                            .foregroundStyle(.secondary)
                    }
                    Spacer()
                    HStack(spacing: 10) {
                        Button {
                            vm.toggleLanguage()
                        } label: {
                            HStack(spacing: 4) {
                                Image(systemName: "globe")
                                    .font(.system(size: 11, weight: .semibold))
                                Text(i18n.isEN ? "中文" : "EN")
                                    .font(.system(size: 11.5, weight: .semibold))
                            }
                            .foregroundStyle(Color.accentColor)
                            .padding(.horizontal, 9)
                            .padding(.vertical, 4)
                            .background(Capsule().fill(Color.accentColor.opacity(0.12)))
                            .overlay(Capsule().strokeBorder(Color.accentColor.opacity(0.32), lineWidth: 0.8))
                        }
                        .buttonStyle(.plain)
                        .fixedSize()
                        .help(i18n.isEN ? "切换界面为简体中文" : "Switch UI to English")

                        Button {
                            completeAndClose()
                        } label: {
                            Image(systemName: "xmark.circle.fill")
                                .font(.system(size: 18))
                                .foregroundStyle(.secondary.opacity(0.75))
                        }
                        .buttonStyle(.plain)
                        .help(L("关闭引导页", "Close Guide"))
                    }
                }
                .padding(.horizontal, 24)
                .padding(.top, 20)
                .padding(.bottom, 14)

                Divider()

                // 分步核心教程卡片区
                ScrollView {
                    VStack(alignment: .leading, spacing: 12) {
                        switch currentStep {
                        case 0:
                            stepOneConnectView(palette: palette)
                        case 1:
                            stepTwoModelView(palette: palette)
                        case 2:
                            stepThreeWorkflowsView(palette: palette)
                        default:
                            stepFourSafetyView(palette: palette)
                        }
                    }
                    .padding(22)
                }

                Divider()

                // 底部操作栏
                HStack(spacing: 10) {
                    Image(systemName: "info.circle")
                        .font(.system(size: 11.5))
                        .foregroundStyle(.secondary)
                    Text(L(
                        "随时可点击左上角「新手引导」或顶栏「使用指南」再次打开本页",
                        "Reopen anytime via 'Guide' at top-left or 'User Guide' in the top bar"
                    ))
                        .font(.system(size: 11.5))
                        .foregroundStyle(.secondary)
                        .lineLimit(1)

                    Spacer()

                    if currentStep > 0 {
                        Button(L("上一步", "Previous")) {
                            withAnimation(.easeInOut(duration: 0.16)) {
                                currentStep -= 1
                            }
                        }
                        .controlSize(.regular)
                    }

                    if currentStep < ONBOARDING_STEPS.count - 1 {
                        Button(L("下一步", "Next")) {
                            withAnimation(.easeInOut(duration: 0.16)) {
                                currentStep += 1
                            }
                        }
                        .buttonStyle(.borderedProminent)
                        .controlSize(.regular)
                        .keyboardShortcut(.defaultAction)
                    } else {
                        Button(L("开始创作", "Start Creating")) {
                            completeAndClose()
                        }
                        .buttonStyle(.borderedProminent)
                        .controlSize(.regular)
                        .keyboardShortcut(.defaultAction)
                    }
                }
                .padding(.horizontal, 22)
                .padding(.vertical, 13)
                .background(palette.workspaceCardFill)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .background(palette.workspaceCanvas)
        }
        .id(i18n.lang)
        .frame(width: 840, height: 560)
        .onAppear {
            currentStep = max(0, min(ONBOARDING_STEPS.count - 1, vm.guideInitialStep))
            UserDefaults.standard.set(true, forKey: "hasSeenOnboardingGuide_v1")
        }
    }

    // MARK: - Step 1: 连接云端算力

    @ViewBuilder
    private func stepOneConnectView(palette: StudioPalette) -> some View {
        guideInfoCard(
            number: "1",
            title: L("绑定 Google 账号（仅首次需要一次）", "Bind Your Google Account (One-Time Setup)"),
            detail: L(
                "在主界面左侧「Colab 算力实例」卡片点击「绑定」，在弹出的浏览器页面登录开通了 Colab Pro / AI Ultra 的 Google 账号并粘贴授权码。绑定后会自动同步真实剩余 CU 计算单元与 Google Drive 云盘。",
                "In the left 'Colab Compute' card, click 'Bind', sign in with a Google account subscribed to Colab Pro / Pro+ / AI Ultra in your browser, and paste the authorization code. Your real CU balance and Google Drive will sync automatically."
            ),
            palette: palette
        ) {
            if !vm.cliLoggedIn {
                Button {
                    completeAndClose()
                    Task { await vm.startGoogleOAuthLogin() }
                } label: {
                    Label(L("现在去绑定 Google 账号", "Bind Google Account Now"), systemImage: "person.crop.circle.badge.checkmark")
                }
                .buttonStyle(.borderedProminent)
                .controlSize(.small)
            } else {
                Label(L("你的 Google 账号已完成绑定", "Your Google account is connected"), systemImage: "checkmark.circle.fill")
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.green)
            }
        }

        guideInfoCard(
            number: "2",
            title: L("选择 G4 机型并点击「唤醒实例并部署」（免开网页）", "Select G4 & Click 'Wake & Deploy' (Browserless)"),
            detail: L(
                "默认已为你选中性价比最高的 G4 机型（NVIDIA RTX PRO 6000 · 96GB 超大显存 + 176GB 系统内存）。点击蓝色「唤醒实例并部署」按钮后，客户端会自动在云端拉起实例、挂载你的 Google Drive 云盘并完成自动连接，全程约 1～2 分钟。",
                "G4 (NVIDIA RTX PRO 6000 · 96GB VRAM + 176GB System RAM) is pre-selected for maximum price-performance. Click the blue 'Wake & Deploy' button to provision a cloud runtime, mount Google Drive, and connect automatically in ~1–2 minutes."
            ),
            palette: palette
        ) {
            if vm.cliLoggedIn && !vm.isConnected && !vm.isWakingColab {
                Button {
                    completeAndClose()
                    Task { await vm.wakeColabHeadless() }
                } label: {
                    Label(L("立即一键唤醒 G4 并部署", "Wake G4 & Deploy Now"), systemImage: "bolt.fill")
                }
                .buttonStyle(.borderedProminent)
                .controlSize(.small)
            }
        }

        guideInfoCard(
            number: "3",
            title: L("备选方案：通过 Google Colab 网页端手动运行笔记本", "Alternative: Run the Notebook Manually in Google Colab Web"),
            detail: L(
                "若你希望在浏览器里查看原生 Notebook，也可以把同步生成的 EasyColab_Server.ipynb 上传至 Colab 网页运行，再把生成的 https://xxxx.gradio.live 地址粘贴到左侧服务地址栏点击「连接」。",
                "Prefer running a notebook in your browser? Upload EasyColab_Server.ipynb to Google Colab, run the cell, then paste the generated https://xxxx.gradio.live URL into the Server URL field on the left and click 'Connect'."
            ),
            palette: palette
        ) {
            HStack(spacing: 10) {
                Button {
                    revealServerNotebookInFinder()
                } label: {
                    Label(L("导出 / 定位 .ipynb 笔记本", "Reveal .ipynb Notebook"), systemImage: "folder")
                }
                .controlSize(.small)

                Button {
                    if let url = URL(string: "https://colab.research.google.com/") {
                        NSWorkspace.shared.open(url)
                    }
                } label: {
                    Label(L("打开 Google Colab 官网", "Open Google Colab Web"), systemImage: "safari")
                }
                .controlSize(.small)
            }
        }
    }

    // MARK: - Step 2: 下载与加载模型

    @ViewBuilder
    private func stepTwoModelView(palette: StudioPalette) -> some View {
        guideInfoCard(
            number: "1",
            title: L("先点「下载权重」：一次存入 Google Drive，永久免重下", "Step 1 — 'Download Weights': Save Once to Google Drive Forever"),
            detail: L(
                "在左侧「开源模型中心」选中你想用的模型。第一次使用时点击「下载权重」，服务端会以 8 线程极速将模型直接下载进你的 Google Drive 云盘。以后每次重新唤醒新机器，都会秒级识别云盘已有权重，无需重复下载。",
                "Pick a model in 'Open Model Center' on the left. Click 'Download Weights' once — the server downloads shards at 8-thread speed directly into your Google Drive. Future runtimes detect existing Drive weights instantly without re-downloading."
            ),
            palette: palette
        ) { EmptyView() }

        guideInfoCard(
            number: "2",
            title: L("再点「加载到显存」：96GB 显存 + 176GB 内存热备加速", "Step 2 — 'Load to VRAM': 96GB VRAM + 176GB RAM Hot-Standby"),
            detail: L(
                "权重就绪后点击「加载到显存」即可开始生成。在 G4 机型上：\n• MiniMax-H3 原生 BF16 会自动激活「双主干内存热备」，同提示词换种子 0ms 瞬回，换新提示词解析仅需约 10 秒。\n• 支持多模型同时常驻显存（例如同时驻留 Qwen3.8-GGUF 对话与生图/视频模型），也可随时在卡片上点「卸载」单独释放。",
                "Once weights are ready, click 'Load to VRAM':\n• On G4, MiniMax-H3 Native BF16 activates dual-backbone RAM hot-standby — 0ms cache hit when changing seeds and ~10s encoding on new prompts.\n• Multiple models can co-reside in VRAM simultaneously (e.g. Qwen3.8-GGUF chat alongside image/video models) and be unloaded individually anytime."
            ),
            palette: palette
        ) { EmptyView() }

        guideInfoCard(
            number: "3",
            title: L("右侧实时日志与折线图监控", "Live Telemetry Charts & Real-Time Run Logs"),
            detail: L(
                "左下角算力卡片提供显存、系统内存与磁盘折线走势图（点切换按钮可合并/展开三线对比）；右侧独立面板实时滚动下载速率、采样步进度与预计剩余时间。",
                "The left compute card plots live VRAM, System RAM, and Disk curves (toggle between Split and Combined views), while the collapsible right log panel streams live download speeds, sampling steps, and ETA."
            ),
            palette: palette
        ) { EmptyView() }
    }

    // MARK: - Step 3: 四大创作模式快速上手

    @ViewBuilder
    private func stepThreeWorkflowsView(palette: StudioPalette) -> some View {
        guideInfoCard(
            number: "A",
            title: L("MiniMax-H3 · 4～15 秒电影级原生有声视频", "MiniMax-H3 · 4–15s Cinematic Video with Native Stereo Audio"),
            detail: L(
                "支持「文生有声视频」「首帧图生视频」「首尾帧生视频」三种模式。可分别填写画面描述、环境音效与背景配乐（也可点右上角「示例模板」一键填入），下方提供 4s / 5s / 8s / 10s / 12s / 15s 快捷时长按钮，直出带 32kHz 立体声的 MP4 成片。",
                "Supports Text-to-Video+Audio, Image-to-Video, and First/Last Frame modes. Describe visual scenes, soundscapes/dialogue, and music (or insert a preset from 'Templates'), pick 4s–15s duration chips, and render MP4s with 32kHz stereo audio."
            ),
            palette: palette
        ) {
            Button {
                jumpToModel("minimax_h3")
            } label: {
                Label(L("切换至 MiniMax-H3 视频工作台", "Switch to MiniMax-H3 Video Studio"), systemImage: "film.stack")
            }
            .controlSize(.small)
        }

        guideInfoCard(
            number: "B",
            title: L("ComfyUI 节点工作台 · 预置 4 套零基础中文傻瓜工作流", "ComfyUI Node Studio · 4 Turnkey Preset Video Workflow Packs"),
            detail: L(
                "不会连节点也能直接用：切到 ComfyUI -> 点击「一键部署并启动」-> 在下方「预置图生视频 / 首尾帧运镜工作流包」任选万相 Wan2.2 / MiniMax-H3 / LTX-2.3 / 混元 1.5 点「一键配齐」-> 点击打开免费公网画布 -> 左上角「工作流」菜单打开中文模板 -> 上传首尾图片点「运行」即可！所有插件、模型与工作流均自动持久化到云盘。",
                "No node wiring required: switch to ComfyUI -> click 'Start ComfyUI' -> pick Wan2.2 / MiniMax-H3 / LTX-2.3 / Hunyuan 1.5 under Preset Workflow Packs and click '1-Click Install' -> open the fullscreen canvas -> select a template from Workflows -> upload 1–2 images and hit Run! All custom nodes, models, and workflows persist to Google Drive."
            ),
            palette: palette
        ) {
            Button {
                jumpToModel("comfyui_studio")
            } label: {
                Label(L("切换至 ComfyUI 节点工作台", "Switch to ComfyUI Node Studio"), systemImage: "point.3.connected.trianglepath.dotted")
            }
            .controlSize(.small)
        }

        guideInfoCard(
            number: "C",
            title: L("Qwen3.8-27B (GGUF 100 tok/s) · 视觉对话与 Claude/OpenAI 网关", "Qwen3.8-27B (GGUF 100 tok/s) · Vision Chat & Claude/OpenAI API Gateway"),
            detail: L(
                "推荐日常选择 GGUF 量化版（仅占约 21GB 显存，生成高达 100 tok/s，支持最高 256K 上下文与拖入图片反推提示词）。切换到「API 协议网关」标签还可一键复制兼容 OpenAI 与 Anthropic 的公网接口，直接接入 Claude Code 或 Cursor。",
                "Recommended for daily use (~21GB VRAM, up to 100 tok/s, up to 256K context, and drag-and-drop image analysis). Switch to the 'API Gateway' mode card to copy OpenAI `/v1` and Anthropic `/v1/messages` endpoints for Claude Code or Cursor."
            ),
            palette: palette
        ) {
            Button {
                jumpToModel("qwen38_27b_gguf")
            } label: {
                Label(L("切换至 Qwen3.8-GGUF 极速对话与网关", "Switch to Qwen3.8-GGUF Chat & Gateway"), systemImage: "bubble.left.and.bubble.right")
            }
            .controlSize(.small)
        }

        guideInfoCard(
            number: "D",
            title: L("Qwen-Image-2.1 / Z-Image-Turbo · 2K 海报生图与自然语言修图", "Qwen-Image-2.1 / Z-Image-Turbo · 2K Poster Generation & Image Editing"),
            detail: L(
                "支持精准中英文海报排版直出，以及上传 1～2 张参考图用一句话指令改服装、换背景或融合多图主体；Z-Image-Turbo 更支持 8 步秒级出图。",
                "Render crisp bilingual typography posters, or upload 1–2 reference images for natural-language outfit swaps, background replacement, and multi-subject fusion; Z-Image-Turbo delivers sub-second 8-step generation."
            ),
            palette: palette
        ) {
            Button {
                jumpToModel("qwen_image_21")
            } label: {
                Label(L("切换至 Qwen-Image-2.1 图像工作台", "Switch to Qwen-Image-2.1 Image Studio"), systemImage: "paintbrush.pointed")
            }
            .controlSize(.small)
        }
    }

    // MARK: - Step 4: 作品保存与省额度秘籍

    @ViewBuilder
    private func stepFourSafetyView(palette: StudioPalette) -> some View {
        guideInfoCard(
            number: "1",
            title: L("生成作品自动回传 Mac 本地 + 云盘双保险", "Auto-Save Outputs to Local Mac + Google Drive Backup"),
            detail: L(
                "所有生成的 MP4 有声视频和 PNG 高清大图都会自动下载回你的 Mac 本地影片目录（Movies/EasyColab），中间预览区可直接播放或切换历史缩略图；ComfyUI 跑出的视频也能在「极速下权重与回传成片」页一键拉回本地。",
                "Every generated MP4 video and PNG image downloads automatically to your Mac (`~/Movies/EasyColab`) for instant playback and history browsing; ComfyUI renders can also be pulled to your Mac in one click."
            ),
            palette: palette
        ) {
            Button {
                NSWorkspace.shared.open(vm.localSaveDir)
            } label: {
                Label(L("打开 Mac 本地作品输出目录", "Open Local Output Folder"), systemImage: "folder")
            }
            .controlSize(.small)
        }

        guideInfoCard(
            number: "2",
            title: L("开启自动休眠 + 用完点「释放全部实例」立省 CU 额度", "Idle Auto-Sleep + 'Release All Instances' Saves Compute Units"),
            detail: L(
                "Colab 按 GPU 在线时长消耗计算单元（CU）：\n• 左侧「算力额度与自动休眠」默认开启 30 分钟闲置看门狗，长时间离开会自动销毁虚拟机防止忘关机。\n• 当天创作结束时，建议直接点击左侧红色的「释放全部实例」按钮，云端 GPU 立即销毁、计费瞬间归零！",
                "Colab bills Compute Units (CU) while a GPU VM is online:\n• 'Compute Quota & Auto-Sleep' enables a 30-minute idle watchdog by default to auto-terminate forgotten runtimes.\n• When done for the day, click the red 'Release All Instances' button on the left to destroy cloud VMs and stop CU burn immediately!"
            ),
            palette: palette
        ) { EmptyView() }

        guideInfoCard(
            number: "3",
            title: L("免费 Cloudflare 加密公网隧道说明", "Free Encrypted Cloudflare Quick Tunnel"),
            detail: L(
                "ComfyUI 使用的 *.trycloudflare.com 随机公网链接由 Cloudflare 官方免费 Quick Tunnel 提供，0 元免注册、全程 HTTPS 加密，且每次释放 Colab 实例后自动销毁失效，安全省心。",
                "ComfyUI's random `*.trycloudflare.com` URL is powered by Cloudflare's official free Quick Tunnel — zero cost, no signup, end-to-end HTTPS encryption, and automatically invalidated whenever the Colab VM is released."
            ),
            palette: palette
        ) { EmptyView() }
    }

    @ViewBuilder
    private func guideInfoCard<ActionContent: View>(
        number: String,
        title: String,
        detail: String,
        palette: StudioPalette,
        @ViewBuilder action: () -> ActionContent
    ) -> some View {
        HStack(alignment: .top, spacing: 12) {
            Text(number)
                .font(.system(size: 12.5, weight: .bold, design: .rounded))
                .frame(width: 24, height: 24)
                .background(Circle().fill(Color.accentColor))
                .foregroundStyle(.white)
                .padding(.top, 1)

            VStack(alignment: .leading, spacing: 7) {
                Text(title)
                    .font(.system(size: 13.5, weight: .bold))
                    .foregroundStyle(.primary)

                Text(detail)
                    .font(.system(size: 12))
                    .foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
                    .lineSpacing(2.5)

                action()
            }
            Spacer(minLength: 0)
        }
        .padding(14)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            RoundedRectangle(cornerRadius: 10, style: .continuous)
                .fill(palette.workspaceCardFill)
        )
        .overlay(
            RoundedRectangle(cornerRadius: 10, style: .continuous)
                .strokeBorder(palette.cardBorder, lineWidth: 0.8)
        )
    }
}


// MARK: - 自定义 HuggingFace 模型仓库添加弹窗

struct AddCustomHFModelMacSheet: View {
    @ObservedObject var vm: StudioViewModel
    @ObservedObject private var i18n = LanguageManager.shared
    @Environment(\.dismiss) private var dismiss
    @Environment(\.colorScheme) private var colorScheme
    @State private var trendingFilterText: String = ""

    private let trendingTabs: [(id: String, zh: String, en: String)] = [
        ("all", "综合热榜", "Trending"),
        ("gguf", "GGUF 量化", "GGUF"),
        ("llm", "对话 / 视觉", "LLM / VLM"),
        ("image_video", "生图 / 视频", "Image / Video"),
    ]

    private var filteredTrendingModels: [HFTrendingModelItem] {
        let q = trendingFilterText.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        guard !q.isEmpty else { return vm.trendingHFModels }
        return vm.trendingHFModels.filter {
            $0.repo_id.lowercased().contains(q)
                || $0.name.lowercased().contains(q)
                || $0.pipeline_tag.lowercased().contains(q)
        }
    }

    var body: some View {
        let palette = StudioPalette(colorScheme: colorScheme)
        Group {
            if vm.showHFModelDetailOverlay {
                HFModelDetailMacOverlayView(vm: vm)
            } else {
                mainFormView
            }
        }
        .padding(18)
        .frame(width: 640)
        .background(palette.workspaceCardFill)
        .task {
            if vm.trendingHFModels.isEmpty {
                await vm.fetchTrendingHFModels()
            }
        }
    }

    private var mainFormView: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                HStack(spacing: 8) {
                    Image(systemName: "plus.square.on.square")
                        .font(.system(size: 16, weight: .bold))
                        .foregroundStyle(Color.accentColor)
                    VStack(alignment: .leading, spacing: 1) {
                        Text(L("添加自定义 HuggingFace 模型仓库", "Add Custom HuggingFace Repository"))
                            .font(.system(size: 15, weight: .bold))
                        Text(L("实时拉取 HuggingFace 热门趋势模型一键填入，或输入任意 Repo ID；受限/需登录模型请填写 HF Token 并同意协议", "Pick live trending models from HuggingFace or enter any Repo ID; provide HF Token for gated/private repos"))
                            .font(.system(size: 11))
                            .foregroundStyle(.secondary)
                    }
                }
                Spacer()
                Button {
                    dismiss()
                } label: {
                    Image(systemName: "xmark.circle.fill")
                        .font(.system(size: 16))
                        .foregroundStyle(.secondary)
                }
                .buttonStyle(.plain)
            }

            Divider()

            VStack(alignment: .leading, spacing: 7) {
                HStack(spacing: 6) {
                    Image(systemName: "chart.line.uptrend.xyaxis")
                        .foregroundStyle(Color.accentColor)
                        .font(.system(size: 12, weight: .bold))
                    Text(L("HuggingFace 实时热榜与搜索 (含参数量 & Colab 显存部署评估)", "Live HuggingFace Trending & Search (with Params & Colab Fit)"))
                        .font(.system(size: 12, weight: .bold))
                    Spacer()
                    ForEach(trendingTabs, id: \.id) { tab in
                        let isSel = vm.trendingHFCategory == tab.id
                        Button {
                            Task {
                                await vm.fetchTrendingHFModels(
                                    category: tab.id,
                                    searchQuery: trendingFilterText,
                                    forceRefresh: false
                                )
                            }
                        } label: {
                            Text(L(tab.zh, tab.en))
                                .font(.system(size: 10.5, weight: isSel ? .bold : .medium))
                                .padding(.horizontal, 8)
                                .padding(.vertical, 3)
                                .background(
                                    Capsule().fill(isSel ? Color.accentColor : Color.primary.opacity(0.07))
                                )
                                .foregroundStyle(isSel ? Color.white : Color.primary)
                        }
                        .buttonStyle(.plain)
                    }
                    Button {
                        Task {
                            await vm.fetchTrendingHFModels(
                                category: vm.trendingHFCategory,
                                searchQuery: trendingFilterText,
                                forceRefresh: true
                            )
                        }
                    } label: {
                        HStack(spacing: 3) {
                            if vm.isLoadingTrendingHF {
                                ProgressView().controlSize(.mini)
                            } else {
                                Image(systemName: "arrow.clockwise")
                                    .font(.system(size: 10, weight: .bold))
                            }
                            Text(L("刷新", "Refresh"))
                                .font(.system(size: 10.5, weight: .semibold))
                        }
                        .foregroundStyle(Color.accentColor)
                    }
                    .buttonStyle(.plain)
                }

                HStack(spacing: 6) {
                    Image(systemName: "magnifyingglass")
                        .font(.system(size: 11))
                        .foregroundStyle(.secondary)
                    TextField(
                        L("搜索 HuggingFace 模型 (如 Qwen3 GGUF / DeepSeek 9B / Flux)，回车在线检索...", "Search HuggingFace models (e.g. Qwen3 GGUF / DeepSeek 9B), press Return..."),
                        text: $trendingFilterText
                    )
                    .textFieldStyle(.roundedBorder)
                    .font(.system(size: 11.5))
                    .onSubmit {
                        Task {
                            await vm.fetchTrendingHFModels(
                                category: vm.trendingHFCategory,
                                searchQuery: trendingFilterText,
                                forceRefresh: true
                            )
                        }
                    }
                    if !trendingFilterText.isEmpty {
                        Button {
                            trendingFilterText = ""
                            Task {
                                await vm.fetchTrendingHFModels(
                                    category: vm.trendingHFCategory,
                                    searchQuery: "",
                                    forceRefresh: false
                                )
                            }
                        } label: {
                            Image(systemName: "xmark.circle.fill")
                                .font(.system(size: 12))
                                .foregroundStyle(.secondary)
                        }
                        .buttonStyle(.plain)
                    }
                    Button {
                        Task {
                            await vm.fetchTrendingHFModels(
                                category: vm.trendingHFCategory,
                                searchQuery: trendingFilterText,
                                forceRefresh: true
                            )
                        }
                    } label: {
                        Text(L("在线搜索", "Search HF"))
                            .font(.system(size: 11, weight: .semibold))
                    }
                    .controlSize(.small)
                }

                if vm.trendingHFModels.isEmpty {
                    HStack(spacing: 6) {
                        if vm.isLoadingTrendingHF {
                            ProgressView().controlSize(.small)
                            Text(L("正在从 HuggingFace Hub 实时拉取模型及参数量/显存评估...", "Fetching models, parameter counts & Colab VRAM fit from HuggingFace Hub..."))
                                .font(.system(size: 11))
                                .foregroundStyle(.secondary)
                        } else {
                            Text(L("未找到匹配模型，可点击「刷新」或更换搜索词，也可直接在下方输入 Repo ID。", "No matching models found. Click 'Refresh', try another keyword, or enter Repo ID below."))
                                .font(.system(size: 11))
                                .foregroundStyle(.secondary)
                        }
                    }
                    .frame(maxWidth: .infinity, minHeight: 80)
                    .background(RoundedRectangle(cornerRadius: 8).fill(Color.primary.opacity(0.03)))
                } else {
                    ScrollView(.vertical, showsIndicators: true) {
                        LazyVGrid(
                            columns: [
                                GridItem(.flexible(minimum: 250), spacing: 8),
                                GridItem(.flexible(minimum: 250), spacing: 8),
                            ],
                            spacing: 7
                        ) {
                            ForEach(vm.trendingHFModels) { item in
                                let isSel = vm.customRepoInput == item.repo_id
                                Button {
                                    vm.customRepoInput = item.repo_id
                                    vm.customIncludePatternInput = item.suggested_pattern
                                    vm.customDisplayNameInput = item.name
                                    vm.customModalityInput = item.modality
                                } label: {
                                    VStack(alignment: .leading, spacing: 4) {
                                        HStack(spacing: 4) {
                                            if item.is_gated {
                                                Image(systemName: "lock.fill")
                                                    .font(.system(size: 9.5))
                                                    .foregroundStyle(.orange)
                                                    .help(L("受限模型 (Gated Repo)：需填写 HF Token 并同意协议", "Gated repo: requires HF Token & license agreement"))
                                            }
                                            Text(item.name)
                                                .font(.system(size: 11.5, weight: .bold))
                                                .foregroundStyle(.primary)
                                                .lineLimit(1)
                                            Spacer(minLength: 4)
                                            if let pLabel = item.param_label, !pLabel.isEmpty {
                                                Text(pLabel)
                                                    .font(.system(size: 9.5, weight: .heavy, design: .rounded))
                                                    .padding(.horizontal, 5.5)
                                                    .padding(.vertical, 1.5)
                                                    .background(Capsule().fill(Color.purple.opacity(0.16)))
                                                    .foregroundStyle(Color.purple)
                                            }
                                            Text(item.is_gguf ? "GGUF" : item.pipeline_tag)
                                                .font(.system(size: 9, weight: .semibold))
                                                .padding(.horizontal, 5)
                                                .padding(.vertical, 1.5)
                                                .background(Capsule().fill(Color.accentColor.opacity(0.14)))
                                                .foregroundStyle(Color.accentColor)
                                            if item.likes > 0 {
                                                HStack(spacing: 2) {
                                                    Image(systemName: "heart.fill")
                                                        .font(.system(size: 8))
                                                    Text("\(item.likes)")
                                                        .font(.system(size: 9.5, weight: .medium))
                                                }
                                                .foregroundStyle(.secondary)
                                            }
                                        }
                                        Text(item.repo_id)
                                            .font(.system(size: 9.5, design: .monospaced))
                                            .foregroundStyle(.secondary)
                                            .lineLimit(1)
                                            .truncationMode(.middle)
                                        HStack(spacing: 5) {
                                            Circle()
                                                .fill(item.deployBadgeColor)
                                                .frame(width: 6, height: 6)
                                            Text(item.localizedDeployLabel)
                                                .font(.system(size: 9.5, weight: .semibold))
                                                .foregroundStyle(item.deployBadgeColor)
                                                .lineLimit(1)
                                            Spacer(minLength: 2)
                                            Button {
                                                vm.customRepoInput = item.repo_id
                                                vm.customIncludePatternInput = item.suggested_pattern
                                                vm.customDisplayNameInput = item.name
                                                vm.customModalityInput = item.modality
                                                Task { await vm.fetchHFModelDetail(repoId: item.repo_id) }
                                            } label: {
                                                HStack(spacing: 2.5) {
                                                    Image(systemName: "info.circle")
                                                        .font(.system(size: 9.5, weight: .semibold))
                                                    Text(L("详情", "Details"))
                                                        .font(.system(size: 9.5, weight: .semibold))
                                                }
                                                .padding(.horizontal, 6)
                                                .padding(.vertical, 2)
                                                .background(Capsule().fill(Color.accentColor.opacity(0.14)))
                                                .foregroundStyle(Color.accentColor)
                                            }
                                            .buttonStyle(.plain)
                                            if isSel {
                                                Image(systemName: "checkmark.circle.fill")
                                                    .font(.system(size: 11))
                                                    .foregroundStyle(Color.accentColor)
                                            }
                                        }
                                    }
                                    .padding(.horizontal, 10)
                                    .padding(.vertical, 7)
                                    .frame(maxWidth: .infinity, alignment: .leading)
                                    .background(
                                        RoundedRectangle(cornerRadius: 8)
                                            .fill(isSel ? Color.accentColor.opacity(0.14) : Color.primary.opacity(0.045))
                                    )
                                    .overlay(
                                        RoundedRectangle(cornerRadius: 8)
                                            .stroke(isSel ? Color.accentColor : Color.primary.opacity(0.08), lineWidth: isSel ? 1.2 : 1)
                                    )
                                }
                                .buttonStyle(.plain)
                            }
                        }
                        .padding(6)
                    }
                    .frame(height: 185)
                    .background(
                        RoundedRectangle(cornerRadius: 9)
                            .fill(Color.primary.opacity(0.025))
                    )
                    .overlay(
                        RoundedRectangle(cornerRadius: 9)
                            .stroke(Color.primary.opacity(0.07), lineWidth: 1)
                    )
                }
            }

            VStack(alignment: .leading, spacing: 5) {
                HStack {
                    Text(L("1. HuggingFace 仓库地址 (Repo ID 或 URL)", "1. HuggingFace Repo ID or URL"))
                        .font(.system(size: 12, weight: .bold))
                    Spacer()
                    Button {
                        let clean = vm.customRepoInput.trimmingCharacters(in: .whitespacesAndNewlines)
                        guard !clean.isEmpty else { return }
                        Task { await vm.fetchHFModelDetail(repoId: clean) }
                    } label: {
                        HStack(spacing: 3) {
                            Image(systemName: "doc.text.magnifyingglass")
                            Text(L("查看模型详情与分片体积", "Inspect Model Details & Shards"))
                        }
                        .font(.system(size: 10.5, weight: .semibold))
                        .foregroundStyle(Color.accentColor)
                    }
                    .buttonStyle(.plain)
                    .disabled(vm.customRepoInput.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                }
                TextField(
                    L("从上方实时热榜点选，或输入任意 Owner/Repo", "Pick from live trending above or enter any Owner/Repo"),
                    text: $vm.customRepoInput
                )
                .textFieldStyle(.roundedBorder)
                .font(.system(size: 12.5, design: .monospaced))
            }

            VStack(alignment: .leading, spacing: 5) {
                Text(L("2. 文件名 / 通配符过滤 (Include Pattern，可选)", "2. Filename / Wildcard Filter (Include Pattern, Optional)"))
                    .font(.system(size: 12, weight: .bold))
                TextField(
                    L("留空默认智能选择；或填 *Q4_K_M*.gguf, *IQ2_XS*.gguf, *.safetensors", "Blank = auto-select; or *Q4_K_M*.gguf, *IQ2_XS*.gguf, *.safetensors"),
                    text: $vm.customIncludePatternInput
                )
                .textFieldStyle(.roundedBorder)
                .font(.system(size: 12, design: .monospaced))

                HStack(spacing: 6) {
                    ForEach(["*Q4_K_M*.gguf", "*Q8_0*.gguf", "*IQ2_XS*.gguf", "*.safetensors"], id: \.self) { pat in
                        Button {
                            vm.customIncludePatternInput = pat
                        } label: {
                            Text(pat)
                                .font(.system(size: 10.5, weight: .medium, design: .monospaced))
                                .padding(.horizontal, 7)
                                .padding(.vertical, 3)
                                .background(Capsule().fill(Color.primary.opacity(0.06)))
                        }
                        .buttonStyle(.plain)
                    }
                }
            }

            HStack(spacing: 12) {
                VStack(alignment: .leading, spacing: 5) {
                    Text(L("3. 自定义显示名称 (可选)", "3. Display Name (Optional)"))
                        .font(.system(size: 12, weight: .bold))
                    TextField(
                        L("留空自动使用仓库名", "Leave blank to use repo name"),
                        text: $vm.customDisplayNameInput
                    )
                    .textFieldStyle(.roundedBorder)
                    .font(.system(size: 12))
                }
                VStack(alignment: .leading, spacing: 5) {
                    Text(L("4. 模型任务模态", "4. Task Modality"))
                        .font(.system(size: 12, weight: .bold))
                    Picker("", selection: $vm.customModalityInput) {
                        Text(L("自动识别 (推荐)", "Auto-detect")).tag("auto")
                        Text(L("对话 / 视觉 / API (LLM/VLM)", "Chat / Vision / API")).tag("llm_vlm")
                        Text(L("文生图 / 图像编辑 (Image)", "Image Generation")).tag("image")
                        Text(L("音视频生成 (Video+Audio)", "Video + Audio")).tag("video_audio")
                    }
                    .labelsHidden()
                    .frame(width: 210)
                }
            }

            VStack(alignment: .leading, spacing: 5) {
                HStack {
                    Image(systemName: "key.fill")
                        .foregroundStyle(.orange)
                        .font(.system(size: 11))
                    Text(L("5. HuggingFace Token (受限/需登录模型必填，自动保存)", "5. HuggingFace Token (Required for Gated/Private Repos)"))
                        .font(.system(size: 12, weight: .bold))
                    Spacer()
                    Button {
                        if let u = URL(string: "https://huggingface.co/settings/tokens") {
                            NSWorkspace.shared.open(u)
                        }
                    } label: {
                        HStack(spacing: 3) {
                            Image(systemName: "key.horizontal")
                            Text(L("获取 HF Token", "Get HF Token"))
                        }
                        .font(.system(size: 10.5, weight: .semibold))
                        .foregroundStyle(Color.accentColor)
                    }
                    .buttonStyle(.plain)

                    Button {
                        let clean = vm.customRepoInput.trimmingCharacters(in: .whitespacesAndNewlines)
                        let urlStr = clean.contains("/") ? "https://huggingface.co/\(clean)" : "https://huggingface.co/models?sort=trending"
                        if let u = URL(string: urlStr) {
                            NSWorkspace.shared.open(u)
                        }
                    } label: {
                        HStack(spacing: 3) {
                            Image(systemName: "safari")
                            Text(L("打开模型主页同意协议", "Open Repo & Accept License"))
                        }
                        .font(.system(size: 10.5, weight: .semibold))
                        .foregroundStyle(Color.accentColor)
                    }
                    .buttonStyle(.plain)
                }
                SecureField("hf_xxxxxxxxxxxxxxxxxxxxxxxx", text: $vm.hfToken)
                    .textFieldStyle(.roundedBorder)
                    .font(.system(size: 12, design: .monospaced))
            }

            if !vm.customModelErrorMessage.isEmpty {
                HStack(spacing: 6) {
                    Image(systemName: "exclamationmark.triangle.fill")
                        .foregroundStyle(.red)
                    Text(vm.customModelErrorMessage)
                        .font(.system(size: 11.5, weight: .medium))
                        .foregroundStyle(.red)
                }
                .padding(8)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(RoundedRectangle(cornerRadius: 7).fill(Color.red.opacity(0.1)))
            }

            Divider()

            HStack(spacing: 10) {
                Button(L("取消", "Cancel")) {
                    dismiss()
                }
                .controlSize(.large)

                Spacer()

                Button {
                    Task { await vm.registerCustomHFModel(autoDownload: false) }
                } label: {
                    HStack(spacing: 5) {
                        if vm.isRegisteringCustomModel {
                            ProgressView().controlSize(.small)
                        } else {
                            Image(systemName: "plus.circle.fill")
                        }
                        Text(L("添加到模型中心", "Add to Model Center"))
                    }
                }
                .controlSize(.large)
                .disabled(vm.isRegisteringCustomModel || vm.customRepoInput.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)

                if vm.isConnected {
                    Button {
                        Task { await vm.registerCustomHFModel(autoDownload: true) }
                    } label: {
                        HStack(spacing: 5) {
                            Image(systemName: "icloud.and.arrow.down.fill")
                            Text(L("添加并立即并发拉取权重", "Add & Download Weights Now"))
                        }
                    }
                    .buttonStyle(.borderedProminent)
                    .controlSize(.large)
                    .disabled(vm.isRegisteringCustomModel || vm.customRepoInput.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                }
            }
        }
    }
}

struct HFModelDetailMacOverlayView: View {
    @ObservedObject var vm: StudioViewModel

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            if vm.isLoadingHFModelDetail {
                VStack(spacing: 12) {
                    ProgressView()
                    Text(L("正在从 HuggingFace Hub 解析模型详情、张量参数与分片体积...", "Inspecting HuggingFace model metadata, tensor parameters & weight shards..."))
                        .font(.system(size: 12))
                        .foregroundStyle(.secondary)
                    Button(L("返回模型列表", "Back to List")) {
                        vm.showHFModelDetailOverlay = false
                    }
                    .controlSize(.small)
                }
                .frame(maxWidth: .infinity, minHeight: 360)
            } else if let d = vm.activeHFModelDetail {
                HStack(alignment: .top) {
                    VStack(alignment: .leading, spacing: 4) {
                        HStack(spacing: 6) {
                            Button {
                                vm.showHFModelDetailOverlay = false
                            } label: {
                                HStack(spacing: 3) {
                                    Image(systemName: "chevron.left")
                                        .font(.system(size: 11, weight: .bold))
                                    Text(L("返回", "Back"))
                                        .font(.system(size: 11.5, weight: .semibold))
                                }
                                .padding(.horizontal, 8)
                                .padding(.vertical, 3)
                                .background(Capsule().fill(Color.primary.opacity(0.08)))
                            }
                            .buttonStyle(.plain)

                            if d.is_gated {
                                Image(systemName: "lock.fill")
                                    .foregroundStyle(.orange)
                                    .font(.system(size: 12))
                            }
                            Text(d.name)
                                .font(.system(size: 15, weight: .bold))
                                .lineLimit(1)
                            if !d.param_label.isEmpty {
                                Text(d.param_label)
                                    .font(.system(size: 11, weight: .heavy, design: .rounded))
                                    .padding(.horizontal, 7)
                                    .padding(.vertical, 2)
                                    .background(Capsule().fill(Color.purple.opacity(0.16)))
                                    .foregroundStyle(Color.purple)
                            }
                            HStack(spacing: 4) {
                                Circle()
                                    .fill(d.deployBadgeColor)
                                    .frame(width: 6, height: 6)
                                Text(d.localizedDeployLabel)
                                    .font(.system(size: 10.5, weight: .bold))
                            }
                            .padding(.horizontal, 8)
                            .padding(.vertical, 2.5)
                            .background(Capsule().fill(d.deployBadgeColor.opacity(0.14)))
                            .foregroundStyle(d.deployBadgeColor)
                        }

                        HStack(spacing: 10) {
                            Text(d.repo_id)
                            HStack(spacing: 3) {
                                Image(systemName: "heart.fill")
                                    .font(.system(size: 9))
                                Text("\(d.likes)")
                            }
                            HStack(spacing: 3) {
                                Image(systemName: "arrow.down.to.line")
                                    .font(.system(size: 9, weight: .bold))
                                Text("\(d.downloads)")
                            }
                            Text("\(L("更新于", "Updated")) \(d.last_modified.isEmpty ? "-" : d.last_modified)")
                        }
                        .font(.system(size: 11, design: .monospaced))
                        .foregroundStyle(.secondary)
                    }
                    Spacer()
                    Button {
                        if let u = URL(string: "https://huggingface.co/\(d.repo_id)") {
                            NSWorkspace.shared.open(u)
                        }
                    } label: {
                        HStack(spacing: 4) {
                            Image(systemName: "safari")
                            Text(L("打开 HF 主页", "Open on HF"))
                        }
                        .font(.system(size: 11, weight: .semibold))
                    }
                    .controlSize(.small)

                    Button {
                        vm.showHFModelDetailOverlay = false
                    } label: {
                        Image(systemName: "xmark.circle.fill")
                            .font(.system(size: 17))
                            .foregroundStyle(.secondary)
                    }
                    .buttonStyle(.plain)
                }

                Divider()

                HStack(spacing: 8) {
                    detailStatBox(
                        title: L("参数量 / 总存储", "Params / Repo Size"),
                        value: "\(d.param_label.isEmpty ? L("未标注", "N/A") : d.param_label) (\(d.used_storage_gb > 0 ? String(format: "%.1f GB", d.used_storage_gb) : "-"))"
                    )
                    detailStatBox(
                        title: L("模型架构 / 上下文", "Arch / Context"),
                        value: "\(d.architecture.isEmpty ? d.pipeline_tag : d.architecture)\(d.context_length > 0 ? " · \(d.context_length / 1024)K" : "")"
                    )
                    detailStatBox(
                        title: L("开源协议 (License)", "License"),
                        value: stripEmojiCharacters(d.license),
                        leadingIcon: d.is_gated ? "lock.fill" : nil
                    )
                    detailStatBox(
                        title: L("基座模型 (Base)", "Base Model"),
                        value: d.base_model.isEmpty ? L("原生基座", "Base") : (d.base_model.split(separator: "/").last.map(String.init) ?? d.base_model)
                    )
                }

                VStack(alignment: .leading, spacing: 6) {
                    HStack(spacing: 5) {
                        Image(systemName: "shippingbox.fill")
                            .font(.system(size: 11))
                            .foregroundStyle(Color.accentColor)
                        Text(L("权重与量化分片清单 (点击「选用此文件」自动填入过滤规则 · 共 \(d.weight_files.count) 个文件)", "Weight & Quant Shards (Click 'Select' to auto-fill Include Pattern · \(d.weight_files.count) files)"))
                            .font(.system(size: 11.5, weight: .bold))
                    }
                    if d.weight_files.isEmpty {
                        Text(L("该仓库未列出直接的 .gguf / .safetensors 顶层权重文件，添加后将按完整仓库拉取。", "No top-level .gguf / .safetensors files listed; full snapshot will be downloaded."))
                            .font(.system(size: 11))
                            .foregroundStyle(.secondary)
                            .padding(.vertical, 6)
                    } else {
                        ScrollView(.vertical, showsIndicators: true) {
                            VStack(spacing: 4) {
                                ForEach(d.weight_files) { wf in
                                    let isCurPat = vm.customIncludePatternInput == wf.filename
                                    HStack(spacing: 8) {
                                        Text(wf.filename)
                                            .font(.system(size: 10.5, design: .monospaced))
                                            .lineLimit(1)
                                            .truncationMode(.middle)
                                        Spacer()
                                        if wf.size_gb > 0 {
                                            Text(String(format: "%.2f GB", wf.size_gb))
                                                .font(.system(size: 10, weight: .semibold, design: .monospaced))
                                                .foregroundStyle(.secondary)
                                        }
                                        HStack(spacing: 4) {
                                            Circle()
                                                .fill(wf.fitColor)
                                                .frame(width: 6, height: 6)
                                            Text(wf.localizedFit)
                                                .font(.system(size: 9.5, weight: .semibold))
                                                .foregroundStyle(wf.fitColor)
                                        }
                                        Button {
                                            vm.customRepoInput = d.repo_id
                                            vm.customIncludePatternInput = wf.filename
                                            vm.customDisplayNameInput = d.name
                                            vm.customModalityInput = d.modality
                                            vm.showHFModelDetailOverlay = false
                                        } label: {
                                            Text(isCurPat ? L("已选用", "Selected") : L("选用此文件", "Select File"))
                                                .font(.system(size: 10, weight: .bold))
                                                .padding(.horizontal, 8)
                                                .padding(.vertical, 3)
                                                .background(Capsule().fill(Color.accentColor))
                                                .foregroundStyle(.white)
                                        }
                                        .buttonStyle(.plain)
                                    }
                                    .padding(.horizontal, 8)
                                    .padding(.vertical, 5)
                                    .background(RoundedRectangle(cornerRadius: 6).fill(Color.primary.opacity(0.04)))
                                }
                            }
                            .padding(4)
                        }
                        .frame(height: 175)
                        .background(RoundedRectangle(cornerRadius: 8).fill(Color.primary.opacity(0.025)))
                        .overlay(RoundedRectangle(cornerRadius: 8).stroke(Color.primary.opacity(0.07), lineWidth: 1))
                    }
                }

                if !d.readme_excerpt.isEmpty {
                    VStack(alignment: .leading, spacing: 5) {
                        HStack(spacing: 5) {
                            Image(systemName: "doc.text.fill")
                                .font(.system(size: 11))
                                .foregroundStyle(Color.accentColor)
                            Text(L("模型卡说明摘要 (Model Card Excerpt)", "Model Card Excerpt"))
                                .font(.system(size: 11.5, weight: .bold))
                        }
                        ScrollView(.vertical, showsIndicators: true) {
                            HFMarkdownExcerptView(markdown: d.readme_excerpt)
                                .padding(8)
                        }
                        .frame(height: 115)
                        .background(RoundedRectangle(cornerRadius: 8).fill(Color.primary.opacity(0.025)))
                        .overlay(RoundedRectangle(cornerRadius: 8).stroke(Color.primary.opacity(0.07), lineWidth: 1))
                    }
                }

                Divider()

                HStack {
                    Button {
                        vm.showHFModelDetailOverlay = false
                    } label: {
                        HStack(spacing: 4) {
                            Image(systemName: "chevron.left")
                            Text(L("返回配置表单", "Back to Form"))
                        }
                    }
                    .controlSize(.large)

                    Spacer()

                    Button {
                        vm.customRepoInput = d.repo_id
                        if vm.customDisplayNameInput.isEmpty {
                            vm.customDisplayNameInput = d.name
                        }
                        vm.customModalityInput = d.modality
                        vm.showHFModelDetailOverlay = false
                    } label: {
                        HStack(spacing: 5) {
                            Image(systemName: "checkmark.circle.fill")
                            Text(L("选用此模型并返回", "Use This Model"))
                        }
                    }
                    .buttonStyle(.borderedProminent)
                    .controlSize(.large)
                }
            }
        }
    }

    private func detailStatBox(title: String, value: String, leadingIcon: String? = nil) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(title)
                .font(.system(size: 9.5))
                .foregroundStyle(.secondary)
                .lineLimit(1)
            HStack(spacing: 3) {
                if let icon = leadingIcon {
                    Image(systemName: icon)
                        .font(.system(size: 9.5))
                        .foregroundStyle(.orange)
                }
                Text(value)
                    .font(.system(size: 11, weight: .bold))
                    .lineLimit(1)
            }
        }
        .padding(.horizontal, 9)
        .padding(.vertical, 6)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(RoundedRectangle(cornerRadius: 7).fill(Color.primary.opacity(0.045)))
    }
}
