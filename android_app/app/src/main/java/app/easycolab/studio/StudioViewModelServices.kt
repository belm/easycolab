package app.easycolab.studio

import android.app.Activity
import android.app.Application
import android.content.ClipData
import android.content.ClipboardManager
import android.content.ContentValues
import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.ImageDecoder
import android.media.MediaScannerConnection
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import android.util.Base64
import android.widget.Toast
import androidx.browser.customtabs.CustomTabsIntent
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableDoubleStateOf
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.core.content.FileProvider
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.io.File
import java.io.FileOutputStream
import java.net.URI
import java.net.URLEncoder
import java.util.Locale
import java.util.UUID
import java.util.concurrent.TimeUnit

// MARK: - StudioViewModel Extension: Custom HF Repos, ComfyUI & MediaStore Gallery

// MARK: - Custom HuggingFace Repository Registration & Persistence

internal fun StudioViewModel.loadPersistedCustomModels() {
    val raw = prefs.getString("customModelsJsonV1", null) ?: return
    try {
        val arr = JSONArray(raw)
        val list = mutableListOf<OpenModelSpec>()
        for (i in 0 until arr.length()) {
            val obj = arr.optJSONObject(i) ?: continue
            list.add(OpenModelSpec.fromCustomJson(obj))
        }
        customModels = list
    } catch (_: Exception) {
    }
}

internal fun StudioViewModel.savePersistedCustomModels() {
    try {
        val arr = JSONArray()
        customModels.forEach { s ->
            val modStr = when (s.modality) {
                ModelModality.VIDEO_AUDIO -> "video_audio"
                ModelModality.IMAGE -> "image"
                else -> "llm_vlm"
            }
            val obj = JSONObject()
                .put("id", s.id)
                .put("name", s.nameZh)
                .put("repo_id", s.repoId)
                .put("include_pattern", s.includePattern)
                .put("modality", modStr)
                .put("category", s.summaryZh)
                .put("approx_size_gb", s.approxSizeGb)
                .put("is_custom", true)
            arr.put(obj)
        }
        prefs.edit().putString("customModelsJsonV1", arr.toString()).apply()
    } catch (_: Exception) {
    }
}

internal fun StudioViewModel.mergeRemoteCustomModels(remoteArr: JSONArray) {
    val byId = customModels.associateBy { it.id }.toMutableMap()
    val remoteIds = mutableListOf<String>()
    for (i in 0 until remoteArr.length()) {
        val obj = remoteArr.optJSONObject(i) ?: continue
        val spec = OpenModelSpec.fromCustomJson(obj)
        byId[spec.id] = spec
        remoteIds.add(spec.id)
    }
    val ordered = remoteIds + customModels.map { it.id }.filter { it !in remoteIds }
    customModels = ordered.mapNotNull { byId[it] }
    savePersistedCustomModels()
}

internal fun StudioViewModel.normalizeHFRepoId(raw: String): String {
    var s = raw.trim()
    for (prefix in listOf(
        "https://huggingface.co/",
        "http://huggingface.co/",
        "https://hf.co/",
        "http://hf.co/",
        "huggingface.co/",
        "hf.co/"
    )) {
        if (s.lowercase(Locale.US).startsWith(prefix)) {
            s = s.substring(prefix.length)
            break
        }
    }
    val parts = s.trim('/').split('/').filter { it.isNotEmpty() }
    return if (parts.size >= 2) "${parts[0]}/${parts[1]}" else s
}

