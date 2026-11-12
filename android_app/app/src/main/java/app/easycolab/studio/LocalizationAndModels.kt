package app.easycolab.studio

import android.content.Context
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.util.Locale
import java.util.UUID

enum class AppLanguage(val code: String) {
    ZH("zh"),
    EN("en")
}

object LanguageManager {
    var lang by mutableStateOf(AppLanguage.ZH)
        private set

    val isEN: Boolean get() = lang == AppLanguage.EN

    fun init(context: Context) {
        val saved = context.getSharedPreferences("easycolab_prefs", Context.MODE_PRIVATE)
            .getString("appLanguage", "zh")
        lang = if (saved == "en") AppLanguage.EN else AppLanguage.ZH
    }

    fun setLanguage(newLang: AppLanguage, context: Context? = null) {
        lang = newLang
        context?.getSharedPreferences("easycolab_prefs", Context.MODE_PRIVATE)
            ?.edit()?.putString("appLanguage", newLang.code)?.apply()
    }

    fun toggle(context: Context? = null) {
        setLanguage(if (lang == AppLanguage.ZH) AppLanguage.EN else AppLanguage.ZH, context)
    }
}

fun L(zh: String, en: String): String = if (LanguageManager.lang == AppLanguage.EN) en else zh

fun stripEmoji(text: String): String {
    if (text.isEmpty()) return ""
    val sb = StringBuilder(text.length)
    var i = 0
    while (i < text.length) {
        val cp = text.codePointAt(i)
        val count = Character.charCount(cp)
        val isEmoji = (cp in 0x1F300..0x1FAFF)
            || (cp in 0x2600..0x27BF)
            || cp == 0xFE0F || cp == 0x200D || cp == 0x20E3
            || (cp in 0x1F1E6..0x1F1FF)
        if (!isEmoji) {
            sb.appendCodePoint(cp)
        }
        i += count
    }
    return sb.toString().replace(Regex("\\s{2,}"), " ").trim()
}

fun localizeModelFileDesc(raw: String): String {
    if (!LanguageManager.isEN || raw.isEmpty()) return raw
    return raw
        .replace(" [RAM内存盘]", " [RAM Disk]")
        .replace("DiT 音视频主干 BF16", "DiT Audio-Video Backbone BF16")
        .replace("多模态编码器 BF16", "Multimodal Encoder BF16")
        .replace("3D 视频 VAE BF16", "3D Video VAE BF16")
        .replace("32kHz 立体声 VAE BF16", "32kHz Stereo Audio VAE BF16")
        .replace("权重分片", "Weight Shard")
        .replace("Unsloth UD-Q4_K_M 主模型", "Unsloth UD-Q4_K_M Main Model")
        .replace("多模态视觉投影器", "Multimodal Vision Projector")
        .replace("Unsloth MTP 多词元投机解码头", "Unsloth MTP Speculative Decoding Head")
        .replace("编码器", "Encoder")
        .replace("图像 VAE", "Image VAE")
}

fun localizeServerText(text: String): String {
    if (text.isEmpty()) return text
    val adaptedZh = text
        .replace("Mac 客户端", "App 客户端")
        .replace("左侧", "算力页/上方")
    if (!LanguageManager.isEN) return adaptedZh

    val exactMap = mapOf(
        "未加载" to "Not Loaded",
        "未连接 Colab 服务端" to "Colab Server Disconnected",
        "尚未启动云端 ComfyUI 工作台" to "Cloud ComfyUI Studio Not Started",
        "Google Drive 自动软链持久化" to "Google Drive Auto-Symlink Persistence",
        "Google Drive 实时软链挂载" to "Google Drive Live Symlink Mount",
        "Google Drive 云盘自动持久化" to "Google Drive Auto-Persistence",
        "实例本地高速存储" to "Instance Local NVMe Storage",
        "已彻底释放全部云端实例，计费速率归零。" to "All cloud Colab instances terminated. Billing rate is now 0 CU/h.",
        "已手动停止当前推理任务" to "Inference cancelled by user",
        "正在上传最新多模型开源服务端代码 (app.py)..." to "Uploading latest multi-model server engine (app.py)...",
        "正在云端配置 Google Drive 持久化、多模型引擎并启动隧道 (约需 40~90 秒)..." to "Configuring Google Drive persistence, multi-model engine & public tunnel (~40–90s)...",
        "正在克隆 DiffSynth-Studio..." to "Cloning DiffSynth-Studio..."
    )
    exactMap[text]?.let { return it }

    var s = localizeModelFileDesc(text)
    val replacements = listOf(
        "已无缝接管在线 ComfyUI 画布" to "Connected to active ComfyUI canvas",
        "ComfyUI 进程已退出" to "ComfyUI process exited",
        "，可点击重新启动" to "; tap to restart",
        "正在 8 线程极速下载 " to "8-thread fast downloading ",
        "正在 8 线程并发下载 " to "8-thread downloading ",
        "正在下载 " to "Downloading ",
        " 已就绪 (" to " ready (",
        ")，跳过下载" to "), skipping",
        "正在评估显存余量并装载 " to "Checking VRAM & loading ",
        " 至 GPU..." to " into GPU...",
        " 正在编码多模态上下文并启动推理..." to " encoding multimodal context & starting inference...",
        " 推理完成！耗时 " to " inference complete! Elapsed ",
        " 正在使用多模态编码器解析提示词" to " encoding prompts with multimodal encoder",
        "DiT 采样已完成，正在执行" to "DiT sampling finished, running ",
        "3D 视频 VAE 解码" to "3D Video VAE decoding",
        "视频帧解码完成，正在执行 32kHz 立体声音轨解码" to "Video frames decoded, decoding 32kHz stereo audio",
        " 正在执行去噪采样第 " to " denoising step ",
        " 步 (" to " (",
        "VAE 解码完成，正在合成 32kHz 立体声音轨并封装 MP4" to "VAE decoded, muxing 32kHz stereo audio into MP4",
        "正在写入无损 PNG 图像文件" to "Writing lossless PNG image",
        "生成完成！耗时 " to "Generation complete! Elapsed ",
        "生成出错: " to "Generation error: ",
        "尚未加载至 Colab GPU 显存，请先在 Mac 客户端点击「加载到显存」。" to "is not loaded in Colab GPU VRAM. Tap 'Load to VRAM' first.",
        "尚未加载到显存" to "is not loaded in VRAM",
        "当前已常驻：" to "currently resident: ",
        "已通过 Google OAuth 自动挂载 Google Drive" to "Mounted Google Drive automatically via Google OAuth"
    )
    for ((zhSub, enSub) in replacements) {
        if (s.contains(zhSub)) s = s.replace(zhSub, enSub)
    }
    return s
}

