import SwiftUI
import AppKit
import AVKit
import UniformTypeIdentifiers
import ObjectiveC.runtime

// MARK: - 中英文国际化语言管理 (默认简体中文 "zh")

enum AppLanguage: String, CaseIterable {
    case zh = "zh"
    case en = "en"
}

extension Notification.Name {
    static let easyColabLanguageDidChange = Notification.Name("EasyColab.LanguageDidChange")
}

final class LanguageManager: ObservableObject {
    static let shared = LanguageManager()

    @Published var lang: AppLanguage {
        didSet {
            UserDefaults.standard.set(lang.rawValue, forKey: "appLanguage")
            if oldValue != lang {
                NotificationCenter.default.post(name: .easyColabLanguageDidChange, object: nil)
            }
        }
    }

    var isEN: Bool { lang == .en }

    private init() {
        if UserDefaults.standard.string(forKey: "appLanguage") == "en" {
            self.lang = .en
        } else {
            self.lang = .zh
        }
    }

    func toggle() {
        lang = (lang == .zh) ? .en : .zh
    }
}

@inline(__always)
func L(_ zh: String, _ en: String) -> String {
    LanguageManager.shared.lang == .en ? en : zh
}

func localizeModelFileDesc(_ raw: String) -> String {
    guard LanguageManager.shared.isEN, !raw.isEmpty else { return raw }
    var s = raw
    s = s.replacingOccurrences(of: " [RAM内存盘]", with: " [RAM Disk]")
    s = s.replacingOccurrences(of: "DiT 音视频主干 BF16", with: "DiT Audio-Video Backbone BF16")
    s = s.replacingOccurrences(of: "多模态编码器 BF16", with: "Multimodal Encoder BF16")
    s = s.replacingOccurrences(of: "3D 视频 VAE BF16", with: "3D Video VAE BF16")
    s = s.replacingOccurrences(of: "32kHz 立体声 VAE BF16", with: "32kHz Stereo Audio VAE BF16")
    s = s.replacingOccurrences(of: "权重分片", with: "Weight Shard")
    s = s.replacingOccurrences(of: "Unsloth UD-Q4_K_M 主模型", with: "Unsloth UD-Q4_K_M Main Model")
    s = s.replacingOccurrences(of: "多模态视觉投影器", with: "Multimodal Vision Projector")
    s = s.replacingOccurrences(of: "Unsloth MTP 多词元投机解码头", with: "Unsloth MTP Speculative Decoding Head")
    s = s.replacingOccurrences(of: "编码器", with: "Encoder")
    s = s.replacingOccurrences(of: "图像 VAE", with: "Image VAE")
    return s
}