fun StudioViewModel.fetchTrendingHFModels(
    category: String = trendingHFCategory,
    forceRefresh: Boolean = false,
    searchQuery: String = ""
) {
    val cat = category.trim().lowercase(Locale.US).ifEmpty { "all" }
    val sq = searchQuery.trim()
    trendingHFCategory = cat
    viewModelScope.launch {
        isLoadingTrendingHF = true
        val base = normalizedBaseURL
        val tok = hfToken.trim()
        val results = withContext(Dispatchers.IO) {
            val parsed = mutableListOf<HFTrendingModelItem>()
            if (isConnected && base.isNotEmpty()) {
                try {
                    val encTok = URLEncoder.encode(tok, "UTF-8")
                    val encSq = URLEncoder.encode(sq, "UTF-8")
                    val url = "$base/minimax_api/hf_trending?category=$cat&limit=12&hf_token=$encTok&force_refresh=$forceRefresh&search_query=$encSq"
                    val req = Request.Builder().url(url).get().build()
                    apiClient.newCall(req).execute().use { resp ->
                        if (resp.isSuccessful) {
                            val root = JSONObject(resp.body?.string() ?: "{}")
                            val arr = root.optJSONArray("models")
                            if (arr != null && arr.length() > 0) {
                                for (i in 0 until arr.length()) {
                                    val m = arr.optJSONObject(i) ?: continue
                                    val rid = m.optString("repo_id", "").trim()
                                    if (!rid.contains('/')) continue
                                    val isGguf = m.optBoolean("is_gguf", rid.lowercase(Locale.US).contains("gguf"))
                                    val fallbackSizing = analyzeHFModelSizingJson(m, rid, isGguf)
                                    parsed.add(
                                        HFTrendingModelItem(
                                            repoId = rid,
                                            name = m.optString("name", rid.substringAfterLast('/')),
                                            pipelineTag = m.optString("pipeline_tag", "text-generation"),
                                            modality = m.optString("modality", "llm_vlm"),
                                            isGguf = isGguf,
                                            isGated = m.optBoolean("is_gated", false),
                                            suggestedPattern = m.optString("suggested_pattern", ""),
                                            likes = m.optInt("likes", 0),
                                            downloads = m.optInt("downloads", 0),
                                            paramLabel = m.optString("param_label", fallbackSizing.paramLabel),
                                            estVramGb = m.optDouble("est_vram_gb", fallbackSizing.estVramGb),
                                            deployStatus = m.optString("deploy_status", fallbackSizing.deployStatus),
                                            deployLabelZh = m.optString("deploy_label_zh", fallbackSizing.deployZh),
                                            deployLabelEn = m.optString("deploy_label_en", fallbackSizing.deployEn)
                                        )
                                    )
                                }
                            }
                        }
                    }
                } catch (_: Exception) {
                }
            }
            if (parsed.isNotEmpty()) return@withContext parsed

            val expandQs = "&expand[]=safetensors&expand[]=gguf&expand[]=likes&expand[]=downloads&expand[]=pipeline_tag&expand[]=tags&expand[]=gated"
            val searchQs = if (sq.isNotEmpty()) "&search=${URLEncoder.encode(sq, "UTF-8")}" else ""
            val qpaths = when (cat) {
                "gguf" -> listOf("/api/models?sort=trendingScore&direction=-1&filter=gguf&limit=20$searchQs$expandQs")
                "llm" -> if (sq.isEmpty()) listOf(
                    "/api/models?sort=trendingScore&direction=-1&pipeline_tag=text-generation&limit=18$expandQs",
                    "/api/models?sort=trendingScore&direction=-1&pipeline_tag=image-text-to-text&limit=10$expandQs"
                ) else listOf("/api/models?sort=trendingScore&direction=-1&pipeline_tag=text-generation&limit=20$searchQs$expandQs")
                "image_video" -> listOf(
                    "/api/models?sort=trendingScore&direction=-1&pipeline_tag=text-to-image&limit=12$searchQs$expandQs",
                    "/api/models?sort=trendingScore&direction=-1&pipeline_tag=image-to-video&limit=10$searchQs$expandQs"
                )
                else -> listOf("/api/models?sort=trendingScore&direction=-1&limit=22$searchQs$expandQs")
            }

            val seen = mutableSetOf<String>()
            for (qpath in qpaths) {
                var rawArr: JSONArray? = null
                for (host in listOf("https://huggingface.co", "https://hf-mirror.com")) {
                    try {
                        val rb = Request.Builder()
                            .url("$host$qpath")
                            .header("User-Agent", "EasyColab-Android/2.0")
                            .get()
                        if (tok.isNotEmpty()) {
                            rb.header("Authorization", "Bearer $tok")
                        }
                        apiClient.newCall(rb.build()).execute().use { resp ->
                            if (resp.isSuccessful) {
                                val bodyStr = resp.body?.string() ?: ""
                                if (bodyStr.trim().startsWith("[")) {
                                    rawArr = JSONArray(bodyStr)
                                }
                            }
                        }
                        if (rawArr != null) break
                    } catch (_: Exception) {
                    }
                }
                val arr = rawArr ?: continue
                for (i in 0 until arr.length()) {
                    val item = arr.optJSONObject(i) ?: continue
                    val rid = (item.optStringOrNull("id") ?: item.optStringOrNull("modelId") ?: "").trim()
                    if (!rid.contains('/') || !seen.add(rid)) continue
                    val ridLow = rid.lowercase(Locale.US)
                    val ptag = item.optString("pipeline_tag", "").trim().lowercase(Locale.US)
                    val tags = item.optJSONArray("tags")?.toStringList()?.map { it.lowercase(Locale.US) } ?: emptyList()
                    val isGguf = ridLow.contains("gguf") || tags.contains("gguf")
                    val gatedRaw = item.opt("gated")?.toString()?.lowercase(Locale.US) ?: "false"
                    val isGated = gatedRaw.isNotEmpty() && gatedRaw !in listOf("false", "0", "none", "null")
                    if (sq.isEmpty() && cat == "all" && !isGguf) {
                        if (ptag in UNSUPPORTED_HF_PIPELINE_TAGS) continue
                        if (ptag.isNotEmpty() && ptag !in SUPPORTED_TRENDING_PIPELINE_TAGS) continue
                        if (ptag.isEmpty() && tags.none { it in setOf("transformers", "diffusers", "text-generation") }) continue
                    }
                    val modStr = when {
                        ptag.contains("video") || tags.contains("text-to-video") || tags.contains("image-to-video") -> "video_audio"
                        ptag.contains("text-to-image") || ptag.contains("image-to-image") || (tags.contains("diffusers") && !isGguf) -> "image"
                        else -> "llm_vlm"
                    }
                    val sizing = analyzeHFModelSizingJson(item, rid, isGguf)
                    parsed.add(
                        HFTrendingModelItem(
                            repoId = rid,
                            name = rid.substringAfterLast('/'),
                            pipelineTag = ptag.ifEmpty { if (isGguf) "gguf" else "text-generation" },
                            modality = modStr,
                            isGguf = isGguf,
                            isGated = isGated,
                            suggestedPattern = if (isGguf) "*Q4_K_M*.gguf" else "",
                            likes = item.optInt("likes", 0),
                            downloads = item.optInt("downloads", 0),
                            paramLabel = sizing.paramLabel,
                            estVramGb = sizing.estVramGb,
                            deployStatus = sizing.deployStatus,
                            deployLabelZh = sizing.deployZh,
                            deployLabelEn = sizing.deployEn
                        )
                    )
                    if (parsed.size >= 12) break
                }
                if (parsed.size >= 12) break
            }
            parsed
        }
        if (results.isNotEmpty() || sq.isNotEmpty()) {
            trendingHFModels = results
        }
        isLoadingTrendingHF = false
    }
}