fun formatDuration(sec: Double, compact: Boolean = false): String {
    val s = sec.coerceAtLeast(0.0)
    if (s < 60.0) {
        if (compact) return String.format(Locale.US, "%.1fs", s)
        return if (LanguageManager.isEN) String.format(Locale.US, "%.1f s", s)
        else String.format(Locale.US, "%.1f 秒", s)
    }
    val mins = (s / 60.0).toInt()
    val rem = s - mins * 60.0
    if (compact) return String.format(Locale.US, "%dm%.0fs", mins, rem)
    return if (LanguageManager.isEN) String.format(Locale.US, "%dm %.1fs", mins, rem)
    else String.format(Locale.US, "%d分%.1f秒", mins, rem)
}

enum class ModelModality(val raw: String) {
    VIDEO_AUDIO("video_audio"),
    IMAGE("image"),
    LLM_VLM("llm_vlm"),
    COMFY_UI("comfyui")
}

data class TaskModeItem(
    val id: String,
    val titleZh: String,
    val titleEn: String,
    val subtitleZh: String,
    val subtitleEn: String
) {
    val title: String get() = L(titleZh, titleEn)
    val subtitle: String get() = L(subtitleZh, subtitleEn)
}

data class ModelFileItem(
    val name: String,
    val desc: String? = null,
    val exists: Boolean = false,
    val sizeGb: Double = 0.0
) {
    val localizedDesc: String? get() = desc?.takeIf { it.isNotEmpty() }?.let { localizeModelFileDesc(it) }
}

data class OpenModelSpec(
    val id: String,
    val nameZh: String,
    val nameEn: String,
    val shortTitleZh: String,
    val shortTitleEn: String,
    val repoId: String,
    val badgeZh: String,
    val badgeEn: String,
    val summaryZh: String,
    val summaryEn: String,
    val approxSizeGb: Double,
    val modality: ModelModality,
    val defaultSteps: Float,
    val modes: List<TaskModeItem>,
    val defaultFiles: List<ModelFileItem>,
    val includePattern: String = "",
    val isCustom: Boolean = false
) {
    val name: String get() = L(nameZh, nameEn)
    val shortTitle: String get() = L(shortTitleZh, shortTitleEn)
    val badge: String get() = L(badgeZh, badgeEn)
    val summary: String get() = L(summaryZh, summaryEn)

    companion object {
        fun fromCustomJson(obj: JSONObject): OpenModelSpec {
            val modRaw = obj.optString("modality", "llm_vlm")
            val mod = when (modRaw) {
                "video_audio" -> ModelModality.VIDEO_AUDIO
                "image" -> ModelModality.IMAGE
                else -> ModelModality.LLM_VLM
            }
            val repoId = obj.optString("repo_id", "")
            val rawName = obj.optString("name", repoId.substringAfterLast('/').ifEmpty { "Custom HF" })
            val sizeGb = obj.optDouble("approx_size_gb", 0.0).let { if (it.isNaN()) 0.0 else it }
            val arch = obj.optString("pipeline_arch", "gguf").ifEmpty { "gguf" }.uppercase(Locale.US)
            val inc = obj.optString("include_pattern", "")
            val badgeZh = if (sizeGb > 0.0) String.format(Locale.US, "自定义 %s · %.1f GB", arch, sizeGb) else "自定义 HF · $arch"
            val badgeEn = if (sizeGb > 0.0) String.format(Locale.US, "Custom %s · %.1f GB", arch, sizeGb) else "Custom HF · $arch"
            val patDesc = if (inc.isNotEmpty()) " ($inc)" else ""
            val summaryZh = obj.optString("category", "").ifEmpty { "自定义 HuggingFace 仓库 $repoId$patDesc" }
            val summaryEn = "Custom HuggingFace repo $repoId$patDesc"
            val (steps, modes) = when (mod) {
                ModelModality.VIDEO_AUDIO -> 35f to listOf(
                    TaskModeItem("t2va", "文生音视频", "Text to Video+Audio", "输入镜头与声音描述生成视频", "Generate HD video & stereo audio from prompts"),
                    TaskModeItem("fl2va", "首尾帧生视频", "Keyframes to Video", "从相册选择首帧/尾帧参考图", "Pick start/end keyframes from Gallery")
                )
                ModelModality.IMAGE -> 20f to listOf(
                    TaskModeItem("t2i", "高清文生图", "HD Text-to-Image", "自定义 HuggingFace 图像生成管线", "Custom HuggingFace image generation"),
                    TaskModeItem("i2i_edit", "图生图重绘", "Image Restyle", "从手机相册选参考图重绘", "Pick a photo and adjust denoising strength")
                )
                else -> 20f to listOf(
                    TaskModeItem("chat", "深度推理对话", "Reasoning Chat", "自定义 HuggingFace 模型对话与推理", "Custom HuggingFace model chat & reasoning"),
                    TaskModeItem("vlm", "看图反推/视觉", "Vision & Prompt", "多模态看图分析与提示词生成", "Multimodal photo analysis & prompt generation"),
                    TaskModeItem("api", "API 协议网关", "API Gateway", "OpenAI (/v1) 与 Anthropic (/v1/messages) 接口", "OpenAI (/v1) & Anthropic (/v1/messages) endpoints")
                )
            }
            return OpenModelSpec(
                id = obj.optString("id", "custom_" + UUID.randomUUID().toString().take(8)),
                nameZh = rawName,
                nameEn = rawName,
                shortTitleZh = rawName,
                shortTitleEn = rawName,
                repoId = repoId,
                badgeZh = badgeZh,
                badgeEn = badgeEn,
                summaryZh = summaryZh,
                summaryEn = summaryEn,
                approxSizeGb = sizeGb,
                modality = mod,
                defaultSteps = steps,
                modes = modes,
                defaultFiles = emptyList(),
                includePattern = inc,
                isCustom = true
            )
        }
    }
}