func localizeServerText(_ text: String) -> String {
    guard LanguageManager.shared.isEN, !text.isEmpty else { return text }

    let exactMap: [String: String] = [
        "未加载": "Not Loaded",
        "未连接 Colab 服务端": "Colab Server Disconnected",
        "尚未启动云端 ComfyUI 工作台": "Cloud ComfyUI Studio Not Started",
        "尚未启动（支持一键拉起 ComfyUI + Google Drive 自动软链持久化）": "Not started (1-click ComfyUI + Google Drive auto-symlink persistence ready)",
        "Google Drive 自动软链持久化": "Google Drive Auto-Symlink Persistence",
        "Google Drive 实时软链挂载": "Google Drive Live Symlink Mount",
        "Google Drive 云盘自动持久化": "Google Drive Auto-Persistence",
        "实例本地高速存储": "Instance Local NVMe Storage",
        "就绪：默认已选 G4 (RTX PRO 6000 · 96GB)，可在左侧一键唤醒实例并部署模型。": "Ready: G4 (RTX PRO 6000 · 96GB) selected by default. Wake & deploy from the left sidebar.",
        "已彻底释放全部云端实例，计费速率归零。": "All cloud Colab instances terminated. Billing rate is now 0 CU/h.",
        "正在初始化 ComfyUI 环境与 Google Drive 持久化目录...": "Initializing ComfyUI environment & Google Drive persistence folders...",
        "正在释放现有常驻模型显存，为 ComfyUI 腾出完整 96GB 空间...": "Releasing resident models from VRAM to free full 96GB for ComfyUI...",
        "正在从 Google Drive 恢复历史持久化的 ComfyUI 节点、模型与工作流...": "Restoring persisted ComfyUI nodes, models & workflows from Google Drive...",
        "正在克隆官方最新 ComfyUI 核心引擎...": "Cloning latest official ComfyUI core engine...",
        "正在安装 ComfyUI 核心依赖（保留当前 G4 Blackwell CUDA PyTorch）...": "Installing ComfyUI core dependencies (preserving G4 Blackwell CUDA PyTorch)...",
        "正在恢复已持久化的自定义节点并配置 ComfyUI-Manager...": "Restoring persisted custom nodes & configuring ComfyUI-Manager...",
        "正在检查并安装已保存自定义节点的 Python 依赖包...": "Checking & installing Python packages for saved custom nodes...",
        "正在拉起 ComfyUI 节点推理引擎 (端口 8188)...": "Starting ComfyUI node inference engine (Port 8188)...",
        "ComfyUI 内核已就绪，正在建立 Cloudflare 高速全屏画布隧道...": "ComfyUI engine ready. Opening Cloudflare Quick Tunnel for fullscreen canvas...",
        "ComfyUI 已停止（节点、模型与工作流已持久化保存至 Google Drive）": "ComfyUI stopped (nodes, models & workflows persisted to Google Drive)",
        "正在先从 Google Drive 检查已持久化的历史模型权重...": "Checking Google Drive for previously persisted model weights...",
        "正在将配齐的模型与中文工作流持久化同步至 Google Drive...": "Syncing installed models & workflow templates to Google Drive...",
        "正在预装并校验 llama.cpp CUDA 高速推理引擎...": "Installing & verifying llama.cpp CUDA inference engine...",
        "正在映射 MiniMax-H3 BF16 多模态编码器权重 (14 分片)...": "Mapping MiniMax-H3 BF16 multimodal encoder weights (14 shards)...",
        "正在映射 MiniMax-H3 BF16 33B DiT 主干权重 (13 分片)...": "Mapping MiniMax-H3 BF16 33B DiT backbone weights (13 shards)...",
        "正在映射 3D 视频 VAE 与 32kHz 立体声 VAE 权重...": "Mapping 3D Video VAE & 32kHz Stereo Audio VAE weights...",
        "正在构建 MiniMax-H3 BF16 原生 GPU 计算图与 Processor...": "Building MiniMax-H3 native BF16 GPU computation graph & processor...",
        "正在映射 Qwen-Image-2.1 权重并构建 GPU 管线...": "Mapping Qwen-Image-2.1 weights & building GPU pipeline...",
        "正在映射 Z-Image-Turbo 权重并构建 8 步极速生图管线...": "Mapping Z-Image-Turbo weights & building 8-step turbo pipeline...",
        "正在预热 Qwen3.8-27B-UD-Q4_K_M.gguf 与 mmproj 视觉权重...": "Warming up Qwen3.8-27B-UD-Q4_K_M.gguf & mmproj vision weights...",
        "正在自动补齐 Unsloth MTP 投机解码加速头 (1.31 GB)...": "Downloading Unsloth MTP speculative decoding head (1.31 GB)...",
        "正在上传最新多模型开源服务端代码 (app.py)...": "Uploading latest multi-model server engine (app.py)...",
        "正在云端配置 Google Drive 持久化、多模型引擎并启动隧道 (约需 40~90 秒)...": "Configuring Google Drive persistence, multi-model engine & public tunnel (~40–90s)...",
        "正在克隆 DiffSynth-Studio...": "Cloning DiffSynth-Studio...",
        "容器仍在初始化，继续尝试连接内核...": "Container still initializing, retrying kernel connection...",
        "旧实例已失效或正在销毁，正在自动清理并重新分配新实例...": "Previous runtime expired; cleaning up and provisioning a fresh GPU instance...",
        "已手动停止当前推理任务": "Inference cancelled by user",
        "首尾帧模式下请至少提供首帧或尾帧图片": "Please provide at least a start frame or end frame image in First/Last Frame mode",
        "图像编辑/重绘模式下请至少拖入一张输入图片": "Please drop at least one reference image in Image Edit / Restyle mode"
    ]
    if let exact = exactMap[text] {
        return exact
    }

    var s = localizeModelFileDesc(text)
    let replacements: [(String, String)] = [
        ("已无缝接管在线 ComfyUI 画布", "Connected to active ComfyUI canvas"),
        ("ComfyUI 进程已退出", "ComfyUI process exited"),
        ("，可点击重新启动", "; click to restart"),
        ("正在建立 ", "Linking "),
        (" 目录软链", " symlinks"),
        ("正在准备配齐「", "Preparing preset pack \""),
        ("正在生成「", "Generating workflow templates for \""),
        ("」全中文三步傻瓜注释工作流...", "\"..."),
        ("」（共 ", "\" ("),
        (" 个官方权重）...", " official weights)..."),
        ("正在 8 线程极速下载 ", "8-thread fast downloading "),
        ("正在 8 线程并发下载 ", "8-thread downloading "),
        ("正在下载 ", "Downloading "),
        (" 至 models/", " to models/"),
        (" 已就绪 (", " ready ("),
        (")，跳过下载", "), skipping"),
        ("正在为 ", "Starting 8-stream parallel download for "),
        (" 启动 8 路并发 HTTP Range 极速下载通道...", "..."),
        ("正在获取 ", "Fetching tokenizer & processor configs for "),
        (" 的分词器与 Processor 配置文件...", "..."),
        ("正在评估显存余量并装载 ", "Checking VRAM & loading "),
        (" 至 GPU...", " into GPU..."),
        ("[显存常驻加速] 正在将子模块 ", "[VRAM Pinning] Warming up submodule "),
        (" 预热锁入 GPU 显存...", " in GPU VRAM..."),
        (" 正在编码多模态上下文并启动推理...", " encoding multimodal context & starting inference..."),
        (" 推理完成！耗时 ", " inference complete! Elapsed "),
        (" 正在使用多模态编码器解析提示词", " encoding prompts with multimodal encoder"),
        ("DiT 采样已完成，正在执行", "DiT sampling finished, running "),
        ("3D 视频 VAE 解码", "3D Video VAE decoding"),
        ("视频帧解码完成，正在执行 32kHz 立体声音轨解码", "Video frames decoded, decoding 32kHz stereo audio"),
        (" 正在执行去噪采样第 ", " denoising step "),
        (" 步 (", " ("),
        ("VAE 解码完成，正在合成 32kHz 立体声音轨并封装 MP4", "VAE decoded, muxing 32kHz stereo audio into MP4"),
        ("正在写入无损 PNG 图像文件", "Writing lossless PNG image"),
        ("正在等待上一任务释放 GPU 显存锁...", "Waiting for previous job to release GPU lock..."),
        ("生成完成！耗时 ", "Generation complete! Elapsed "),
        ("生成出错: ", "Generation error: "),
        ("尚未加载至 Colab GPU 显存，请先在 Mac 客户端点击「加载到显存」。", "is not loaded in Colab GPU VRAM. Click 'Load to VRAM' in the Mac app first."),
        ("尚未加载到 GPU 显存！请先在左侧点击「加载到显存」（显存充裕时可与现有模型同时常驻）。", "is not loaded in GPU VRAM! Click 'Load to VRAM' on the left first (can co-reside with loaded models)."),
        ("尚未加载至 GPU 显存！请先在左侧点击「加载到显存」。", "is not loaded in GPU VRAM! Click 'Load to VRAM' on the left first."),
        ("尚未加载到显存", "is not loaded in VRAM"),
        ("当前已常驻：", "currently resident: "),
        ("请点击左侧「加载到显存」，显存充裕时可同时常驻无需卸载现有模型。", "Click 'Load to VRAM' on the left (can co-reside when VRAM permits)."),
        ("当前已分配实例型号为 ", "Current assigned instance is "),
        ("，正在释放并切换为您选择的 ", "; releasing and switching to "),
        ("正在检查已有实例 ", "Checking existing runtime "),
        (" 连通性...", " connectivity..."),
        ("已通过 Google OAuth 自动挂载 Google Drive", "Mounted Google Drive automatically via Google OAuth"),
        ("启动超时，日志尾部: ", "Startup timed out, log tail: "),
        ("Google Drive 实时软链挂载", "Google Drive Live Symlink"),
        ("Google Drive 云盘自动持久化", "Google Drive Auto-Persist"),
        ("实例本地高速存储", "Local NVMe Storage")
    ]
    for (zhSub, enSub) in replacements {
        if s.contains(zhSub) {
            s = s.replacingOccurrences(of: zhSub, with: enSub)
        }
    }
    return s
}