fun StudioViewModel.fetchHFModelDetail(repoIdRaw: String) {
    val cleanId = normalizeHFRepoId(repoIdRaw)
    if (!cleanId.contains('/')) return
    showHFModelDetailDialog = true
    viewModelScope.launch {
        isLoadingHFModelDetail = true
        val tok = hfToken.trim()
        val detail = withContext(Dispatchers.IO) {
            var meta: JSONObject? = null
            for (host in listOf("https://huggingface.co", "https://hf-mirror.com")) {
                try {
                    val rb = Request.Builder()
                        .url("$host/api/models/$cleanId?blobs=true")
                        .header("User-Agent", "EasyColab-Android/2.0")
                        .get()
                    if (tok.isNotEmpty()) rb.header("Authorization", "Bearer $tok")
                    apiClient.newCall(rb.build()).execute().use { resp ->
                        if (resp.isSuccessful) {
                            meta = JSONObject(resp.body?.string() ?: "{}")
                        }
                    }
                    if (meta != null) break
                } catch (_: Exception) {
                }
            }
            val m = meta ?: return@withContext null
            val rid = (m.optStringOrNull("id") ?: m.optStringOrNull("modelId") ?: cleanId).trim()
            val ridLow = rid.lowercase(Locale.US)
            val ptag = m.optString("pipeline_tag", "").trim().lowercase(Locale.US)
            val tags = m.optJSONArray("tags")?.toStringList()?.map { it.lowercase(Locale.US) } ?: emptyList()
            val ggufObj = m.optJSONObject("gguf")
            val isGguf = ridLow.contains("gguf") || tags.contains("gguf") || (ggufObj != null && ggufObj.length() > 0)
            val gatedRaw = m.opt("gated")?.toString()?.lowercase(Locale.US) ?: "false"
            val isGated = gatedRaw.isNotEmpty() && gatedRaw !in listOf("false", "0", "none", "null")
            val modStr = when {
                ptag.contains("video") || tags.contains("text-to-video") || tags.contains("image-to-video") -> "video_audio"
                ptag.contains("text-to-image") || ptag.contains("image-to-image") || (tags.contains("diffusers") && !isGguf) -> "image"
                else -> "llm_vlm"
            }
            val sizing = analyzeHFModelSizingJson(m, rid, isGguf)
            val cardData = m.optJSONObject("cardData")
            val configData = m.optJSONObject("config")
            val lic = cardData?.optString("license", "")?.ifEmpty { "Unspecified" } ?: "Unspecified"
            val baseModel = cardData?.optString("base_model", "") ?: ""
            val archStr = configData?.optJSONArray("architectures")?.optString(0, "")
                ?: ggufObj?.optString("architecture", "")
                ?: configData?.optString("model_type", "")
                ?: ""
            val ctxLen = ggufObj?.optInt("context_length", 0) ?: 0
            val usedStorageGb = kotlin.math.round((m.optDouble("usedStorage", 0.0) / 1_073_741_824.0) * 100.0) / 100.0

            val wfiles = mutableListOf<HFModelWeightFileItem>()
            val sibs = m.optJSONArray("siblings")
            if (sibs != null) {
                for (i in 0 until sibs.length()) {
                    val sib = sibs.optJSONObject(i) ?: continue
                    val fn = sib.optString("rfilename", "").trim()
                    val fl = fn.lowercase(Locale.US)
                    if (!fl.endsWith(".gguf") && !fl.endsWith(".safetensors") && !fl.endsWith(".bin") && !fl.endsWith(".pth")) continue
                    val fBytes = sib.optDouble("size", sib.optJSONObject("lfs")?.optDouble("size", 0.0) ?: 0.0)
                    val sGb = if (fBytes > 0.0) kotlin.math.round((fBytes / 1_073_741_824.0) * 100.0) / 100.0 else 0.0
                    val vNeed = if (sGb > 0.0) kotlin.math.round((sGb * 1.12 + 1.0) * 10.0) / 10.0 else 0.0
                    val (st, zh, en) = when {
                        vNeed <= 0.0 -> Triple("unknown", "体积待测", "Size TBD")
                        vNeed <= 14.5 -> Triple("great", "T4(15G)可跑", "T4 15G Ready")
                        vNeed <= 22.5 -> Triple("good", "L4(24G)可跑", "L4 24G Ready")
                        vNeed <= 39.0 -> Triple("a100", "需A100(40G)", "A100 40G")
                        vNeed <= 78.0 -> Triple("heavy", "需A100(80G)", "A100 80G")
                        else -> Triple("too_large", "超单卡显存", ">80G VRAM")
                    }
                    wfiles.add(HFModelWeightFileItem(fn, sGb, st, zh, en))
                    if (wfiles.size >= 36) break
                }
            }
            var readme = ""
            for (host in listOf("https://huggingface.co", "https://hf-mirror.com")) {
                try {
                    val rb = Request.Builder().url("$host/$rid/raw/main/README.md").get()
                    if (tok.isNotEmpty()) rb.header("Authorization", "Bearer $tok")
                    apiClient.newCall(rb.build()).execute().use { resp ->
                        if (resp.isSuccessful) {
                            var raw = (resp.body?.string() ?: "").take(24000)
                            if (raw.startsWith("---")) {
                                val end = raw.indexOf("\n---", 3)
                                if (end != -1) raw = raw.substring(end + 4)
                            }
                            raw = raw.replace(Regex("<!--[\\s\\S]*?-->"), "")
                                .replace(Regex("<a[^>]*>\\s*<img[^>]*>\\s*</a>", RegexOption.IGNORE_CASE), "")
                                .replace(Regex("<img[^>]*>", RegexOption.IGNORE_CASE), "")
                                .replace(Regex("<h[1-4][^>]*>(.*?)</h[1-4]>", setOf(RegexOption.IGNORE_CASE, RegexOption.DOT_MATCHES_ALL)), "\n### $1\n")
                                .replace(Regex("<[^>]+>"), "")
                                .replace(Regex("\\[!\\[[^\\]]*\\]\\([^\\)]*\\)\\]\\([^\\)]*\\)"), "")
                                .replace(Regex("!\\[[^\\]]*\\]\\([^\\)]*\\)"), "")
                            readme = raw.lines()
                                .map { it.trim() }
                                .filter { it.isNotEmpty() && !it.startsWith("```") && !it.startsWith("|---") && !it.startsWith("| ---") }
                                .joinToString("\n")
                                .take(1200)
                                .replace(Regex("\\[([^\\]]+)\\]\\([^\\)\\n]*$"), "$1")
                        }
                    }
                    if (readme.isNotEmpty()) break
                } catch (_: Exception) {
                }
            }
            HFModelDetailInfo(
                repoId = rid,
                name = rid.substringAfterLast('/'),
                pipelineTag = ptag.ifEmpty { if (isGguf) "gguf" else "text-generation" },
                modality = modStr,
                isGguf = isGguf,
                isGated = isGated,
                license = lic,
                baseModel = baseModel,
                architecture = archStr,
                contextLength = ctxLen,
                likes = m.optInt("likes", 0),
                downloads = m.optInt("downloads", 0),
                usedStorageGb = usedStorageGb,
                paramLabel = sizing.paramLabel,
                deployLabelZh = sizing.deployZh,
                deployLabelEn = sizing.deployEn,
                weightFiles = wfiles,
                readmeExcerpt = readme
            )
        }
        activeHFModelDetail = detail
        isLoadingHFModelDetail = false
    }
}