val OPEN_MODEL_CATALOG: List<OpenModelSpec> = listOf(
    OpenModelSpec(
        id = "minimax_h3",
        nameZh = "MiniMax-H3 (33B)",
        nameEn = "MiniMax-H3 (33B)",
        shortTitleZh = "MiniMax 有声视频",
        shortTitleEn = "MiniMax Video",
        repoId = "MiniMaxAI/MiniMax-H3",
        badgeZh = "BF16 原生 · 134 GB",
        badgeEn = "Native BF16 · 134 GB",
        summaryZh = "同步生成 24fps 高清视频与 32kHz 立体声音效、对白及配乐",
        summaryEn = "Native BF16 HD video generation with synchronized 32kHz stereo SFX, speech & music",
        approxSizeGb = 134.1,
        modality = ModelModality.VIDEO_AUDIO,
        defaultSteps = 35f,
        modes = listOf(
            TaskModeItem("t2va", "文生音视频", "Text to Video+Audio", "输入镜头与声音描述，一次生成视频与立体声音轨", "Generate HD video & stereo audio from visual and sound prompts"),
            TaskModeItem("fl2va", "首尾帧生视频", "Keyframes to Video", "从相册选择首帧/尾帧参考图，精准锁定起止画面与运镜", "Pick start/end keyframes from Gallery to control motion")
        ),
        defaultFiles = (1..13).map { ModelFileItem(String.format(Locale.US, "FL2VA/transformer/model-%05d-of-00013.safetensors", it), "DiT 音视频主干 BF16 $it/13") } +
            (1..14).map { ModelFileItem(String.format(Locale.US, "FL2VA/text_encoder/model-%05d-of-00014.safetensors", it), "多模态编码器 BF16 $it/14") } +
            listOf(
                ModelFileItem("FL2VA/video_vae/source/model.safetensors", "3D 视频 VAE BF16 (9.7 GB)"),
                ModelFileItem("FL2VA/audio_vae/model.safetensors", "32kHz 立体声 VAE BF16 (0.6 GB)")
            )
    ),
    OpenModelSpec(
        id = "z_image_turbo",
        nameZh = "Z-Image-Turbo",
        nameEn = "Z-Image-Turbo",
        shortTitleZh = "Z-Image 8步生图",
        shortTitleEn = "Z-Image Turbo",
        repoId = "Tongyi-MAI/Z-Image-Turbo",
        badgeZh = "8步极速 · 30.6 GB",
        badgeEn = "8-Step Turbo · 30.6 GB",
        summaryZh = "8 步蒸馏极速写实摄影与中英文排版海报生图模型",
        summaryEn = "8-step distilled photorealism & bilingual poster design model",
        approxSizeGb = 30.6,
        modality = ModelModality.IMAGE,
        defaultSteps = 8f,
        modes = listOf(
            TaskModeItem("t2i", "8 步极速文生图", "8-Step Text-to-Image", "秒级输出商业级写实摄影与中英文排版海报", "Seconds-fast commercial portrait & poster typography"),
            TaskModeItem("i2i_edit", "图生图风格重绘", "Image Restyle", "从手机相册选参考图并调节重绘幅度生成新细节", "Pick a photo and adjust denoising strength to restyle")
        ),
        defaultFiles = (1..3).map { ModelFileItem(String.format(Locale.US, "transformer/diffusion_pytorch_model-%05d-of-00003.safetensors", it), "DiT $it/3") } +
            (1..3).map { ModelFileItem(String.format(Locale.US, "text_encoder/model-%05d-of-00003.safetensors", it), "编码器 $it/3") } +
            listOf(ModelFileItem("vae/diffusion_pytorch_model.safetensors", "图像 VAE"))
    ),
    OpenModelSpec(
        id = "qwen_image_21",
        nameZh = "Qwen-Image-2.1",
        nameEn = "Qwen-Image-2.1",
        shortTitleZh = "Qwen 旗舰修图",
        shortTitleEn = "Qwen-Image 2.1",
        repoId = "Qwen/Qwen-Image-2.1",
        badgeZh = "生图与修图 · 30.9 GB",
        badgeEn = "Gen & Edit · 30.9 GB",
        summaryZh = "通义千问旗舰图像生成与自然语言多图指令编辑模型",
        summaryEn = "Qwen flagship image generation & multi-image instruction editing",
        approxSizeGb = 30.9,
        modality = ModelModality.IMAGE,
        defaultSteps = 40f,
        modes = listOf(
            TaskModeItem("t2i", "高清文生图", "HD Text-to-Image", "复杂构图、精准中英文文字排版与高质感插画摄影", "Complex layouts, accurate bilingual text & high-detail art"),
            TaskModeItem("i2i_edit", "多图指令修图", "Instruction Photo Edit", "从相册选 1~2 张照片，用自然语言改局部、换背景或融合主体", "Pick 1–2 photos to edit regions, swap backgrounds, or fuse subjects")
        ),
        defaultFiles = (1..2).map { ModelFileItem(String.format(Locale.US, "transformer/diffusion_pytorch_model-%05d-of-00002.safetensors", it), "DiT $it/2") } +
            (1..4).map { ModelFileItem(String.format(Locale.US, "text_encoder/model-%05d-of-00004.safetensors", it), "编码器 $it/4") } +
            listOf(ModelFileItem("vae/diffusion_pytorch_model.safetensors", "图像 VAE"))
    ),
    OpenModelSpec(
        id = "qwen38_27b_gguf",
        nameZh = "Qwen3.8-27B-GGUF",
        nameEn = "Qwen3.8-27B-GGUF",
        shortTitleZh = "Qwen3.8 极速对话",
        shortTitleEn = "Qwen3.8 GGUF",
        repoId = "unsloth/Qwen3.8-27B-GGUF",
        badgeZh = "100 tok/s · 18.7 GB",
        badgeEn = "100 tok/s · 18.7 GB",
        summaryZh = "UD-Q4_K_M + MTP 投机解码极速推理，支持最高 256K 上下文、看图反推与 API 网关",
        summaryEn = "UD-Q4_K_M + MTP speculative decoding (~100 tok/s), 256K context, vision & API gateway",
        approxSizeGb = 18.7,
        modality = ModelModality.LLM_VLM,
        defaultSteps = 20f,
        modes = listOf(
            TaskModeItem("chat", "深度推理对话", "Reasoning Chat", "长思维链推理、代码与分镜创作", "CoT reasoning, coding & storyboards"),
            TaskModeItem("vlm", "看图反推/视觉", "Vision & Prompt", "传照片解析构图、OCR 或反推生视频提示词", "Analyze photos, OCR & reverse-engineer prompts"),
            TaskModeItem("api", "API 协议网关", "API Gateway", "OpenAI (/v1) 与 Anthropic (/v1/messages) 接口", "OpenAI (/v1) & Anthropic (/v1/messages) endpoints")
        ),
        defaultFiles = listOf(
            ModelFileItem("Qwen3.8-27B-UD-Q4_K_M.gguf", "Unsloth UD-Q4_K_M 主模型 (16.5 GB)"),
            ModelFileItem("mmproj-F16.gguf", "多模态视觉投影器 (0.93 GB)"),
            ModelFileItem("MTP/mtp-Qwen3.8-27B-Q4_0.gguf", "Unsloth MTP 多词元投机解码头 (1.31 GB)")
        )
    ),
    OpenModelSpec(
        id = "qwen38_27b",
        nameZh = "Qwen3.8-27B (BF16)",
        nameEn = "Qwen3.8-27B (BF16)",
        shortTitleZh = "Qwen3.8 满血版",
        shortTitleEn = "Qwen3.8 BF16",
        repoId = "Qwen/Qwen3.8-27B",
        badgeZh = "BF16 原生 · 51.8 GB",
        badgeEn = "Native BF16 · 51.8 GB",
        summaryZh = "原生 BF16 满血精度多模态大模型，支持最高 256K 上下文与视觉理解",
        summaryEn = "Full native BF16 multimodal LLM, up to 256K context & vision understanding",
        approxSizeGb = 51.8,
        modality = ModelModality.LLM_VLM,
        defaultSteps = 20f,
        modes = listOf(
            TaskModeItem("chat", "深度推理对话", "Reasoning Chat", "BF16 满血长思维链对话与创作", "Full BF16 CoT reasoning & scripting"),
            TaskModeItem("vlm", "看图反推/视觉", "Vision & Prompt", "传照片进行高精度视觉理解与提示词反推", "High-precision photo analysis & prompt generation"),
            TaskModeItem("api", "API 协议网关", "API Gateway", "OpenAI (/v1) 与 Anthropic (/v1/messages) 接口", "OpenAI (/v1) & Anthropic (/v1/messages) endpoints")
        ),
        defaultFiles = (1..18).map { ModelFileItem(String.format(Locale.US, "model-%05d-of-00018.safetensors", it), "权重分片 $it/18") }
    ),
    OpenModelSpec(
        id = "minimax_h3_image",
        nameZh = "MiniMax-H3-Image (4K)",
        nameEn = "MiniMax-H3-Image (4K)",
        shortTitleZh = "H3-Image 4K",
        shortTitleEn = "H3-Image 4K",
        repoId = "MiniMaxAI/MiniMax-H3-Image",
        badgeZh = "4K 直出 · 6 步蒸馏 · 135 GB",
        badgeEn = "Native 4K · 6-Step · 135 GB",
        summaryZh = "MiniMax H3 家族开源 4K 图像模型，支持文生图与最多 16 张参考图编辑，6 步极速采样",
        summaryEn = "Open-weight 4K image model from the H3 family: text-to-image & multi-reference editing in 6 steps",
        approxSizeGb = 135.4,
        modality = ModelModality.IMAGE,
        defaultSteps = 6f,
        modes = listOf(
            TaskModeItem("t2i", "4K 高清文生图", "4K Text-to-Image", "1600 万像素 4K 原生直出，照片级细节与精准构图", "Native 16MP 4K output with photoreal detail"),
            TaskModeItem("i2i_edit", "多参考图指令编辑", "Multi-Reference Edit", "上传 1~2 张参考图，用自然语言改局部、换背景或融合主体", "Upload 1-2 references to edit or fuse subjects via natural language")
        ),
        defaultFiles = (1..12).map { ModelFileItem(String.format(Locale.US, "transformer_diffusers/diffusion_pytorch_model-%05d-of-00012.safetensors", it), "DiT $it/12") }
            + (1..14).map { ModelFileItem(String.format(Locale.US, "text_encoder/model-%05d-of-00014.safetensors", it), "编码器 $it/14") }
            + listOf(
                ModelFileItem("vae_diffusers/diffusion_pytorch_model.safetensors", "4K 图像 VAE"),
                ModelFileItem("pdd_fused_heads.safetensors", "PDD 融合输出头")
            )
    ),
    OpenModelSpec(
        id = "comfyui_studio",
        nameZh = "ComfyUI 节点工作台",
        nameEn = "ComfyUI Node Studio",
        shortTitleZh = "ComfyUI 工作台",
        shortTitleEn = "ComfyUI Studio",
        repoId = "comfyanonymous/ComfyUI",
        badgeZh = "4套预置包 · 云盘持久化",
        badgeEn = "4 Preset Packs · Drive Sync",
        summaryZh = "一键拉起云端 ComfyUI + 4 套视频工作流包，支持内置画布预览与成片一键存手机相册",
        summaryEn = "1-click cloud ComfyUI + 4 preset video packs, Chrome Custom Tab canvas & 1-tap pull to Android Gallery",
        approxSizeGb = 0.0,
        modality = ModelModality.COMFY_UI,
        defaultSteps = 25f,
        modes = listOf(
            TaskModeItem("comfy_canvas", "云端工作流与画布", "Workflows & Canvas", "一键配齐 Wan2.2 / MiniMax / LTX / 混元预置包并打开画布", "Install Wan2.2 / MiniMax / LTX / Hunyuan packs & open canvas"),
            TaskModeItem("comfy_assets", "下权重与拉取成片", "Weights & Outputs", "8 线程极速下模型至云盘，并将 ComfyUI 成片一键拉回手机", "8-thread cloud weight download & 1-tap pull outputs to phone")
        ),
        defaultFiles = emptyList()
    )
)