func localizeConsoleLine(_ line: String) -> String {
    guard LanguageManager.shared.isEN, !line.isEmpty else { return line }
    if line.contains("实时下载/采样进度流") {
        return line.replacingOccurrences(of: "实时下载/采样进度流", with: "Live Download / Sampling Progress")
    }
    return localizeServerText(line)
}


func stripEmojiCharacters(_ text: String) -> String {
    stripEmoji(text)
}

func cleanHFReadmeExcerpt(_ rawMd: String) -> String {
    var body = rawMd
    if body.hasPrefix("---"),
       let rEnd = body.range(of: "\n---", range: body.index(body.startIndex, offsetBy: 3)..<body.endIndex) {
        body = String(body[rEnd.upperBound...])
    }
    // Remove HTML comments and multi-line anchor/image badge blocks
    body = body.replacingOccurrences(of: "<!--[\\s\\S]*?-->", with: "", options: .regularExpression)
    body = body.replacingOccurrences(of: "<a[^>]*>\\s*<img[^>]*>\\s*</a>", with: "", options: [.regularExpression, .caseInsensitive])
    body = body.replacingOccurrences(of: "<img[^>]*>", with: "", options: [.regularExpression, .caseInsensitive])
    body = body.replacingOccurrences(of: "<h[1-4][^>]*>(.*?)</h[1-4]>", with: "\n### $1\n", options: [.regularExpression, .caseInsensitive])
    body = body.replacingOccurrences(of: "<[^>]+>", with: "", options: .regularExpression)
    body = body.replacingOccurrences(of: "\\[!\\[[^\\]]*\\]\\([^\\)]*\\)\\]\\([^\\)]*\\)", with: "", options: .regularExpression)
    body = body.replacingOccurrences(of: "!\\[[^\\]]*\\]\\([^\\)]*\\)", with: "", options: .regularExpression)
    body = body.replacingOccurrences(of: "&nbsp;", with: " ")
        .replacingOccurrences(of: "&amp;", with: "&")
        .replacingOccurrences(of: "&lt;", with: "<")
        .replacingOccurrences(of: "&gt;", with: ">")
        .replacingOccurrences(of: "&quot;", with: "\"")

    var cleanLines: [String] = []
    var totalChars = 0
    for ln in body.components(separatedBy: .newlines) {
        let s = ln.trimmingCharacters(in: .whitespacesAndNewlines)
        if s.isEmpty || s.hasPrefix("```") || s.hasPrefix("|---") || s.hasPrefix("| ---") {
            continue
        }
        cleanLines.append(s)
        totalChars += s.count + 1
        if totalChars >= 1400 { break }
    }
    var joined = cleanLines.joined(separator: "\n")
    joined = joined.replacingOccurrences(of: "\\[([^\\]]+)\\]\\([^\\)\\n]*$", with: "$1", options: .regularExpression)
    return joined
}