fun StudioViewModel.registerCustomHFModel(autoDownload: Boolean = false) {
    val repo = normalizeHFRepoId(customRepoInput)
    if (!repo.contains('/') || repo.split('/').size != 2) {
        customModelErrorMessage = L(
            "请输入合法的 HuggingFace 仓库地址（如 unsloth/Qwen3.8-27B-GGUF）",
            "Please enter a valid HuggingFace Repo ID (e.g. unsloth/Qwen3.8-27B-GGUF)"
        )
        return
    }
    customModelErrorMessage = ""
    val inc = customIncludePatternInput.trim()
    val disp = customDisplayNameInput.trim()
    val modPref = customModalityInput

    viewModelScope.launch {
        isRegisteringCustomModel = true
        val base = normalizedBaseURL
        if (isConnected && base.isNotEmpty()) {
            try {
                val body = JSONObject()
                    .put("repo_id", repo)
                    .put("include_pattern", inc)
                    .put("custom_name", disp)
                    .put("display_name", disp)
                    .put("modality", modPref)
                    .put("modality_hint", modPref)
                    .put("hf_token", hfToken.trim())
                val json = postJsonForStatus("$base/minimax_api/custom_model/register", body, timeoutSec = 35L)
                if (json != null) {
                    if (json.optBoolean("action_ok", true) == false) {
                        isRegisteringCustomModel = false
                        customModelErrorMessage = json.optString("action_message", L("解析 HuggingFace 仓库失败", "Failed to resolve HuggingFace repo"))
                        return@launch
                    }
                    applyStatusJson(json)
                    json.optJSONObject("registered_model")?.let { reg ->
                        val spec = OpenModelSpec.fromCustomJson(reg)
                        val updated = customModels.toMutableList()
                        val idx = updated.indexOfFirst { it.id == spec.id }
                        if (idx >= 0) updated[idx] = spec else updated.add(spec)
                        customModels = updated
                        savePersistedCustomModels()
                        switchSelectedModel(spec)
                    }
                    json.optStringOrNull("action_message")?.takeIf { it.isNotEmpty() }?.let { statusMessage = stripEmoji(it) }
                    isRegisteringCustomModel = false
                    showAddCustomModelDialog = false
                    customRepoInput = ""
                    customIncludePatternInput = ""
                    customDisplayNameInput = ""
                    if (autoDownload) startRemoteDownloadWeights()
                    return@launch
                }
            } catch (_: Exception) {
            }
        }

        // Offline / local registration fallback
        val slug = (repo + if (inc.isEmpty()) "" else "_$inc")
            .lowercase(Locale.US)
            .replace(Regex("[^a-z0-9]+"), "_")
            .trim('_')
        val modelId = "custom_" + slug.take(40)
        val resolvedMod = if (modPref == "auto") {
            val lower = "$repo $inc".lowercase(Locale.US)
            when {
                listOf("video", "wan", "ltx", "minimax", "hunyuan").any { lower.contains(it) } -> "video_audio"
                listOf("flux", "image", "sdxl", "z-image").any { lower.contains(it) } -> "image"
                else -> "llm_vlm"
            }
        } else modPref
        val shortName = repo.substringAfterLast('/')
        val finalName = disp.ifEmpty { if (inc.isEmpty()) shortName else "$shortName ($inc)" }
        val archGuess = if (repo.lowercase(Locale.US).contains("gguf") || inc.lowercase(Locale.US).contains(".gguf")) "gguf"
        else if (resolvedMod == "image") "diffusers_image" else "transformers"
        val obj = JSONObject()
            .put("id", modelId)
            .put("name", finalName)
            .put("repo_id", repo)
            .put("include_pattern", inc)
            .put("modality", resolvedMod)
            .put("pipeline_arch", archGuess)
            .put("category", "自定义 HuggingFace 仓库 ($repo)")
            .put("approx_size_gb", 0.0)
            .put("is_custom", true)
        val spec = OpenModelSpec.fromCustomJson(obj)
        val updated = customModels.toMutableList()
        val idx = updated.indexOfFirst { it.id == spec.id }
        if (idx >= 0) updated[idx] = spec else updated.add(spec)
        customModels = updated
        savePersistedCustomModels()
        switchSelectedModel(spec)
        isRegisteringCustomModel = false
        showAddCustomModelDialog = false
        customRepoInput = ""
        customIncludePatternInput = ""
        customDisplayNameInput = ""
        statusMessage = L(
            "已添加自定义模型「$finalName」($repo)，连接 Colab 后即可并发拉取至 Google Drive。",
            "Added custom model '$finalName' ($repo). Connect to Colab to download weights to Google Drive."
        )
    }
}