data class ResolutionOption(
    val id: String,
    val labelZh: String,
    val labelEn: String,
    val width: Int,
    val height: Int
) {
    val label: String get() = L(labelZh, labelEn)
}

val VIDEO_RESOLUTIONS: List<ResolutionOption> = listOf(
    ResolutionOption("v_480_832", "480 × 832 (9:16 竖屏短视频 · 推荐)", "480 × 832 (9:16 Vertical Short · Pick)", 480, 832),
    ResolutionOption("v_832_480", "832 × 480 (16:9 横屏标准)", "832 × 480 (16:9 Landscape Standard)", 832, 480),
    ResolutionOption("v_720_1280", "720 × 1280 (9:16 720P 高清竖屏)", "720 × 1280 (9:16 720P HD Vertical)", 720, 1280),
    ResolutionOption("v_1280_720", "1280 × 720 (16:9 720P 高清横屏)", "1280 × 720 (16:9 720P HD Landscape)", 1280, 720),
    ResolutionOption("v_640_640", "640 × 640 (1:1 方形)", "640 × 640 (1:1 Square)", 640, 640)
)

val IMAGE_RESOLUTIONS: List<ResolutionOption> = listOf(
    ResolutionOption("i_768_1344", "768 × 1344 (9:16 手机全屏海报 · 推荐)", "768 × 1344 (9:16 Mobile Poster · Pick)", 768, 1344),
    ResolutionOption("i_1024_1024", "1024 × 1024 (1:1 超清方图)", "1024 × 1024 (1:1 Square HD)", 1024, 1024),
    ResolutionOption("i_1344_768", "1344 × 768 (16:9 电影横幅)", "1344 × 768 (16:9 Cinematic Widescreen)", 1344, 768),
    ResolutionOption("i_1536_1024", "1536 × 1024 (3:2 单反摄影)", "1536 × 1024 (3:2 DSLR Photo)", 1536, 1024)
)

