import SwiftUI
import PhotosUI

// MARK: - Tab 1: Multimodal Creation Studio (Video+Audio, Image, Qwen3.8 Chat/API, ComfyUI)

struct CreateTabView: View {
    @ObservedObject var vm: IOSStudioViewModel
    @ObservedObject var langMgr = LanguageManager.shared
    @ObservedObject var kbObserver = IOSKeyboardObserver.shared
    @State private var firstPickerItem: PhotosPickerItem? = nil
    @State private var lastPickerItem: PhotosPickerItem? = nil
    @State private var showAdvancedParams: Bool = false
    @State private var showWeightShards: Bool = false
    @FocusState private var promptFocused: Bool

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                createTopHeaderBar

                ScrollView {
                    VStack(spacing: 14) {
                        modelCarouselStrip
                        vramReadinessCard

                        if vm.activeModelSpec.modality == .comfyUI {
                            comfyStudioSection
                        } else if vm.activeModelSpec.modality == .llmVLM {
                            qwenWorkspaceSection
                        } else {
                            mediaGenerationSection
                        }
                    }
                    .padding(.horizontal, 14)
                    .padding(.vertical, 10)
                }
                .scrollDismissesKeyboard(.immediately)
            }
            .background(Color(UIColor.systemGroupedBackground))
            .toolbar(.hidden, for: .navigationBar)
            .onChange(of: firstPickerItem) { newItem in
                guard let newItem else { return }
                Task {
                    if let data = try? await newItem.loadTransferable(type: Data.self),
                       let img = UIImage(data: data) {
                        vm.firstFrameImage = img
                    }
                }
            }
            .onChange(of: lastPickerItem) { newItem in
                guard let newItem else { return }
                Task {
                    if let data = try? await newItem.loadTransferable(type: Data.self),
                       let img = UIImage(data: data) {
                        vm.lastFrameImage = img
                    }
                }
            }
            .sheet(isPresented: $vm.showAddCustomModelSheet) {
                AddCustomHFModelSheet(vm: vm)
            }
        }
    }

    private func compactGPUTag(from raw: String) -> String {
        let u = raw.uppercased()
        if u.contains("6000") || u.contains("G4") { return "G4" }
        if u.contains("H100") { return "H100" }
        if u.contains("A100") { return "A100" }
        if u.contains("L4") { return "L4" }
        if u.contains("T4") { return "T4" }
        let cleaned = raw.replacingOccurrences(of: "NVIDIA ", with: "").trimmingCharacters(in: .whitespacesAndNewlines)
        return cleaned.isEmpty ? "GPU" : String(cleaned.prefix(10))
    }

    private var createTopHeaderBar: some View {
        HStack(spacing: 8) {
            Text("EasyColab")
                .font(.headline.weight(.bold))
                .lineLimit(1)
                .fixedSize(horizontal: true, vertical: false)

            connectionStatusChip

            Spacer(minLength: 6)

            HStack(spacing: 8) {
                if kbObserver.isVisible || promptFocused {
                    Button {
                        promptFocused = false
                        dismissIOSKeyboard()
                    } label: {
                        HStack(spacing: 4) {
                            Image(systemName: "keyboard.chevron.compact.down")
                                .font(.system(size: 12, weight: .bold))
                            Text(L("收起", "Done"))
                                .font(.caption.weight(.bold))
                        }
                        .foregroundColor(.white)
                        .padding(.horizontal, 10)
                        .frame(height: 28)
                        .background(Color.accentColor)
                        .clipShape(Capsule())
                    }
                    .buttonStyle(.plain)
                }

                Button {
                    vm.maskServerURL.toggle()
                } label: {
                    Image(systemName: vm.maskServerURL ? "eye.slash.fill" : "eye")
                        .font(.system(size: 13, weight: .semibold))
                        .foregroundColor(.primary)
                        .frame(width: 30, height: 28)
                        .background(Color(UIColor.secondarySystemFill))
                        .clipShape(Capsule())
                }
                .buttonStyle(.plain)

                Button {
                    LanguageManager.shared.toggle()
                } label: {
                    Text(langMgr.isEN ? "中文" : "EN")
                        .font(.caption.weight(.bold))
                        .foregroundColor(.primary)
                        .lineLimit(1)
                        .fixedSize(horizontal: true, vertical: false)
                        .padding(.horizontal, 10)
                        .frame(height: 28)
                        .background(Color(UIColor.secondarySystemFill))
                        .clipShape(Capsule())
                }
                .buttonStyle(.plain)
            }
            .fixedSize(horizontal: true, vertical: false)
        }
        .padding(.horizontal, 16)
        .padding(.top, 6)
        .padding(.bottom, 8)
        .background(Color(UIColor.systemGroupedBackground))
    }

    private var connectionStatusChip: some View {
        Button {
            vm.selectedTab = .cloud
        } label: {
            HStack(spacing: 5) {
                Circle()
                    .fill(vm.isConnected ? Color.green : (vm.isWakingColab ? Color.orange : Color.gray))
                    .frame(width: 7, height: 7)
                Text(vm.isConnected
                     ? (vm.vramTotalGB > 0 ? String(format: "%@ · %.0fG", compactGPUTag(from: vm.gpuName), vm.vramFreeGB) : compactGPUTag(from: vm.gpuName))
                     : (vm.isWakingColab ? L("唤醒中...", "Waking...") : L("未连接", "Offline")))
                    .font(.caption.weight(.semibold))
                    .foregroundColor(.primary)
                    .lineLimit(1)
                    .fixedSize(horizontal: true, vertical: false)
            }
            .padding(.horizontal, 10)
            .frame(height: 28)
            .background(Color(UIColor.secondarySystemFill))
            .clipShape(Capsule())
        }
        .buttonStyle(.plain)
    }

    // MARK: Horizontal Model Selector Strip

    private var modelCarouselStrip: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 10) {
                ForEach(vm.allAvailableModels) { spec in
                    let isSelected = vm.selectedModelId == spec.id
                    let isLoaded = vm.loadedModelIds.contains(spec.id) || (spec.modality == .comfyUI && vm.comfyRunning)
                    Button {
                        vm.switchSelectedModel(spec)
                    } label: {
                        HStack(spacing: 8) {
                            Image(systemName: spec.icon)
                                .font(.system(size: 15, weight: .semibold))
                                .foregroundColor(isSelected ? .white : .accentColor)
                            VStack(alignment: .leading, spacing: 1) {
                                HStack(spacing: 4) {
                                    Text(spec.shortTitle)
                                        .font(.caption.weight(.bold))
                                        .foregroundColor(isSelected ? .white : .primary)
                                        .lineLimit(1)
                                    if isLoaded {
                                        Circle()
                                            .fill(isSelected ? Color.white : Color.green)
                                            .frame(width: 6, height: 6)
                                    }
                                }
                                Text(spec.badge)
                                    .font(.system(size: 10))
                                    .foregroundColor(isSelected ? .white.opacity(0.85) : .secondary)
                                    .lineLimit(1)
                            }
                        }
                        .padding(.horizontal, 12)
                        .padding(.vertical, 9)
                        .background(isSelected ? Color.accentColor : Color(UIColor.secondarySystemGroupedBackground))
                        .clipShape(RoundedRectangle(cornerRadius: 13, style: .continuous))
                    }
                    .buttonStyle(.plain)
                    .contextMenu {
                        if spec.isCustom {
                            Button(role: .destructive) {
                                Task { await vm.removeCustomHFModel(spec) }
                            } label: {
                                Label(L("从列表移除该自定义模型", "Remove Custom Model"), systemImage: "trash")
                            }
                        }
                    }
                }

                Button {
                    vm.customModelBannerMessage = ""
                    vm.showAddCustomModelSheet = true
                } label: {
                    HStack(spacing: 6) {
                        Image(systemName: "plus.circle.fill")
                            .font(.system(size: 15, weight: .semibold))
                            .foregroundColor(.accentColor)
                        VStack(alignment: .leading, spacing: 1) {
                            Text(L("+ 自定义模型", "+ Custom HF"))
                                .font(.caption.weight(.bold))
                                .foregroundColor(.primary)
                            Text(L("输入 HF Repo ID", "Import HF Repo"))
                                .font(.system(size: 10))
                                .foregroundColor(.secondary)
                        }
                    }
                    .padding(.horizontal, 12)
                    .padding(.vertical, 9)
                    .background(Color(UIColor.secondarySystemGroupedBackground))
                    .overlay(
                        RoundedRectangle(cornerRadius: 13, style: .continuous)
                            .strokeBorder(Color.accentColor.opacity(0.45), style: StrokeStyle(lineWidth: 1, dash: [4, 3]))
                    )
                    .clipShape(RoundedRectangle(cornerRadius: 13, style: .continuous))
                }
                .buttonStyle(.plain)
            }
            .padding(.horizontal, 2)
        }
    }

    // MARK: Smart Readiness Banner

    @ViewBuilder
    private var vramReadinessCard: some View {
        if !vm.isConnected {
            HStack(spacing: 12) {
                Image(systemName: "bolt.horizontal.icloud.fill")
                    .font(.title3)
                    .foregroundColor(.orange)
                VStack(alignment: .leading, spacing: 2) {
                    Text(L("尚未连接云端 Colab GPU", "Colab Cloud GPU Disconnected"))
                        .font(.subheadline.weight(.semibold))
                    Text(L("支持免开网页一键唤醒 G4 (96GB) 或粘贴链接直连", "1-tap headless G4 (96GB) wake or paste tunnel URL"))
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
                Spacer()
                Button {
                    vm.selectedTab = .cloud
                } label: {
                    Text(L("去唤醒", "Connect"))
                        .font(.caption.weight(.bold))
                        .padding(.horizontal, 12)
                        .padding(.vertical, 7)
                        .background(Color.orange)
                        .foregroundColor(.white)
                        .clipShape(Capsule())
                }
            }
            .padding(13)
            .background(Color(UIColor.secondarySystemGroupedBackground))
            .clipShape(RoundedRectangle(cornerRadius: 15, style: .continuous))
        } else if vm.activeModelSpec.modality != .comfyUI {
            VStack(alignment: .leading, spacing: 10) {
                HStack {
                    VStack(alignment: .leading, spacing: 2) {
                        Text(vm.activeModelSpec.name)
                            .font(.subheadline.weight(.bold))
                        Text(vm.isSelectedModelLoadedInVRAM
                             ? L("已常驻云端 GPU 显存 · 可立即推理", "Resident in GPU VRAM · Ready to generate")
                             : (vm.allDownloaded
                                ? L("权重已就绪 (\(String(format: "%.1f", vm.totalDiskSizeGB)) GB) · 请加载到显存", "Weights on disk (\(String(format: "%.1f", vm.totalDiskSizeGB)) GB) · Load to VRAM")
                                : L("权重进度 \(vm.downloadedCount)/\(vm.totalFileCount) · 云盘自动持久化", "Weights \(vm.downloadedCount)/\(vm.totalFileCount) · Auto-persisted to Drive")))
                            .font(.caption)
                            .foregroundColor(vm.isSelectedModelLoadedInVRAM ? .green : .secondary)
                    }
                    Spacer()
                    if vm.isSelectedModelLoadedInVRAM {
                        Button {
                            Task { await vm.unloadRemoteModelFromVRAM(modelId: vm.selectedModelId) }
                        } label: {
                            Text(L("卸载", "Unload"))
                                .font(.caption.weight(.semibold))
                        }
                        .buttonStyle(.bordered)
                        .controlSize(.small)
                        .disabled(vm.isUnloadingModel || vm.isGenerating)
                    } else if !vm.allDownloaded {
                        Button {
                            Task { await vm.startRemoteDownloadWeights() }
                        } label: {
                            HStack(spacing: 4) {
                                if vm.isDownloadingWeights { ProgressView().scaleEffect(0.7) }
                                Text(vm.isDownloadingWeights ? L("下载中...", "Downloading...") : L("下载权重", "Download"))
                                    .font(.caption.weight(.bold))
                            }
                        }
                        .buttonStyle(.borderedProminent)
                        .controlSize(.small)
                        .disabled(vm.isDownloadingWeights)
                    } else {
                        Button {
                            Task { await vm.loadRemoteModelToVRAM() }
                        } label: {
                            HStack(spacing: 4) {
                                if vm.isLoadingModel { ProgressView().scaleEffect(0.7) }
                                Text(vm.isLoadingModel ? L("装载中...", "Loading...") : L("加载到显存", "Load VRAM"))
                                    .font(.caption.weight(.bold))
                            }
                        }
                        .buttonStyle(.borderedProminent)
                        .tint(.green)
                        .controlSize(.small)
                        .disabled(vm.isLoadingModel)
                    }
                }

                if vm.isDownloadingWeights || vm.isLoadingModel {
                    ProgressView(value: min(1.0, max(0.02, vm.modelTaskProgress)))
                        .tint(.accentColor)
                }

                if vm.selectedModelId == "minimax_h3" || !vm.modelFiles.isEmpty {
                    Divider()
                    HStack(spacing: 8) {
                        if vm.selectedModelId == "minimax_h3" {
                            Text(L("显存调度", "VRAM Offload"))
                                .font(.caption2)
                                .foregroundColor(.secondary)
                            Menu {
                                Button(L("智能磁盘卸载 (稳妥)", "Smart Disk Offload")) { vm.selectedOffload = "disk" }
                                Button(L("G4 176GB 双主干热备 (CPU RAM)", "G4 176GB DDR5 Hot-Standby")) { vm.selectedOffload = "cpu" }
                                Button(L("全显存极速 (96G 推荐)", "Full GPU (96G)")) { vm.selectedOffload = "none" }
                            } label: {
                                HStack(spacing: 4) {
                                    Text(vm.selectedOffload == "none"
                                         ? L("全显存极速 (96G)", "Full GPU (96G)")
                                         : (vm.selectedOffload == "cpu" ? L("G4 内存热备", "DDR5 Standby") : L("智能磁盘卸载", "Disk Offload")))
                                        .font(.caption2.weight(.semibold))
                                    Image(systemName: "chevron.up.chevron.down")
                                        .font(.system(size: 9, weight: .bold))
                                }
                                .foregroundColor(.accentColor)
                                .padding(.horizontal, 8)
                                .padding(.vertical, 4)
                                .background(Color.accentColor.opacity(0.12))
                                .clipShape(Capsule())
                            }
                        }
                        Spacer()
                        Button {
                            withAnimation(.easeInOut(duration: 0.2)) { showWeightShards.toggle() }
                        } label: {
                            HStack(spacing: 3) {
                                Text(L("分片明细 (\(vm.downloadedCount)/\(vm.totalFileCount))", "Shards (\(vm.downloadedCount)/\(vm.totalFileCount))"))
                                    .font(.caption2)
                                Image(systemName: showWeightShards ? "chevron.up" : "chevron.down")
                                    .font(.system(size: 9, weight: .semibold))
                            }
                            .foregroundColor(.secondary)
                        }
                        .buttonStyle(.plain)
                    }

                    if showWeightShards {
                        VStack(alignment: .leading, spacing: 3) {
                            ForEach(vm.modelFiles.prefix(12)) { f in
                                HStack {
                                    Text((f.exists ? "✓ " : "○ ") + (f.name.split(separator: "/").last.map(String.init) ?? f.name))
                                        .font(.system(size: 10, design: .monospaced))
                                        .foregroundColor(f.exists ? .green : .secondary)
                                        .lineLimit(1)
                                    Spacer()
                                    if let d = f.localizedDesc {
                                        Text(d)
                                            .font(.system(size: 10))
                                            .foregroundColor(.secondary)
                                            .lineLimit(1)
                                    }
                                }
                            }
                            if vm.modelFiles.count > 12 {
                                Text(L("… 共 \(vm.modelFiles.count) 个权重分片", "… \(vm.modelFiles.count) weight shards total"))
                                    .font(.system(size: 10))
                                    .foregroundColor(.secondary)
                            }
                        }
                        .padding(.top, 2)
                    }
                }
            }
            .padding(13)
            .background(Color(UIColor.secondarySystemGroupedBackground))
            .clipShape(RoundedRectangle(cornerRadius: 15, style: .continuous))
        }
    }

    // MARK: Video+Audio & Image Generation Section

    private var mediaGenerationSection: some View {
        VStack(spacing: 14) {
            // Mode Picker + Preset Menu
            VStack(alignment: .leading, spacing: 10) {
                HStack {
                    Picker(L("任务模式", "Mode"), selection: $vm.taskModeId) {
                        ForEach(vm.activeModelSpec.modes) { mode in
                            Text(mode.title).tag(mode.id)
                        }
                    }
                    .pickerStyle(.segmented)

                    Menu {
                        ForEach(PRESET_TEMPLATES.filter { $0.category == vm.activeModelSpec.modality }) { tpl in
                            Button(tpl.name) {
                                vm.visualPrompt = tpl.visual
                                if !tpl.soundscape.isEmpty { vm.soundscapePrompt = tpl.soundscape }
                                if !tpl.music.isEmpty { vm.musicPrompt = tpl.music }
                            }
                        }
                    } label: {
                        Image(systemName: "sparkles")
                            .font(.body.weight(.semibold))
                            .padding(8)
                            .background(Color.accentColor.opacity(0.14))
                            .clipShape(RoundedRectangle(cornerRadius: 9, style: .continuous))
                    }
                }

                // Reference Keyframe / Edit Photo Pickers
                if ["fl2va", "i2i_edit"].contains(vm.taskModeId) {
                    HStack(spacing: 10) {
                        photoSlotView(
                            title: vm.taskModeId == "fl2va" ? L("首帧参考图", "Start Frame") : L("参考原图 1", "Source Photo 1"),
                            image: vm.firstFrameImage,
                            selection: $firstPickerItem,
                            onClear: { vm.firstFrameImage = nil; firstPickerItem = nil }
                        )
                        photoSlotView(
                            title: vm.taskModeId == "fl2va" ? L("尾帧参考图 (可选)", "End Frame (Opt)") : L("融合参考图 2 (可选)", "Photo 2 (Opt)"),
                            image: vm.lastFrameImage,
                            selection: $lastPickerItem,
                            onClear: { vm.lastFrameImage = nil; lastPickerItem = nil }
                        )
                    }
                }

                // Visual Prompt
                VStack(alignment: .leading, spacing: 5) {
                    HStack(spacing: 8) {
                        Text(vm.activeModelSpec.modality == .videoAudio ? L("画面与运镜描述 (Visual Prompt)", "Visual & Camera Prompt") : L("画面/修图指令描述", "Image / Edit Prompt"))
                            .font(.caption.weight(.semibold))
                            .foregroundColor(.secondary)
                        Spacer()
                        if !vm.visualPrompt.isEmpty {
                            Button(L("清空", "Clear")) { vm.visualPrompt = "" }
                                .font(.caption2)
                        }
                        if kbObserver.isVisible || promptFocused {
                            Button {
                                promptFocused = false
                                dismissIOSKeyboard()
                            } label: {
                                Label(L("收起键盘", "Done"), systemImage: "keyboard.chevron.compact.down")
                                    .font(.caption2.weight(.bold))
                            }
                        }
                    }
                    TextEditor(text: $vm.visualPrompt)
                        .focused($promptFocused)
                        .frame(minHeight: 96, maxHeight: 150)
                        .padding(8)
                        .scrollContentBackground(.hidden)
                        .background(Color(UIColor.tertiarySystemFill))
                        .clipShape(RoundedRectangle(cornerRadius: 11, style: .continuous))
                        .font(.subheadline)
                }

                // Stereo Audio Prompts for MiniMax-H3
                if vm.activeModelSpec.modality == .videoAudio {
                    VStack(alignment: .leading, spacing: 6) {
                        Text(L("环境音效与对白 (32kHz 立体声)", "Soundscape, SFX & Dialogue"))
                            .font(.caption.weight(.semibold))
                            .foregroundColor(.secondary)
                        TextField(L("例如：雨滴声、列车驶过铁轨声...", "e.g., Raindrops, train wheels clacking..."), text: $vm.soundscapePrompt, axis: .vertical)
                            .lineLimit(2...4)
                            .focused($promptFocused)
                            .padding(9)
                            .background(Color(UIColor.tertiarySystemFill))
                            .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
                            .font(.footnote)

                        Text(L("背景配乐 (Background Music)", "Background Music"))
                            .font(.caption.weight(.semibold))
                            .foregroundColor(.secondary)
                        TextField(L("例如：温暖治愈的钢琴与大提琴...", "e.g., Emotional solo piano and strings..."), text: $vm.musicPrompt, axis: .vertical)
                            .lineLimit(1...3)
                            .focused($promptFocused)
                            .padding(9)
                            .background(Color(UIColor.tertiarySystemFill))
                            .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
                            .font(.footnote)
                    }
                }
            }
            .padding(14)
            .background(Color(UIColor.secondarySystemGroupedBackground))
            .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))

            // Parameters Disclosure Card
            VStack(alignment: .leading, spacing: 10) {
                Button {
                    withAnimation(.easeInOut(duration: 0.2)) { showAdvancedParams.toggle() }
                } label: {
                    HStack {
                        Label(L("画幅与采样参数", "Resolution & Sampling"), systemImage: "slider.horizontal.3")
                            .font(.subheadline.weight(.semibold))
                            .foregroundColor(.primary)
                        Spacer()
                        Text(vm.activeModelSpec.modality == .image ? "\(vm.selectedImageResolution.width)×\(vm.selectedImageResolution.height)" : "\(vm.selectedVideoResolution.width)×\(vm.selectedVideoResolution.height)")
                            .font(.caption.monospacedDigit())
                            .foregroundColor(.secondary)
                        Image(systemName: showAdvancedParams ? "chevron.up" : "chevron.down")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                }
                .buttonStyle(.plain)

                if showAdvancedParams {
                    Divider()
                    if vm.activeModelSpec.modality == .image {
                        HStack(spacing: 8) {
                            Text(L("输出画幅", "Aspect Ratio"))
                                .font(.caption)
                                .lineLimit(1)
                                .fixedSize(horizontal: true, vertical: false)
                            Spacer(minLength: 6)
                            Menu {
                                ForEach(imageResolutions(forModelId: vm.selectedModelId)) { r in
                                    Button {
                                        vm.selectedImageResolution = r
                                    } label: {
                                        if vm.selectedImageResolution.id == r.id {
                                            Label(r.label, systemImage: "checkmark")
                                        } else {
                                            Text(r.label)
                                        }
                                    }
                                }
                            } label: {
                                HStack(spacing: 4) {
                                    Text(vm.selectedImageResolution.label)
                                        .font(.caption.weight(.semibold))
                                        .lineLimit(1)
                                        .minimumScaleFactor(0.82)
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
                    } else {
                        HStack(spacing: 8) {
                            Text(L("视频画幅", "Video Aspect"))
                                .font(.caption)
                                .lineLimit(1)
                                .fixedSize(horizontal: true, vertical: false)
                            Spacer(minLength: 6)
                            Menu {
                                ForEach(VIDEO_RESOLUTIONS) { r in
                                    Button {
                                        vm.selectedVideoResolution = r
                                    } label: {
                                        if vm.selectedVideoResolution.id == r.id {
                                            Label(r.label, systemImage: "checkmark")
                                        } else {
                                            Text(r.label)
                                        }
                                    }
                                }
                            } label: {
                                HStack(spacing: 4) {
                                    Text(vm.selectedVideoResolution.label)
                                        .font(.caption.weight(.semibold))
                                        .lineLimit(1)
                                        .minimumScaleFactor(0.82)
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

                        VStack(alignment: .leading, spacing: 4) {
                            HStack {
                                Text(L("视频帧数 (时长约 \(String(format: "%.1f", vm.numFrames / max(1, vm.fps))) 秒)", "Frames (~\(String(format: "%.1f", vm.numFrames / max(1, vm.fps)))s)"))
                                    .font(.caption)
                                Spacer()
                                Text("\(Int(vm.numFrames)) f").font(.caption.monospacedDigit().weight(.semibold))
                            }
                            Slider(value: $vm.numFrames, in: 76...364, step: 24)
                        }
                    }

                    VStack(alignment: .leading, spacing: 4) {
                        HStack {
                            Text(L("去噪采样步数 (Steps)", "Inference Steps")).font(.caption)
                            Spacer()
                            Text("\(Int(vm.inferenceSteps))").font(.caption.monospacedDigit().weight(.semibold))
                        }
                        Slider(value: $vm.inferenceSteps, in: 4...50, step: 1)
                    }

                    if vm.taskModeId == "i2i_edit" && vm.selectedModelId == "z_image_turbo" {
                        VStack(alignment: .leading, spacing: 4) {
                            HStack {
                                Text(L("重绘幅度 (Denoise)", "Denoising Strength")).font(.caption)
                                Spacer()
                                Text(String(format: "%.2f", vm.denoisingStrength)).font(.caption.monospacedDigit())
                            }
                            Slider(value: $vm.denoisingStrength, in: 0.20...1.0, step: 0.05)
                        }
                    }

                    Stepper(L("连续生成数量: \(vm.batchCount)", "Batch Count: \(vm.batchCount)"), value: $vm.batchCount, in: 1...4)
                        .font(.caption)

                    Toggle(L("随机种子 (Random Seed)", "Randomize Seed"), isOn: $vm.randomizeSeed)
                        .font(.caption)
                }
            }
            .padding(14)
            .background(Color(UIColor.secondarySystemGroupedBackground))
            .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))

            // Primary Generate / Cancel Action Card
            generateActionCard

            // Live Result Stage
            MediaStageCard(vm: vm)
        }
    }

    private var generateActionCard: some View {
        VStack(spacing: 10) {
            if vm.isGenerating {
                VStack(alignment: .leading, spacing: 6) {
                    HStack {
                        ProgressView().scaleEffect(0.85)
                        Text(String(format: "%.0f%% · %@", vm.progressValue * 100, formatDuration(vm.currentJobElapsed, compact: true)))
                            .font(.caption.monospacedDigit().weight(.bold))
                            .foregroundColor(.accentColor)
                        Spacer()
                        Button(role: .destructive) {
                            Task { await vm.cancelCurrentGeneration() }
                        } label: {
                            Label(L("停止生成", "Cancel"), systemImage: "stop.fill")
                                .font(.caption.weight(.bold))
                        }
                        .buttonStyle(.borderedProminent)
                        .tint(.red)
                        .controlSize(.small)
                    }
                    ProgressView(value: vm.progressValue)
                        .tint(.accentColor)
                    Text(vm.statusMessage)
                        .font(.caption2)
                        .foregroundColor(.secondary)
                        .lineLimit(2)
                }
            } else {
                Button {
                    promptFocused = false
                    dismissIOSKeyboard()
                    Task { await vm.startGeneration() }
                } label: {
                    HStack(spacing: 8) {
                        Image(systemName: "sparkles.tv.fill")
                        Text(vm.activeModelSpec.modality == .videoAudio
                             ? L("开始生成有声视频", "Generate Video + Stereo Audio")
                             : L("开始生成高清图像", "Generate HD Image"))
                            .fontWeight(.bold)
                    }
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 14)
                    .background(vm.isSelectedModelLoadedInVRAM ? Color.accentColor : Color.gray.opacity(0.45))
                    .foregroundColor(.white)
                    .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
                }
                Text(vm.statusMessage)
                    .font(.caption2)
                    .foregroundColor(.secondary)
                    .multilineTextAlignment(.center)
                    .lineLimit(2)
            }
        }
        .padding(14)
        .background(Color(UIColor.secondarySystemGroupedBackground))
        .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
    }

    // MARK: Qwen3.8-27B Chat, Vision & Dual-Protocol API Gateway

    private var qwenWorkspaceSection: some View {
        VStack(spacing: 14) {
            Picker(L("模式", "Mode"), selection: $vm.taskModeId) {
                ForEach(vm.activeModelSpec.modes) { m in Text(m.title).tag(m.id) }
            }
            .pickerStyle(.segmented)

            if vm.taskModeId == "api" {
                qwenApiGatewayCard
            } else {
                qwenChatCard
            }
        }
    }

    private var qwenApiGatewayCard: some View {
        let base = vm.normalizedBaseURL.isEmpty ? "https://xxxx.gradio.live" : vm.normalizedBaseURL
        return VStack(alignment: .leading, spacing: 12) {
            HStack {
                Label(L("双协议公网 API 网关", "Dual-Protocol Public API"), systemImage: "network")
                    .font(.headline)
                Spacer()
                Text(L("已处理 \(vm.apiRequestCount) 次", "\(vm.apiRequestCount) reqs"))
                    .font(.caption2.monospacedDigit())
                    .padding(.horizontal, 8)
                    .padding(.vertical, 3)
                    .background(Color.green.opacity(0.15))
                    .foregroundColor(.green)
                    .clipShape(Capsule())
            }

            Toggle(L("启用 Bearer / x-api-key 鉴权保护", "Require API Key Auth"), isOn: $vm.apiKeyEnabled)
                .font(.subheadline)

            if vm.apiKeyEnabled {
                HStack {
                    Text(vm.maskServerURL ? "sk-colab-••••••••••••" : vm.apiAccessKey)
                        .font(.caption.monospaced())
                        .lineLimit(1)
                    Spacer()
                    Button(L("复制 Key", "Copy Key")) {
                        UIPasteboard.general.string = vm.apiAccessKey
                        vm.showToast(L("已复制 API Key", "API Key Copied"))
                    }
                    .buttonStyle(.borderedProminent)
                    .controlSize(.mini)
                    Button(L("重置", "Reset")) { vm.regenerateApiKey() }
                        .buttonStyle(.bordered)
                        .controlSize(.mini)
                }
                .padding(10)
                .background(Color(UIColor.tertiarySystemFill))
                .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
            }

            VStack(alignment: .leading, spacing: 6) {
                Text("OpenAI Base URL: \(vm.maskedURLDisplay(base))/v1")
                    .font(.caption.monospaced())
                Text("Anthropic Base URL: \(vm.maskedURLDisplay(base))")
                    .font(.caption.monospaced())
                Button {
                    UIPasteboard.general.string = "\(base)/v1"
                    vm.showToast(L("已复制 OpenAI Base URL", "Copied OpenAI Base URL"))
                } label: {
                    Label(L("一键复制 OpenAI / Cursor 接口地址", "Copy OpenAI / Cursor Base URL"), systemImage: "doc.on.doc")
                        .font(.caption.weight(.semibold))
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.bordered)
            }
        }
        .padding(14)
        .background(Color(UIColor.secondarySystemGroupedBackground))
        .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
    }

    private var qwenChatCard: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Toggle(L("深度思考 (<think>)", "Thinking CoT"), isOn: $vm.enableThinking)
                    .font(.caption.weight(.semibold))
                Spacer()
                Picker(L("上下文", "Context"), selection: $vm.contextLengthK) {
                    ForEach([16, 32, 64, 128, 256], id: \.self) { k in
                        Text("\(k)K").tag(k)
                    }
                }
                .pickerStyle(.menu)
                .onChange(of: vm.contextLengthK) { _ in
                    Task { await vm.syncContextLengthToColab() }
                }
                if !vm.chatHistory.isEmpty {
                    Button(L("清空对话", "Clear")) { vm.chatHistory.removeAll() }
                        .font(.caption)
                }
            }

            if vm.taskModeId == "vlm" {
                photoSlotView(
                    title: L("选择要解析或反推 Prompt 的照片", "Pick Photo for Vision Analysis"),
                    image: vm.firstFrameImage,
                    selection: $firstPickerItem,
                    onClear: { vm.firstFrameImage = nil; firstPickerItem = nil }
                )
            }

            if vm.chatHistory.isEmpty {
                VStack(spacing: 8) {
                    Text(L("支持最高 256K 上下文、看图反推生视频提示词与代码创作", "Up to 256K context, vision prompt reverse-engineering & coding"))
                        .font(.caption)
                        .foregroundColor(.secondary)
                        .multilineTextAlignment(.center)
                    HStack {
                        ForEach(PRESET_TEMPLATES.filter { $0.category == .llmVLM }) { tpl in
                            Button(tpl.name) {
                                vm.visualPrompt = tpl.visual
                            }
                            .font(.caption2)
                            .buttonStyle(.bordered)
                        }
                    }
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, 16)
            } else {
                VStack(spacing: 10) {
                    ForEach(vm.chatHistory) { turn in
                        VStack(alignment: turn.role == "user" ? .trailing : .leading, spacing: 6) {
                            if !turn.thinking.isEmpty {
                                DisclosureGroup(L("思维链推理过程", "Reasoning Process")) {
                                    Text(turn.thinking)
                                        .font(.caption2)
                                        .foregroundColor(.secondary)
                                        .frame(maxWidth: .infinity, alignment: .leading)
                                        .padding(.top, 4)
                                }
                                .font(.caption.weight(.medium))
                                .padding(9)
                                .background(Color(UIColor.tertiarySystemFill))
                                .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
                            }
                            if !turn.content.isEmpty || turn.role == "user" {
                                Text(turn.content)
                                    .font(.subheadline)
                                    .textSelection(.enabled)
                                    .padding(11)
                                    .background(turn.role == "user" ? Color.accentColor : Color(UIColor.tertiarySystemFill))
                                    .foregroundColor(turn.role == "user" ? .white : .primary)
                                    .clipShape(RoundedRectangle(cornerRadius: 13, style: .continuous))
                            } else if vm.isGenerating {
                                ProgressView().padding(8)
                            }
                        }
                        .frame(maxWidth: .infinity, alignment: turn.role == "user" ? .trailing : .leading)
                    }
                }
            }

            HStack(alignment: .bottom, spacing: 8) {
                TextField(L("输入问题或视觉指令...", "Ask Qwen3.8 or describe vision task..."), text: $vm.visualPrompt, axis: .vertical)
                    .lineLimit(1...5)
                    .focused($promptFocused)
                    .padding(10)
                    .background(Color(UIColor.tertiarySystemFill))
                    .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))

                if vm.isGenerating {
                    Button(role: .destructive) {
                        Task { await vm.cancelCurrentGeneration() }
                    } label: {
                        Image(systemName: "stop.circle.fill")
                            .font(.system(size: 32))
                            .foregroundColor(.red)
                    }
                } else {
                    Button {
                        promptFocused = false
                        dismissIOSKeyboard()
                        Task { await vm.startGeneration() }
                    } label: {
                        Image(systemName: "arrow.up.circle.fill")
                            .font(.system(size: 32))
                            .foregroundColor(vm.isSelectedModelLoadedInVRAM ? .accentColor : .gray)
                    }
                    .disabled(!vm.isSelectedModelLoadedInVRAM)
                }
            }
        }
        .padding(14)
        .background(Color(UIColor.secondarySystemGroupedBackground))
        .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
    }

    // MARK: ComfyUI Cloud Studio Section

    private var comfyStudioSection: some View {
        VStack(spacing: 14) {
            VStack(alignment: .leading, spacing: 10) {
                HStack {
                    Label(L("云端 ComfyUI 节点引擎", "Cloud ComfyUI Engine"), systemImage: "point.3.connected.trianglepath.dotted")
                        .font(.headline)
                    Spacer()
                    Text(vm.comfyRunning ? L("运行中", "Running") : (vm.comfyStarting ? L("部署中", "Starting") : L("未启动", "Stopped")))
                        .font(.caption.weight(.bold))
                        .padding(.horizontal, 8)
                        .padding(.vertical, 3)
                        .background((vm.comfyRunning ? Color.green : Color.secondary).opacity(0.15))
                        .foregroundColor(vm.comfyRunning ? .green : .secondary)
                        .clipShape(Capsule())
                }

                Text(localizeServerText(vm.comfyStatusMessage))
                    .font(.caption)
                    .foregroundColor(.secondary)

                if vm.comfyStarting || vm.comfyDownloadingWeight {
                    ProgressView(value: max(0.05, vm.comfyProgress))
                }

                HStack(spacing: 8) {
                    if vm.comfyRunning && !vm.comfyPublicURL.isEmpty {
                        Button {
                            vm.openComfyCanvas()
                        } label: {
                            Label(L("打开内置全屏画布", "Open Node Canvas"), systemImage: "safari.fill")
                                .font(.caption.weight(.bold))
                                .frame(maxWidth: .infinity)
                        }
                        .buttonStyle(.borderedProminent)

                        Button {
                            Task { await vm.syncRemoteComfyUIToDrive() }
                        } label: {
                            Image(systemName: "icloud.and.arrow.up")
                        }
                        .buttonStyle(.bordered)

                        Button(role: .destructive) {
                            Task { await vm.stopRemoteComfyUI() }
                        } label: {
                            Image(systemName: "stop.fill")
                        }
                        .buttonStyle(.bordered)
                    } else {
                        Button {
                            Task { await vm.startRemoteComfyUI() }
                        } label: {
                            Label(vm.comfyStarting ? L("正在启动 ComfyUI...", "Deploying ComfyUI...") : L("一键拉起云端 ComfyUI", "Deploy Cloud ComfyUI"), systemImage: "play.fill")
                                .font(.subheadline.weight(.bold))
                                .frame(maxWidth: .infinity)
                        }
                        .buttonStyle(.borderedProminent)
                        .disabled(!vm.isConnected || vm.comfyStarting)
                    }
                }
            }
            .padding(14)
            .background(Color(UIColor.secondarySystemGroupedBackground))
            .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))

            // 4 Preset Workflow Packs
            VStack(alignment: .leading, spacing: 10) {
                Text(L("零基础一键预置视频工作流包 (自动存云盘)", "1-Tap Preset Video Workflow Packs"))
                    .font(.subheadline.weight(.bold))
                ForEach(vm.comfyPresetPacks) { pack in
                    VStack(alignment: .leading, spacing: 6) {
                        HStack {
                            Text(pack.localizedTitle)
                                .font(.caption.weight(.bold))
                            Spacer()
                            Text(pack.localizedBadge)
                                .font(.system(size: 10, weight: .semibold))
                                .padding(.horizontal, 6)
                                .padding(.vertical, 2)
                                .background(Color.accentColor.opacity(0.12))
                                .foregroundColor(.accentColor)
                                .clipShape(Capsule())
                        }
                        Text(pack.localizedScenario)
                            .font(.caption2)
                            .foregroundColor(.secondary)
                        HStack {
                            Text(String(format: "%.1f GB · %d/%d", pack.approx_size_gb, pack.installed_models, pack.total_models))
                                .font(.caption2.monospacedDigit())
                                .foregroundColor(.secondary)
                            Spacer()
                            Button {
                                Task { await vm.installComfyPresetPack(pack) }
                            } label: {
                                Text(pack.ready ? L("已就绪 · 重装/更新", "Ready · Reinstall") : L("一键配齐并启动", "Install & Launch"))
                                    .font(.caption.weight(.bold))
                            }
                            .buttonStyle(.borderedProminent)
                            .tint(pack.ready ? .green : .accentColor)
                            .controlSize(.mini)
                            .disabled(!vm.isConnected || vm.comfyDownloadingWeight)
                        }
                    }
                    .padding(11)
                    .background(Color(UIColor.tertiarySystemFill))
                    .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
                }
            }
            .padding(14)
            .background(Color(UIColor.secondarySystemGroupedBackground))
            .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))

            // Pull Cloud ComfyUI Outputs to iPhone
            if !vm.comfyRecentOutputs.isEmpty {
                VStack(alignment: .leading, spacing: 8) {
                    Text(L("云端 ComfyUI 最新成片 (一键拉回手机相册)", "Recent Cloud ComfyUI Outputs"))
                        .font(.subheadline.weight(.bold))
                    ForEach(vm.comfyRecentOutputs) { out in
                        HStack {
                            Image(systemName: out.filename.lowercased().hasSuffix(".mp4") ? "film" : "photo")
                                .foregroundColor(.accentColor)
                            VStack(alignment: .leading, spacing: 1) {
                                Text(out.filename).font(.caption.weight(.medium)).lineLimit(1)
                                if let sz = out.size_mb {
                                    Text(String(format: "%.1f MB", sz)).font(.caption2).foregroundColor(.secondary)
                                }
                            }
                            Spacer()
                            Button {
                                Task { await vm.pullComfyOutputToPhone(out) }
                            } label: {
                                if vm.comfyPullingOutputRelPath == out.rel_path {
                                    ProgressView().scaleEffect(0.75)
                                } else {
                                    Label(L("存手机", "Pull"), systemImage: "arrow.down.circle.fill")
                                        .font(.caption.weight(.semibold))
                                }
                            }
                            .buttonStyle(.borderedProminent)
                            .controlSize(.mini)
                        }
                        .padding(.vertical, 4)
                    }
                }
                .padding(14)
                .background(Color(UIColor.secondarySystemGroupedBackground))
                .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
            }
        }
    }

    private func photoSlotView(
        title: String,
        image: UIImage?,
        selection: Binding<PhotosPickerItem?>,
        onClear: @escaping () -> Void
    ) -> some View {
        VStack(alignment: .leading, spacing: 5) {
            HStack {
                Text(title).font(.caption2.weight(.semibold)).foregroundColor(.secondary).lineLimit(1)
                Spacer()
                if image != nil {
                    Button(role: .destructive, action: onClear) {
                        Image(systemName: "xmark.circle.fill").font(.caption)
                    }
                }
            }
            PhotosPicker(selection: selection, matching: .images) {
                ZStack {
                    RoundedRectangle(cornerRadius: 10, style: .continuous)
                        .fill(Color(UIColor.tertiarySystemFill))
                        .frame(height: 92)
                    if let image {
                        Image(uiImage: image)
                            .resizable()
                            .scaledToFill()
                            .frame(height: 92)
                            .frame(maxWidth: .infinity)
                            .clipped()
                            .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
                    } else {
                        VStack(spacing: 4) {
                            Image(systemName: "photo.badge.plus")
                                .font(.title3)
                                .foregroundColor(.accentColor)
                            Text(L("从相册选择", "Pick Photo"))
                                .font(.caption2)
                                .foregroundColor(.secondary)
                        }
                    }
                }
            }
        }
        .frame(maxWidth: .infinity)
    }
}