fun StudioViewModel.removeCustomHFModel(spec: OpenModelSpec) {
    if (!spec.isCustom) return
    customModels = customModels.filter { it.id != spec.id }
    savePersistedCustomModels()
    if (selectedModelId == spec.id) {
        switchSelectedModel(OPEN_MODEL_CATALOG[0])
    }
    val base = normalizedBaseURL
    if (isConnected && base.isNotEmpty()) {
        viewModelScope.launch {
            try {
                val json = postJsonForStatus(
                    "$base/minimax_api/custom_model/remove",
                    JSONObject().put("model_id", spec.id).put("delete_weights", false)
                )
                if (json != null) applyStatusJson(json)
            } catch (_: Exception) {
            }
        }
    }
}


// MARK: - ComfyUI Cloud Actions

fun StudioViewModel.openComfyCanvas(context: Context) {
    if (comfyPublicURL.isNotBlank()) {
        openExternalOrCustomTab(context, comfyPublicURL)
    }
}

fun StudioViewModel.startRemoteComfyUI(forceRestart: Boolean = false) {
    val base = normalizedBaseURL
    if (!isConnected || base.isEmpty()) {
        statusMessage = L("请先唤醒或连接云端实例后再启动 ComfyUI。", "Please connect to a cloud GPU runtime first.")
        return
    }
    viewModelScope.launch {
        comfyStarting = true
        comfyProgress = 0.05f
        statusMessage = L("正在部署云端 ComfyUI 并挂载 Google Drive 持久化...", "Deploying cloud ComfyUI & mounting Google Drive...")
        try {
            val payload = JSONObject()
                .put("unload_existing", comfyUnloadOthersOnStart)
                .put("force_restart", forceRestart)
            postJsonForStatus("$base/minimax_api/comfyui/start", payload)?.let(::applyStatusJson)
            for (i in 0 until 180) {
                delay(1500)
                checkColabStatus(silent = true)
                statusMessage = localizeServerText(comfyStatusMessage)
                if (comfyRunning && comfyPublicURL.isNotEmpty() && !comfyStarting) {
                    showToast(L("ComfyUI 画布已就绪！", "ComfyUI Canvas Ready!"))
                    return@launch
                }
                if (!comfyStarting && !comfyRunning) break
            }
        } catch (e: Exception) {
            comfyStarting = false
            statusMessage = L("启动 ComfyUI 失败: ${e.message}", "Failed to start ComfyUI: ${e.message}")
        }
    }
}