val H3_IMAGE_RESOLUTIONS: List<ResolutionOption> = listOf(
    ResolutionOption("h3_4096_4096", "4096 × 4096 (1:1 4K 方图 · 推荐)", "4096 × 4096 (1:1 4K Square · Recommended)", 4096, 4096),
    ResolutionOption("h3_4736_3552", "4736 × 3552 (4:3 4K 横图)", "4736 × 3552 (4:3 4K Landscape)", 4736, 3552),
    ResolutionOption("h3_3552_4736", "3552 × 4736 (3:4 4K 竖图)", "3552 × 4736 (3:4 4K Portrait)", 3552, 4736),
    ResolutionOption("h3_5472_3072", "5472 × 3072 (16:9 4K 宽屏)", "5472 × 3072 (16:9 4K Widescreen)", 5472, 3072),
    ResolutionOption("h3_3072_5472", "3072 × 5472 (9:16 4K 竖屏)", "3072 × 5472 (9:16 4K Portrait)", 3072, 5472),
    ResolutionOption("h3_6272_2688", "6272 × 2688 (21:9 4K 超宽)", "6272 × 2688 (21:9 4K Ultra-wide)", 6272, 2688)
)

fun imageResolutionsFor(modelId: String): List<ResolutionOption> =
    if (modelId == "minimax_h3_image") H3_IMAGE_RESOLUTIONS else IMAGE_RESOLUTIONS

data class PresetTemplate(
    val id: String,
    val category: ModelModality,
    val nameZh: String,
    val nameEn: String,
    val visualZh: String,
    val visualEn: String,
    val soundscape: String,
    val music: String
) {
    val name: String get() = L(nameZh, nameEn)
    val visual: String get() = L(visualZh, visualEn)
}