func renderHFInlineMarkdown(_ raw: String) -> AttributedString {
    var cleaned = raw.trimmingCharacters(in: .whitespacesAndNewlines)
    cleaned = cleaned.replacingOccurrences(of: "\\[([^\\]]+)\\]\\([^\\)\\n]*$", with: "$1", options: .regularExpression)
    let oddBold = cleaned.components(separatedBy: "**").count - 1
    if oddBold % 2 != 0, let lastRange = cleaned.range(of: "**", options: .backwards) {
        cleaned.removeSubrange(lastRange)
    }
    if let attr = try? AttributedString(
        markdown: cleaned,
        options: AttributedString.MarkdownParsingOptions(
            allowsExtendedAttributes: true,
            interpretedSyntax: .inlineOnlyPreservingWhitespace,
            failurePolicy: .returnPartiallyParsedIfPossible
        )
    ) {
        return attr
    }
    var plain = cleaned
    plain = plain.replacingOccurrences(of: "\\[([^\\]]+)\\]\\(([^\\)]+)\\)", with: "$1", options: .regularExpression)
    plain = plain.replacingOccurrences(of: "**", with: "")
    plain = plain.replacingOccurrences(of: "__", with: "")
    plain = plain.replacingOccurrences(of: "`", with: "")
    return AttributedString(plain)
}