fun StudioViewModel.stopRemoteComfyUI() {
    val base = normalizedBaseURL.takeIf { it.isNotEmpty() && isConnected } ?: return
    viewModelScope.launch {
        try {
            postJsonForStatus("$base/minimax_api/comfyui/stop", JSONObject(), timeoutSec = 35L)
                ?.let(::applyStatusJson)
        } catch (_: Exception) {
        }
    }
}

fun StudioViewModel.syncRemoteComfyUIToDrive() {
    val base = normalizedBaseURL.takeIf { it.isNotEmpty() && isConnected } ?: return
    viewModelScope.launch {
        comfySyncingDrive = true
        try {
            val res = postJsonForStatus("$base/minimax_api/comfyui/sync_drive", JSONObject(), timeoutSec = 90L)
            if (res != null) {
                applyStatusJson(res)
                showToast(L("已同步至 Google Drive", "Synced to Google Drive"))
            } else {
                comfySyncingDrive = false
            }
        } catch (_: Exception) {
            comfySyncingDrive = false
        }
    }
}

fun StudioViewModel.installComfyPresetPack(pack: ComfyPresetPackItem) {
    val base = normalizedBaseURL.takeIf { it.isNotEmpty() && isConnected } ?: return
    viewModelScope.launch {
        comfyDownloadingWeight = true
        comfyInstallingPackId = pack.id
        comfyProgress = 0.04f
        statusMessage = L("正在一键配齐「${pack.localizedTitle}」...", "Installing preset pack \"${pack.localizedTitle}\"...")
        try {
            val payload = JSONObject()
                .put("pack_id", pack.id)
                .put("auto_start", true)
                .put("hf_token", hfToken)
            postJsonForStatus("$base/minimax_api/comfyui/install_pack", payload)?.let(::applyStatusJson)
            for (i in 0 until 600) {
                delay(1500)
                checkColabStatus(silent = true)
                statusMessage = localizeServerText(comfyStatusMessage)
                if (!comfyDownloadingWeight && comfyInstallingPackId.isEmpty() && !comfyStarting) break
            }
        } catch (e: Exception) {
            comfyDownloadingWeight = false
            comfyInstallingPackId = ""
            statusMessage = e.message ?: "Pack install error"
        }
    }
}

fun StudioViewModel.startComfyWeightDownload() {
    val src = comfyWeightSourceInput.trim()
    val base = normalizedBaseURL
    if (src.isEmpty() || !isConnected || base.isEmpty()) return
    viewModelScope.launch {
        comfyDownloadingWeight = true
        try {
            val payload = JSONObject()
                .put("url_or_repo", src)
                .put("filename", comfyWeightFilenameInput.trim())
                .put("subfolder", comfyWeightSubfolder)
                .put("hf_token", hfToken)
            postJsonForStatus("$base/minimax_api/comfyui/download_weight", payload)?.let(::applyStatusJson)
            while (comfyDownloadingWeight && isActive) {
                delay(1500)
                checkColabStatus(silent = true)
            }
        } catch (_: Exception) {
            comfyDownloadingWeight = false
        }
    }
}

fun StudioViewModel.pullComfyOutputToPhone(item: ComfyOutputMediaItem) {
    val base = normalizedBaseURL.takeIf { it.isNotEmpty() } ?: return
    val encodedRel = item.relPath.split("/").joinToString("/") { seg ->
        URLEncoder.encode(seg, "UTF-8").replace("+", "%20")
    }
    val cleanName = item.filename.substringAfterLast('/')
    viewModelScope.launch {
        comfyPullingOutputRelPath = item.relPath
        try {
            downloadMediaToLocal("$base/minimax_api/comfyui/output_media/$encodedRel", "comfy_$cleanName", null)
        } finally {
            comfyPullingOutputRelPath = null
        }
    }
}


// MARK: - Local Gallery, System MediaStore Save & FileProvider Share

fun StudioViewModel.refreshLocalMedia() {
    val validExts = setOf("mp4", "png", "jpg", "jpeg", "webp")
    val elapsedMap = loadElapsedMap()
    val files = localGalleryDir.listFiles().orEmpty()
        .filter { it.isFile && it.extension.lowercase(Locale.US) in validExts }
        .sortedByDescending { it.lastModified() }
        .map { f ->
            LocalMediaItem(
                file = f,
                filename = f.name,
                isImage = !f.extension.equals("mp4", ignoreCase = true),
                createdAtMillis = f.lastModified(),
                elapsedSeconds = elapsedMap[f.name],
                fileSizeMb = f.length().toDouble() / 1_048_576.0
            )
        }
    localMediaItems = files
    if (currentMediaFile != null && currentMediaFile?.exists() != true) {
        currentPreviewBitmap = null
        currentMediaFile = null
    }
    if (currentMediaFile == null && files.isNotEmpty()) {
        selectMedia(files.first().file)
    }
}