val PRESET_TEMPLATES: List<PresetTemplate> = listOf(
    PresetTemplate(
        id = "tpl_shinkai_train",
        category = ModelModality.VIDEO_AUDIO,
        nameZh = "新海诚风 · 盛夏樱花铁道口",
        nameEn = "Makoto Shinkai · Cherry Blossom Railway",
        visualZh = "Masterpiece Makoto Shinkai anime style, 2D cel-shaded animation. A teenage girl in a Japanese sailor school uniform standing at a sunlit railway crossing in late spring. A green commuter train speeds past in front of her, creating a strong gust of wind that blows her long black hair and a flurry of pink cherry blossom petals across the frame. Dramatic lens flare, glowing cumulous clouds in a deep blue sky, vibrant cinematic lighting, smooth 24fps keyframe animation.",
        visualEn = "Masterpiece Makoto Shinkai anime style, 2D cel-shaded animation. A teenage girl in a Japanese sailor school uniform standing at a sunlit railway crossing in late spring. A green commuter train speeds past in front of her, creating a strong gust of wind that blows her long black hair and a flurry of pink cherry blossom petals across the frame. Dramatic lens flare, glowing cumulous clouds in a deep blue sky, vibrant cinematic lighting, smooth 24fps keyframe animation.",
        soundscape = "Metallic clacking of train wheels on railway tracks, rhythmic dinging of the railroad crossing warning bell, warm spring wind rustling through leaves, a soft gasp from the girl.",
        music = "Emotional and nostalgic solo piano melody joined by warm acoustic guitar and soaring cinematic strings."
    ),
    PresetTemplate(
        id = "tpl_ufotable_duel",
        category = ModelModality.VIDEO_AUDIO,
        nameZh = "飞碟社风 · 苍蓝雷光剑术对决",
        nameEn = "Ufotable Sakuga · Azure Lightning Duel",
        visualZh = "High-budget ufotable anime action sakuga, dynamic fast-paced camera tracking. A silver-haired anime swordsman in a dark haori coat dashes across a shattered stone temple under a blood-red full moon, swinging a katana wreathed in crackling blue lightning and swirling water dragon effects. Sparks and glowing embers fly toward the camera in slow-motion impact frames, intense anime shading, dramatic motion blur.",
        visualEn = "High-budget ufotable anime action sakuga, dynamic fast-paced camera tracking. A silver-haired anime swordsman in a dark haori coat dashes across a shattered stone temple under a blood-red full moon, swinging a katana wreathed in crackling blue lightning and swirling water dragon effects. Sparks and glowing embers fly toward the camera in slow-motion impact frames, intense anime shading, dramatic motion blur.",
        soundscape = "Sharp metallic sword unsheathing and clashing clang, roaring thunder and crackling electric arcs, heavy stone debris crumbling, fierce battle cry.",
        music = "Epic dark orchestral battle music with fast taiko drums, intense choir, and distorted electric guitar riffs."
    ),
    PresetTemplate(
        id = "tpl_iceland_fpv",
        category = ModelModality.VIDEO_AUDIO,
        nameZh = "冰岛巨型瀑布 FPV 穿越机航拍",
        nameEn = "Iceland Waterfall FPV Drone Dive",
        visualZh = "FPV drone shot diving down a majestic Icelandic waterfall surrounded by lush green moss and basalt columns under golden hour sunlight, mist rising into a rainbow.",
        visualEn = "FPV drone shot diving down a majestic Icelandic waterfall surrounded by lush green moss and basalt columns under golden hour sunlight, mist rising into a rainbow.",
        soundscape = "Roaring waterfall rushing water, wind whooshing past the camera, distant seabirds calling.",
        music = "Epic cinematic acoustic guitar and soaring cello."
    ),
    PresetTemplate(
        id = "tpl_cyber_poster",
        category = ModelModality.IMAGE,
        nameZh = "东方赛博霓虹海报（含中文排版）",
        nameEn = "Cyberpunk Neon Bund Poster",
        visualZh = "超清商业电影海报摄影，雨夜霓虹闪烁的未来上海外滩街道，一位身着机能风银色夹克的少女回眸凝视镜头，景深虚化光斑，顶部醒目发光现代中文字体排版写着“未来纪元 2026”，极致光影细节，8K画质。",
        visualEn = "Ultra-HD commercial sci-fi movie poster photography, rain-slicked cyberpunk Shanghai Bund street glowing with neon reflections at night, a young woman in a futuristic silver techwear jacket looking back at the camera, shallow depth of field bokeh flares, bold glowing modern title typography at the top reading \"FUTURE ERA 2026\" (未来纪元 2026), intricate lighting details, 8K.",
        soundscape = "",
        music = ""
    ),
    PresetTemplate(
        id = "tpl_llm_storyboard",
        category = ModelModality.LLM_VLM,
        nameZh = "分镜构思",
        nameEn = "Storyboards",
        visualZh = "请帮我构思 3 组极具画面感的新海诚风格动画短片分镜，每组包含：1) 英文 Visual & Camera 镜头提示词；2) Soundscape 环境音描述；3) Background Music 配乐描述。",
        visualEn = "Please design 3 vivid Makoto Shinkai-style anime short film storyboard shots. For each shot, provide: 1) Visual & Camera prompt; 2) Soundscape & SFX prompt; 3) Background Music prompt.",
        soundscape = "",
        music = ""
    ),
    PresetTemplate(
        id = "tpl_vlm_reverse",
        category = ModelModality.LLM_VLM,
        nameZh = "看图反推",
        nameEn = "Vision Prompt",
        visualZh = "请仔细观察这张图片的主体、光影色调、镜头景别与艺术风格，先做简要中文分析，然后反推出一段高质量的英文生图/生视频 Prompt。",
        visualEn = "Carefully analyze the subject, lighting, color palette, camera framing, and artistic style of this image. First give a concise visual breakdown, then write a high-quality English image/video generation prompt.",
        soundscape = "",
        music = ""
    )
)

data class LoadedModelSummary(
    val id: String,
    val name: String,
    val mode: String? = null,
    val vramGb: Double? = null,
    val contextLength: Int? = null
) {
    val localizedName: String
        get() = OPEN_MODEL_CATALOG.firstOrNull { it.id == id }?.name ?: localizeServerText(name)
}

data class ComfyOutputMediaItem(
    val relPath: String,
    val filename: String,
    val mediaType: String? = null,
    val sizeMb: Double? = null
)