struct HFMarkdownExcerptView: View {
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
                        .font(.system(size: 11.5, weight: .bold))
                        .foregroundStyle(.primary)
                        .padding(.top, idx == 0 ? 0 : 3)
                } else if idx == 0 && line.count <= 60 && !line.hasSuffix(".") && !line.hasSuffix("。") && !line.hasPrefix("**") {
                    Text(renderHFInlineMarkdown(line))
                        .font(.system(size: 11.5, weight: .bold))
                        .foregroundStyle(.primary)
                } else if line.hasPrefix("- ") || line.hasPrefix("* ") || line.hasPrefix("+ ") {
                    let itemText = String(line.dropFirst(2)).trimmingCharacters(in: .whitespaces)
                    HStack(alignment: .firstTextBaseline, spacing: 5) {
                        Text("•")
                            .font(.system(size: 10.5, weight: .bold))
                            .foregroundStyle(.secondary)
                        Text(renderHFInlineMarkdown(itemText))
                            .font(.system(size: 10.5))
                            .foregroundStyle(.secondary)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                } else if line.hasPrefix(">") {
                    let quoteText = String(line.drop(while: { $0 == ">" || $0 == " " }))
                    HStack(alignment: .top, spacing: 6) {
                        RoundedRectangle(cornerRadius: 1.5)
                            .fill(Color.accentColor.opacity(0.45))
                            .frame(width: 2.5)
                        Text(renderHFInlineMarkdown(quoteText))
                            .font(.system(size: 10.5))
                            .foregroundStyle(.secondary)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                } else {
                    Text(renderHFInlineMarkdown(line))
                        .font(.system(size: 10.5))
                        .foregroundStyle(.secondary)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .textSelection(.enabled)
    }
}

let UNSUPPORTED_HF_PIPELINE_TAGS: Set<String> = [
    "image-to-3d", "text-to-3d", "image-segmentation", "object-detection",
    "depth-estimation", "mask-generation", "keypoint-detection", "robotics",
    "reinforcement-learning", "tabular-classification", "tabular-regression",
    "time-series-forecasting", "audio-classification", "automatic-speech-recognition",
    "text-to-speech", "audio-to-audio", "feature-extraction", "sentence-similarity",
    "token-classification", "text-classification", "zero-shot-image-classification",
    "zero-shot-classification", "fill-mask", "question-answering",
    "table-question-answering", "video-classification"
]

let SUPPORTED_TRENDING_PIPELINE_TAGS: Set<String> = [
    "text-generation", "image-text-to-text", "visual-question-answering",
    "any-to-any", "text-to-image", "image-to-image", "text-to-video", "image-to-video"
]

func analyzeHFModelSizing(_ obj: [String: Any], repoId: String, isGGUF: Bool, fallbackStorageGb: Double = 0.0) -> (
    paramCount: Int,
    paramLabel: String,
    estVramGb: Double,
    deployStatus: String,
    deployZh: String,
    deployEn: String
) {
    let ptag = ((obj["pipeline_tag"] as? String) ?? "").trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
    let st = obj["safetensors"] as? [String: Any]
    let gg = obj["gguf"] as? [String: Any]
    var totalParams: Int64 = 0
    if let n = st?["total"] as? NSNumber {
        totalParams = n.int64Value
    } else if let n = gg?["total"] as? NSNumber {
        totalParams = n.int64Value
    }
    if totalParams <= 0 {
        if let regex = try? NSRegularExpression(pattern: "(?:^|[-_/])(\\d+(?:\\.\\d+)?)\\s*([bBmMtT])(?:[-_/\\b]|$)"),
           let match = regex.firstMatch(in: repoId, range: NSRange(repoId.startIndex..., in: repoId)),
           let r1 = Range(match.range(at: 1), in: repoId),
           let r2 = Range(match.range(at: 2), in: repoId),
           let val = Double(repoId[r1]) {
            let unit = repoId[r2].uppercased()
            if unit == "T" { totalParams = Int64(val * 1_000_000_000_000) }
            else if unit == "B" { totalParams = Int64(val * 1_000_000_000) }
            else if unit == "M" { totalParams = Int64(val * 1_000_000) }
        }
    }

    let paramLabel: String
    if totalParams >= 1_000_000_000_000 {
        paramLabel = String(format: "%.1fT", Double(totalParams) / 1_000_000_000_000.0)
    } else if totalParams >= 1_000_000_000 {
        let b = Double(totalParams) / 1_000_000_000.0
        if b >= 20 {
            paramLabel = String(format: "%.0fB", b)
        } else {
            let s = String(format: "%.1fB", b)
            paramLabel = s.replacingOccurrences(of: ".0B", with: "B")
        }
    } else if totalParams >= 1_000_000 {
        paramLabel = String(format: "%.0fM", Double(totalParams) / 1_000_000.0)
    } else {
        paramLabel = ""
    }

    let paramsB = totalParams > 0 ? (Double(totalParams) / 1_000_000_000.0) : 0.0
    var estVramGb: Double = 0.0
    if isGGUF {
        estVramGb = paramsB > 0 ? ((paramsB * 0.62 + 1.2) * 10).rounded() / 10 : 0.0
    } else if let pmap = st?["parameters"] as? [String: Any], !pmap.isEmpty {
        var bytesTotal: Double = 0.0
        for (dtype, rawCnt) in pmap {
            let cnt = (rawCnt as? NSNumber)?.doubleValue ?? 0.0
            let dt = dtype.uppercased()
            if dt.contains("32") { bytesTotal += cnt * 4.0 }
            else if dt.contains("16") { bytesTotal += cnt * 2.0 }
            else if dt.contains("8") { bytesTotal += cnt * 1.0 }
            else if dt.contains("4") { bytesTotal += cnt * 0.55 }
            else { bytesTotal += cnt * 2.0 }
        }
        estVramGb = (((bytesTotal / 1_000_000_000.0) * 1.12 + 1.2) * 10).rounded() / 10
    } else if paramsB > 0 {
        estVramGb = ((paramsB * 2.1 + 1.2) * 10).rounded() / 10
    } else if fallbackStorageGb > 0 {
        estVramGb = ((fallbackStorageGb * 1.12 + 1.0) * 10).rounded() / 10
    }

    let status: String
    let zh: String
    let en: String
    let vramInt = max(1, Int(estVramGb.rounded()))
    if !isGGUF && UNSUPPORTED_HF_PIPELINE_TAGS.contains(ptag) {
        status = "too_large"
        zh = "非内置管线 (\(ptag) · 需专用SDK)"
        en = "Custom Pipeline (\(ptag))"
    } else if estVramGb <= 0 {
        status = "unknown"
        zh = "显存待探测"
        en = "VRAM TBD"
    } else if estVramGb <= 14.2 {
        status = "great"
        zh = "适合 · T4(15G)可跑 (~\(vramInt)G)"
        en = "Fit: T4 15G (~\(vramInt)G)"
    } else if estVramGb <= 22.5 {
        status = "good"
        zh = "适合 · 需L4(24G) (~\(vramInt)G)"
        en = "Fit: L4 24G (~\(vramInt)G)"
    } else if estVramGb <= 39.0 {
        status = "a100"
        zh = "可部署 · 需A100(40G) (~\(vramInt)G)"
        en = "Fit: A100 40G (~\(vramInt)G)"
    } else if estVramGb <= 78.0 {
        status = "heavy"
        zh = "需A100(80G) (~\(vramInt)G)"
        en = "Needs A100 80G (~\(vramInt)G)"
    } else if isGGUF && paramsB <= 240.0 {
        status = "heavy"
        zh = "需A100(80G)+CPU卸载 (~\(vramInt)G)"
        en = "A100 80G + Offload (~\(vramInt)G)"
    } else {
        status = "too_large"
        zh = "超单卡上限 (~\(vramInt)G · 建议搜GGUF)"
        en = "Too Large (~\(vramInt)G · Try GGUF)"
    }
    return (Int(clamping: totalParams), paramLabel, estVramGb, status, zh, en)
}


// MARK: - 文本清理：过滤服务端消息中的 emoji

func stripEmoji(_ text: String) -> String {
    var scalars = String.UnicodeScalarView()
    for s in text.unicodeScalars {
        let p = s.properties
        let v = s.value
        let isEmoji = p.isEmojiPresentation
            || (p.isEmoji && v > 0x238C)
            || v == 0xFE0F || v == 0x200D || v == 0x20E3
            || (0x1F1E6...0x1F1FF).contains(v)
        if !isEmoji { scalars.append(s) }
    }
    var result = String(scalars)
    while result.contains("  ") { result = result.replacingOccurrences(of: "  ", with: " ") }
    return result.trimmingCharacters(in: .whitespaces)
}