fun StudioViewModel.selectMedia(file: File) {
    currentMediaFile = file
    if (file.extension.equals("mp4", ignoreCase = true)) {
        currentPreviewBitmap = null
    } else {
        currentPreviewBitmap = BitmapFactory.decodeFile(file.absolutePath)
    }
}

fun StudioViewModel.deleteLocalMedia(item: LocalMediaItem) {
    deleteLocalMediaFile(item.file)
}

fun StudioViewModel.deleteLocalMediaFile(file: File) {
    val fname = file.name
    if (currentMediaFile?.absolutePath == file.absolutePath) {
        currentPreviewBitmap = null
        currentMediaFile = null
    }
    val map = loadElapsedMap()
    if (map.remove(fname) != null) {
        val obj = JSONObject()
        for ((k, v) in map) obj.put(k, v)
        prefs.edit().putString("mediaElapsedJson", obj.toString()).apply()
    }
    val deleted = !file.exists() || file.delete()
    refreshLocalMedia()
    val msg = if (deleted) {
        L("已从作品库删除: $fname", "Deleted: $fname")
    } else {
        L("删除文件失败: $fname", "Failed to delete: $fname")
    }
    showToast(msg)
    Toast.makeText(appContext, msg, Toast.LENGTH_SHORT).show()
}

internal suspend fun StudioViewModel.downloadMediaToLocal(remoteUrl: String, filename: String, elapsedSeconds: Double?) {
    val cleanFilename = filename.substringAfterLast('/')
    val destFile = File(localGalleryDir, cleanFilename)
    val alreadyExists = destFile.exists()
    try {
        val ok = withContext(Dispatchers.IO) {
            val req = Request.Builder().url(remoteUrl).get().build()
            apiClient.newCall(req).execute().use { resp ->
                if (!resp.isSuccessful) return@withContext false
                val body = resp.body ?: return@withContext false
                val tmpFile = File(localGalleryDir, "$cleanFilename.part")
                FileOutputStream(tmpFile).use { out ->
                    body.byteStream().copyTo(out)
                }
                if (destFile.exists()) destFile.delete()
                tmpFile.renameTo(destFile)
            }
        }
        if (!ok) return
        if (elapsedSeconds != null && elapsedSeconds > 0.0) {
            recordMediaElapsed(cleanFilename, elapsedSeconds)
        }
        refreshLocalMedia()
        selectMedia(destFile)

        if (autoSaveToGallery && !alreadyExists) {
            saveMediaToSystemGallery(destFile, silent = true)
        } else {
            showToast(L("已下载成片: $cleanFilename", "Saved: $cleanFilename"))
        }
    } catch (e: Exception) {
        statusMessage = L("下载成片失败: ${e.message}", "Failed to download media: ${e.message}")
    }
}