data class ComfyPresetPackItem(
    val id: String,
    val title: String,
    val badge: String,
    val scenario: String,
    val approxSizeGb: Double,
    val installedModels: Int,
    val totalModels: Int,
    val ready: Boolean
) {
    val localizedTitle: String
        get() {
            if (!LanguageManager.isEN) return title
            return when (id) {
                "wan22_i2v_flf2v" -> "Wan2.2 14B · I2V + First/Last Frame"
                "minimax_h3_i2v_flf2v" -> "MiniMax-H3 Turbo · I2VA + Keyframes"
                "ltx23_flf2v" -> "LTX-2.3 (22B) · Cinematic Camera + Audio"
                "hunyuan15_i2v_1080p" -> "HunyuanVideo 1.5 · Direct 1080P Super-Res"
                else -> localizeServerText(title)
            }
        }

    val localizedBadge: String
        get() {
            if (!LanguageManager.isEN) return badge
            return when (id) {
                "wan22_i2v_flf2v" -> "Beginner Pick · 4-Step"
                "minimax_h3_i2v_flf2v" -> "Stereo Audio · 8-Step"
                "ltx23_flf2v" -> "Camera Motion · 2 Weights"
                "hunyuan15_i2v_1080p" -> "720P + 1080P Dual"
                else -> localizeServerText(badge)
            }
        }

    val localizedScenario: String
        get() {
            if (!LanguageManager.isEN) return scenario
            return when (id) {
                "wan22_i2v_flf2v" -> "Single-Image I2V & First/Last-Frame templates (~25s on G4, 100% built-in nodes)"
                "minimax_h3_i2v_flf2v" -> "HD dynamic video + synchronized stereo SFX, speech & music in one pass"
                "ltx23_flf2v" -> "Optimized for sweeping camera motion between start & end keyframes with audio"
                "hunyuan15_i2v_1080p" -> "Upload 1 image to render both 720P base video and 1920×1080 Full HD output"
                else -> localizeServerText(scenario)
            }
        }
}

val DEFAULT_COMFY_PRESET_PACKS: List<ComfyPresetPackItem> = listOf(
    ComfyPresetPackItem("wan22_i2v_flf2v", "万相 Wan2.2 14B · 图生视频 + 首尾帧双工作流", "新手首选 · 4步极速", "含「单图动起来」与「首尾双图丝滑过渡」2 套中文画布，G4 约 25 秒出片", 35.4, 0, 6, false),
    ComfyPresetPackItem("minimax_h3_i2v_flf2v", "MiniMax-H3 Turbo · 图生有声视频 + 首尾帧", "立体声音效 · 8步加速", "一次生成高清动态画面 + 同步环境音效/配乐/对白", 39.1, 0, 5, false),
    ComfyPresetPackItem("ltx23_flf2v", "LTX-2.3 (22B) · 首尾帧电影级运镜有声工作流", "电影推拉摇移 · 仅 2 权重", "专为首尾关键帧大幅度镜头运动优化 + 自动合成配乐音轨", 36.3, 0, 2, false),
    ComfyPresetPackItem("hunyuan15_i2v_1080p", "混元 HunyuanVideo 1.5 · 单图直出 1080P 超分", "720P + 1080P 双路超清", "默认激活潜空间超分管线，传 1 张图自动渲染 720P 与 1080P 成片", 43.5, 0, 7, false)
)

data class LocalMediaItem(
    val file: File,
    val filename: String,
    val isImage: Boolean,
    val createdAtMillis: Long,
    val elapsedSeconds: Double?,
    val fileSizeMb: Double
)

data class HFTrendingModelItem(
    val repoId: String,
    val name: String,
    val pipelineTag: String,
    val modality: String,
    val isGguf: Boolean,
    val isGated: Boolean,
    val suggestedPattern: String,
    val likes: Int,
    val downloads: Int,
    val paramLabel: String = "",
    val estVramGb: Double = 0.0,
    val deployStatus: String = "unknown",
    val deployLabelZh: String = "显存待探测",
    val deployLabelEn: String = "VRAM TBD"
) {
    val localizedDeployLabel: String
        get() = stripEmoji(L(deployLabelZh.ifEmpty { "显存待探测" }, deployLabelEn.ifEmpty { "VRAM TBD" }))
}

val UNSUPPORTED_HF_PIPELINE_TAGS = setOf(
    "image-to-3d", "text-to-3d", "image-segmentation", "object-detection",
    "depth-estimation", "mask-generation", "keypoint-detection", "robotics",
    "reinforcement-learning", "tabular-classification", "tabular-regression",
    "time-series-forecasting", "audio-classification", "automatic-speech-recognition",
    "text-to-speech", "audio-to-audio", "feature-extraction", "sentence-similarity",
    "token-classification", "text-classification", "zero-shot-image-classification",
    "zero-shot-classification", "fill-mask", "question-answering",
    "table-question-answering", "video-classification"
)

val SUPPORTED_TRENDING_PIPELINE_TAGS = setOf(
    "text-generation", "image-text-to-text", "visual-question-answering",
    "any-to-any", "text-to-image", "image-to-image", "text-to-video", "image-to-video"
)

fun analyzeHFModelSizingJson(item: JSONObject, repoId: String, isGguf: Boolean): HFSizingResult {
    val ptag = item.optString("pipeline_tag", "").trim().lowercase(java.util.Locale.US)
    val st = item.optJSONObject("safetensors")
    val gg = item.optJSONObject("gguf")
    var totalParams = st?.optLong("total", 0L)?.takeIf { it > 0L }
        ?: gg?.optLong("total", 0L)?.takeIf { it > 0L }
        ?: 0L
    if (totalParams <= 0L) {
        val m = Regex("(?:^|[-_/])(\\d+(?:\\.\\d+)?)\\s*([bBmMtT])(?:[-_/\\b]|$)").find(repoId)
        if (m != null) {
            val v = m.groupValues[1].toDoubleOrNull() ?: 0.0
            when (m.groupValues[2].uppercase()) {
                "T" -> totalParams = (v * 1_000_000_000_000.0).toLong()
                "B" -> totalParams = (v * 1_000_000_000.0).toLong()
                "M" -> totalParams = (v * 1_000_000.0).toLong()
            }
        }
    }
    val paramLabel = when {
        totalParams >= 1_000_000_000_000L -> String.format(java.util.Locale.US, "%.1fT", totalParams / 1e12)
        totalParams >= 1_000_000_000L -> {
            val b = totalParams / 1e9
            if (b >= 20.0) String.format(java.util.Locale.US, "%.0fB", b)
            else String.format(java.util.Locale.US, "%.1fB", b).replace(".0B", "B")
        }
        totalParams >= 1_000_000L -> String.format(java.util.Locale.US, "%.0fM", totalParams / 1e6)
        else -> ""
    }
    val paramsB = if (totalParams > 0L) totalParams / 1e9 else 0.0
    val pmap = st?.optJSONObject("parameters")
    val estVramGb = when {
        isGguf -> if (paramsB > 0.0) kotlin.math.round((paramsB * 0.62 + 1.2) * 10.0) / 10.0 else 0.0
        pmap != null && pmap.length() > 0 -> {
            var bytesTotal = 0.0
            val keys = pmap.keys()
            while (keys.hasNext()) {
                val dt = keys.next()
                val cnt = pmap.optDouble(dt, 0.0)
                val dtUp = dt.uppercase()
                bytesTotal += when {
                    dtUp.contains("32") -> cnt * 4.0
                    dtUp.contains("16") -> cnt * 2.0
                    dtUp.contains("8") -> cnt * 1.0
                    dtUp.contains("4") -> cnt * 0.55
                    else -> cnt * 2.0
                }
            }
            kotlin.math.round(((bytesTotal / 1e9) * 1.12 + 1.2) * 10.0) / 10.0
        }
        paramsB > 0.0 -> kotlin.math.round((paramsB * 2.1 + 1.2) * 10.0) / 10.0
        else -> 0.0
    }
    val vInt = kotlin.math.max(1, kotlin.math.round(estVramGb).toInt())
    return when {
        !isGguf && ptag in UNSUPPORTED_HF_PIPELINE_TAGS -> HFSizingResult(paramLabel, estVramGb, "too_large", "非内置管线 ($ptag · 需专用SDK)", "Custom Pipeline ($ptag)")
        estVramGb <= 0.0 -> HFSizingResult(paramLabel, 0.0, "unknown", "显存待探测", "VRAM TBD")
        estVramGb <= 14.2 -> HFSizingResult(paramLabel, estVramGb, "great", "适合 · T4(15G)可跑 (~${vInt}G)", "Fit: T4 15G (~${vInt}G)")
        estVramGb <= 22.5 -> HFSizingResult(paramLabel, estVramGb, "good", "适合 · 需L4(24G) (~${vInt}G)", "Fit: L4 24G (~${vInt}G)")
        estVramGb <= 39.0 -> HFSizingResult(paramLabel, estVramGb, "a100", "可部署 · 需A100(40G) (~${vInt}G)", "Fit: A100 40G (~${vInt}G)")
        estVramGb <= 78.0 -> HFSizingResult(paramLabel, estVramGb, "heavy", "需A100(80G) (~${vInt}G)", "Needs A100 80G (~${vInt}G)")
        isGguf && paramsB <= 240.0 -> HFSizingResult(paramLabel, estVramGb, "heavy", "需A100(80G)+CPU卸载 (~${vInt}G)", "A100 80G + Offload (~${vInt}G)")
        else -> HFSizingResult(paramLabel, estVramGb, "too_large", "超单卡上限 (~${vInt}G · 建议搜GGUF)", "Too Large (~${vInt}G · Try GGUF)")
    }
}

data class HFSizingResult(
    val paramLabel: String,
    val estVramGb: Double,
    val deployStatus: String,
    val deployZh: String,
    val deployEn: String
)

data class HFModelWeightFileItem(
    val filename: String,
    val sizeGb: Double,
    val fitStatus: String,
    val fitZh: String,
    val fitEn: String
) {
    val localizedFit: String get() = stripEmoji(L(fitZh, fitEn))
}

data class HFModelDetailInfo(
    val repoId: String,
    val name: String,
    val pipelineTag: String,
    val modality: String,
    val isGguf: Boolean,
    val isGated: Boolean,
    val license: String,
    val baseModel: String,
    val architecture: String,
    val contextLength: Int,
    val likes: Int,
    val downloads: Int,
    val usedStorageGb: Double,
    val paramLabel: String,
    val deployLabelZh: String,
    val deployLabelEn: String,
    val weightFiles: List<HFModelWeightFileItem>,
    val readmeExcerpt: String
) {
    val localizedDeployLabel: String get() = stripEmoji(L(deployLabelZh, deployLabelEn))
}

data class ChatTurnItem(
    val id: String = UUID.randomUUID().toString(),
    val role: String,
    val content: String,
    val thinking: String = "",
    val hasImage: Boolean = false
)

fun JSONObject.optDoubleOrNull(key: String): Double? =
    if (has(key) && !isNull(key)) optDouble(key).takeIf { !it.isNaN() } else null

fun JSONObject.optIntOrNull(key: String): Int? =
    if (has(key) && !isNull(key)) optInt(key) else null

fun JSONObject.optBooleanOrNull(key: String): Boolean? =
    if (has(key) && !isNull(key)) optBoolean(key) else null

fun JSONObject.optStringOrNull(key: String): String? =
    if (has(key) && !isNull(key)) optString(key) else null

fun JSONArray.toStringList(): List<String> = (0 until length()).mapNotNull { optString(it, null) }