fun StudioViewModel.saveMediaToSystemGallery(file: File, silent: Boolean = false) {
    if (!file.exists()) {
        if (!silent) {
            val msg = L("文件不存在或已被删除", "File no longer exists")
            showToast(msg)
            Toast.makeText(appContext, msg, Toast.LENGTH_SHORT).show()
            refreshLocalMedia()
        }
        return
    }
    viewModelScope.launch {
        val isVideo = file.extension.equals("mp4", ignoreCase = true)
        val mimeType = when (file.extension.lowercase(Locale.US)) {
            "mp4" -> "video/mp4"
            "jpg", "jpeg" -> "image/jpeg"
            "webp" -> "image/webp"
            else -> "image/png"
        }
        var errorDetail: String? = null
        val success = withContext(Dispatchers.IO) {
            try {
                val resolver = appContext.contentResolver
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                    val collection = if (isVideo) {
                        MediaStore.Video.Media.getContentUri(MediaStore.VOLUME_EXTERNAL_PRIMARY)
                    } else {
                        MediaStore.Images.Media.getContentUri(MediaStore.VOLUME_EXTERNAL_PRIMARY)
                    }
                    val relDir = if (isVideo) {
                        Environment.DIRECTORY_MOVIES + "/EasyColab"
                    } else {
                        Environment.DIRECTORY_PICTURES + "/EasyColab"
                    }

                    fun buildInsertValues(displayName: String) = ContentValues().apply {
                        put(MediaStore.MediaColumns.DISPLAY_NAME, displayName)
                        put(MediaStore.MediaColumns.MIME_TYPE, mimeType)
                        put(MediaStore.MediaColumns.RELATIVE_PATH, relDir)
                        put(MediaStore.MediaColumns.IS_PENDING, 1)
                    }

                    var itemUri: Uri? = try {
                        resolver.insert(collection, buildInsertValues(file.name))
                    } catch (_: Exception) {
                        null
                    }
                    // Fallback with unique timestamp suffix when MediaStore rejects duplicate DISPLAY_NAME
                    if (itemUri == null) {
                        val ext = file.extension.ifEmpty { if (isVideo) "mp4" else "png" }
                        val uniqueName = "${file.nameWithoutExtension}_${System.currentTimeMillis() % 100000}.$ext"
                        itemUri = resolver.insert(collection, buildInsertValues(uniqueName))
                    }
                    val targetUri = itemUri ?: return@withContext false

                    val outStream = resolver.openOutputStream(targetUri)
                    if (outStream == null) {
                        try { resolver.delete(targetUri, null, null) } catch (_: Exception) {}
                        return@withContext false
                    }
                    outStream.use { out ->
                        file.inputStream().use { it.copyTo(out) }
                    }
                    val finalizeValues = ContentValues().apply {
                        put(MediaStore.MediaColumns.IS_PENDING, 0)
                    }
                    resolver.update(targetUri, finalizeValues, null, null)
                    true
                } else {
                    val pubRoot = Environment.getExternalStoragePublicDirectory(
                        if (isVideo) Environment.DIRECTORY_MOVIES else Environment.DIRECTORY_PICTURES
                    )
                    val dstDir = File(pubRoot, "EasyColab").apply { mkdirs() }
                    val dst = File(dstDir, file.name)
                    file.copyTo(dst, overwrite = true)
                    MediaScannerConnection.scanFile(appContext, arrayOf(dst.absolutePath), arrayOf(mimeType), null)
                    true
                }
            } catch (e: Exception) {
                errorDetail = e.message
                false
            }
        }
        if (success) {
            val msg = if (isVideo) {
                L("视频已存入系统相册！", "Video saved to Android Gallery!")
            } else {
                L("高清图已存入系统相册！", "Image saved to Android Gallery!")
            }
            showToast(msg)
            if (!silent) {
                Toast.makeText(appContext, msg, Toast.LENGTH_SHORT).show()
            }
        } else if (!silent) {
            val msg = if (!errorDetail.isNullOrBlank()) {
                L("保存到系统相册失败: $errorDetail", "Failed to save to Gallery: $errorDetail")
            } else {
                L("保存到系统相册失败", "Failed to save to Android Gallery")
            }
            showToast(msg)
            Toast.makeText(appContext, msg, Toast.LENGTH_SHORT).show()
        }
    }
}

fun StudioViewModel.shareMediaFile(context: Context, file: File) {
    if (!file.exists()) {
        val msg = L("文件不存在或已被删除", "File no longer exists")
        showToast(msg)
        Toast.makeText(appContext, msg, Toast.LENGTH_SHORT).show()
        refreshLocalMedia()
        return
    }
    try {
        val uri = FileProvider.getUriForFile(context, "${context.packageName}.fileprovider", file)
        val mimeType = when (file.extension.lowercase(Locale.US)) {
            "mp4" -> "video/mp4"
            "jpg", "jpeg" -> "image/jpeg"
            "webp" -> "image/webp"
            "png" -> "image/png"
            else -> "image/*"
        }
        val clip = ClipData.newRawUri(file.name, uri)
        val shareIntent = Intent(Intent.ACTION_SEND).apply {
            type = mimeType
            putExtra(Intent.EXTRA_STREAM, uri)
            clipData = clip
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        }
        val chooser = Intent.createChooser(shareIntent, file.name).apply {
            clipData = clip
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            if (context !is Activity) {
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
        }
        context.startActivity(chooser)
    } catch (e: Exception) {
        val msg = L("拉起系统分享失败: ${e.message}", "Share failed: ${e.message}")
        showToast(msg)
        Toast.makeText(appContext, msg, Toast.LENGTH_SHORT).show()
    }
}

fun StudioViewModel.shareBundledNotebook(context: Context) {
    viewModelScope.launch {
        try {
            val outFile = withContext(Dispatchers.IO) {
                val sharedDir = File(appContext.cacheDir, "shared_exports").apply { mkdirs() }
                val dst = File(sharedDir, "EasyColab_Server.ipynb")
                appContext.assets.open("EasyColab_Server.ipynb").use { input ->
                    FileOutputStream(dst).use { out -> input.copyTo(out) }
                }
                dst
            }
            val uri = FileProvider.getUriForFile(context, "${context.packageName}.fileprovider", outFile)
            val clip = ClipData.newRawUri("EasyColab_Server.ipynb", uri)
            val intent = Intent(Intent.ACTION_SEND).apply {
                type = "application/x-ipynb+json"
                putExtra(Intent.EXTRA_STREAM, uri)
                clipData = clip
                addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            }
            val chooser = Intent.createChooser(intent, "EasyColab_Server.ipynb").apply {
                clipData = clip
                addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                if (context !is Activity) {
                    addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                }
            }
            context.startActivity(chooser)
        } catch (e: Exception) {
            showToast(L("导出 Notebook 失败: ${e.message}", "Export failed: ${e.message}"))
        }
    }
}
