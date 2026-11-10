package app.easycolab.studio

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.HelpOutline
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.AddPhotoAlternate
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.Bolt
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Cloud
import androidx.compose.material.icons.filled.CloudDownload
import androidx.compose.material.icons.filled.CloudOff
import androidx.compose.material.icons.filled.CloudSync
import androidx.compose.material.icons.filled.ContentCopy
import androidx.compose.material.icons.filled.DeleteSweep
import androidx.compose.material.icons.filled.Download
import androidx.compose.material.icons.filled.ExpandLess
import androidx.compose.material.icons.filled.ExpandMore
import androidx.compose.material.icons.filled.Key
import androidx.compose.material.icons.filled.Link
import androidx.compose.material.icons.filled.OpenInBrowser
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.PowerSettingsNew
import androidx.compose.material.icons.filled.Psychology
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Share
import androidx.compose.material.icons.filled.Stop
import androidx.compose.material.icons.filled.Tune
import androidx.compose.material.icons.filled.Visibility
import androidx.compose.material.icons.filled.VisibilityOff
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.FilterChip
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Slider
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import java.util.Locale

data class DropdownChoice<T>(
    val value: T,
    val label: String
)

/**
 * Guaranteed single-line non-wrapping dropdown trigger pill so long GPU names
 * ("G4 · RTX PRO 6000 (96GB)") and resolutions never wrap onto 2 lines.
 */
@Composable
fun <T> SingleLineDropdownPill(
    selectedLabel: String,
    options: List<DropdownChoice<T>>,
    onSelect: (T) -> Unit,
    modifier: Modifier = Modifier
) {
    var expanded by remember { mutableStateOf(false) }

    Box(modifier = modifier) {
        Surface(
            shape = RoundedCornerShape(10.dp),
            color = MaterialTheme.colorScheme.primary.copy(alpha = 0.10f),
            border = BorderStroke(1.dp, MaterialTheme.colorScheme.primary.copy(alpha = 0.25f)),
            modifier = Modifier
                .fillMaxWidth()
                .clickable { expanded = true }
        ) {
            Row(
                modifier = Modifier.padding(horizontal = 12.dp, vertical = 9.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Text(
                    text = selectedLabel,
                    style = MaterialTheme.typography.bodySmall,
                    fontWeight = FontWeight.SemiBold,
                    color = MaterialTheme.colorScheme.primary,
                    maxLines = 1,
                    softWrap = false,
                    overflow = TextOverflow.Ellipsis,
                    modifier = Modifier.weight(1f)
                )
                Spacer(Modifier.width(4.dp))
                Icon(
                    imageVector = Icons.Default.ExpandMore,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.primary,
                    modifier = Modifier.size(16.dp)
                )
            }
        }

        DropdownMenu(
            expanded = expanded,
            onDismissRequest = { expanded = false }
        ) {
            options.forEach { opt ->
                DropdownMenuItem(
                    text = {
                        Text(
                            text = opt.label,
                            maxLines = 1,
                            softWrap = false,
                            overflow = TextOverflow.Ellipsis
                        )
                    },
                    onClick = {
                        expanded = false
                        onSelect(opt.value)
                    }
                )
            }
        }
    }
}

// ============================================================================
// TAB 1: CREATE WORKSPACE
// ============================================================================

@Composable
fun CreateTabScreen(vm: StudioViewModel) {
    val context = LocalContext.current
    val spec = vm.activeModelSpec

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background),
        contentPadding = PaddingValues(horizontal = 14.dp, vertical = 10.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        // 1. Full-width non-wrapping header bar (prevents top-left truncation on compact screens)
        item {
            CreateTopHeaderBar(
                vm = vm,
                onTapStatus = { vm.selectedTab = AppTab.CLOUD },
                onToggleLanguage = { LanguageManager.toggle(context) }
            )
        }

        // 2. Horizontal 6-model engine selector strip
        item {
            ModelCatalogStrip(vm = vm)
        }

        // 3. Model VRAM Readiness Card (for all non-ComfyUI models)
        if (spec.modality != ModelModality.COMFY_UI) {
            item {
                ModelVramReadinessCard(vm = vm)
            }
        }

        // 4. Modality-specific studio panels
        when (spec.modality) {
            ModelModality.VIDEO_AUDIO, ModelModality.IMAGE -> {
                item { VideoAndImageWorkspaceSection(vm = vm) }
                if (vm.currentMediaFile != null) {
                    item { MediaStageCard(vm = vm) }
                }
            }
            ModelModality.LLM_VLM -> {
                item { QwenLlmWorkspaceSection(vm = vm) }
            }
            ModelModality.COMFY_UI -> {
                item { ComfyStudioWorkspaceSection(vm = vm) }
                if (vm.currentMediaFile != null) {
                    item { MediaStageCard(vm = vm) }
                }
            }
        }

        // 5. Status footer bar
        item {
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(12.dp),
                colors = CardDefaults.cardColors(
                    containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.55f)
                )
            ) {
                Text(
                    text = vm.statusMessage,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(horizontal = 12.dp, vertical = 10.dp)
                )
            }
        }
    }
}

@Composable
private fun CreateTopHeaderBar(
    vm: StudioViewModel,
    onTapStatus: () -> Unit,
    onToggleLanguage: () -> Unit
) {
    val shortGpu = when {
        !vm.isConnected -> L("未连接", "Offline")
        vm.gpuName.contains("PRO 6000", ignoreCase = true) || vm.gpuName.contains("G4") -> "G4"
        vm.gpuName.contains("H100", ignoreCase = true) -> "H100"
        vm.gpuName.contains("A100", ignoreCase = true) -> "A100"
        vm.gpuName.contains("L4", ignoreCase = true) -> "L4"
        vm.gpuName.contains("T4", ignoreCase = true) -> "T4"
        else -> vm.gpuName.split(" ").firstOrNull().orEmpty().take(8)
    }
    val chipLabel = if (vm.isConnected) {
        "$shortGpu · ${String.format(Locale.US, "%.0fG", vm.vramFreeGB)}"
    } else {
        shortGpu
    }

    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 2.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(
            text = "EasyColab",
            style = MaterialTheme.typography.titleMedium,
            fontWeight = FontWeight.Bold,
            maxLines = 1,
            softWrap = false
        )
        Spacer(Modifier.width(8.dp))

        Surface(
            shape = CircleShape,
            color = if (vm.isConnected) Color(0xFF10B981).copy(alpha = 0.14f)
            else MaterialTheme.colorScheme.surfaceVariant,
            modifier = Modifier.clickable { onTapStatus() }
        ) {
            Row(
                modifier = Modifier.padding(horizontal = 9.dp, vertical = 4.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Box(
                    modifier = Modifier
                        .size(7.dp)
                        .clip(CircleShape)
                        .background(if (vm.isConnected) Color(0xFF10B981) else Color(0xFF9CA3AF))
                )
                Spacer(Modifier.width(5.dp))
                Text(
                    text = chipLabel,
                    fontSize = 11.sp,
                    fontWeight = FontWeight.SemiBold,
                    maxLines = 1,
                    softWrap = false,
                    overflow = TextOverflow.Ellipsis
                )
            }
        }

        Spacer(Modifier.weight(1f))

        IconButton(
            onClick = { vm.updateMaskServerURL(!vm.maskServerURL) },
            modifier = Modifier.size(34.dp)
        ) {
            Icon(
                imageVector = if (vm.maskServerURL) Icons.Default.VisibilityOff else Icons.Default.Visibility,
                contentDescription = "Privacy Mask",
                tint = if (vm.maskServerURL) Color(0xFFF59E0B) else MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.size(18.dp)
            )
        }

        Spacer(Modifier.width(4.dp))

        Surface(
            shape = CircleShape,
            color = MaterialTheme.colorScheme.surfaceVariant,
            modifier = Modifier.clickable { onToggleLanguage() }
        ) {
            Text(
                text = if (LanguageManager.isEN) "中文" else "EN",
                fontSize = 11.sp,
                fontWeight = FontWeight.Bold,
                maxLines = 1,
                softWrap = false,
                modifier = Modifier.padding(horizontal = 10.dp, vertical = 5.dp)
            )
        }
    }
}

@Composable
private fun ModelCatalogStrip(vm: StudioViewModel) {
    if (vm.showAddCustomModelDialog) {
        AddCustomHFModelDialog(vm = vm)
    }

    Row(
        modifier = Modifier
            .fillMaxWidth()
            .horizontalScroll(rememberScrollState()),
        horizontalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        vm.allAvailableModels.forEach { item ->
            val selected = vm.selectedModelId == item.id
            val resident = vm.loadedModelIds.contains(item.id) || (item.id == "comfyui_studio" && vm.comfyRunning)
            Surface(
                shape = RoundedCornerShape(14.dp),
                color = if (selected) MaterialTheme.colorScheme.primary
                else MaterialTheme.colorScheme.surface,
                border = if (selected) null else BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
                modifier = Modifier.clickable { vm.switchSelectedModel(item) }
            ) {
                Column(
                    modifier = Modifier
                        .width(150.dp)
                        .padding(horizontal = 11.dp, vertical = 9.dp),
                    verticalArrangement = Arrangement.spacedBy(3.dp)
                ) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        if (resident) {
                            Box(
                                modifier = Modifier
                                    .size(7.dp)
                                    .clip(CircleShape)
                                    .background(if (selected) Color(0xFFA7F3D0) else Color(0xFF10B981))
                            )
                            Spacer(Modifier.width(5.dp))
                        }
                        Text(
                            text = item.shortTitle,
                            fontSize = 13.sp,
                            fontWeight = FontWeight.Bold,
                            color = if (selected) MaterialTheme.colorScheme.onPrimary
                            else MaterialTheme.colorScheme.onSurface,
                            maxLines = 1,
                            softWrap = false,
                            overflow = TextOverflow.Ellipsis,
                            modifier = Modifier.weight(1f)
                        )
                        if (item.isCustom) {
                            Icon(
                                imageVector = Icons.Default.Close,
                                contentDescription = "Remove",
                                tint = if (selected) MaterialTheme.colorScheme.onPrimary.copy(alpha = 0.8f)
                                else MaterialTheme.colorScheme.onSurfaceVariant,
                                modifier = Modifier
                                    .size(14.dp)
                                    .clickable { vm.removeCustomHFModel(item) }
                            )
                        }
                    }
                    Text(
                        text = item.badge,
                        fontSize = 10.sp,
                        color = if (selected) MaterialTheme.colorScheme.onPrimary.copy(alpha = 0.85f)
                        else MaterialTheme.colorScheme.onSurfaceVariant,
                        maxLines = 1,
                        softWrap = false,
                        overflow = TextOverflow.Ellipsis
                    )
                }
            }
        }

        // + Add Custom HuggingFace Repo Chip
        Surface(
            shape = RoundedCornerShape(14.dp),
            color = MaterialTheme.colorScheme.primary.copy(alpha = 0.08f),
            border = BorderStroke(1.dp, MaterialTheme.colorScheme.primary.copy(alpha = 0.35f)),
            modifier = Modifier.clickable {
                vm.customModelErrorMessage = ""
                vm.showAddCustomModelDialog = true
            }
        ) {
            Column(
                modifier = Modifier
                    .width(142.dp)
                    .padding(horizontal = 11.dp, vertical = 9.dp),
                verticalArrangement = Arrangement.spacedBy(3.dp)
            ) {
                Text(
                    text = L("+ 自定义模型", "+ Custom HF"),
                    fontSize = 13.sp,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.primary,
                    maxLines = 1,
                    softWrap = false
                )
                Text(
                    text = L("导入任意 HF 仓库", "Import HF Repo"),
                    fontSize = 10.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 1,
                    softWrap = false
                )
            }
        }
    }
}

@Composable
private fun AddCustomHFModelDialog(vm: StudioViewModel) {
    val context = LocalContext.current
    val trendingTabs = listOf(
        "all" to L("综合热榜", "Trending"),
        "gguf" to L("GGUF", "GGUF"),
        "llm" to L("对话/视觉", "LLM/VLM"),
        "image_video" to L("生图/视频", "Img/Vid")
    )

    androidx.compose.runtime.LaunchedEffect(Unit) {
        if (vm.trendingHFModels.isEmpty()) {
            vm.fetchTrendingHFModels()
        }
    }

    AlertDialog(
        onDismissRequest = { vm.showAddCustomModelDialog = false },
        title = {
            Text(
                text = L("添加自定义 HuggingFace 模型", "Add Custom HuggingFace Repo"),
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold
            )
        },
        text = {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .verticalScroll(rememberScrollState()),
                verticalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                Text(
                    text = L(
                        "支持从下方实时拉取 HuggingFace 热门趋势模型一键填入，或输入任意 Repo ID。若为受限模型 (Gated Repo)，请填写 HF Token 并同意模型页协议。",
                        "Pick from live HuggingFace trending models below or enter any Repo ID. For gated/private repos, enter your HF Token and accept the license on HuggingFace."
                    ),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )

                // Live HuggingFace Trending & Search Section
                var hfSearchQuery by remember { mutableStateOf("") }
                Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = L("HuggingFace 实时热榜与搜索", "Live HuggingFace Trending & Search"),
                            fontSize = 12.sp,
                            fontWeight = FontWeight.Bold
                        )
                        TextButton(
                            onClick = { vm.fetchTrendingHFModels(vm.trendingHFCategory, forceRefresh = true, searchQuery = hfSearchQuery) },
                            contentPadding = PaddingValues(horizontal = 8.dp, vertical = 2.dp)
                        ) {
                            Text(
                                text = if (vm.isLoadingTrendingHF) L("拉取中...", "Loading...") else L("刷新", "Refresh"),
                                fontSize = 11.sp
                            )
                        }
                    }

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(6.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        OutlinedTextField(
                            value = hfSearchQuery,
                            onValueChange = { hfSearchQuery = it },
                            placeholder = { Text(L("搜索 HF 模型 (如 Qwen3 GGUF)...", "Search HF models..."), fontSize = 11.sp) },
                            singleLine = true,
                            modifier = Modifier.weight(1f)
                        )
                        FilledTonalButton(
                            onClick = { vm.fetchTrendingHFModels(vm.trendingHFCategory, forceRefresh = true, searchQuery = hfSearchQuery) },
                            contentPadding = PaddingValues(horizontal = 10.dp, vertical = 8.dp)
                        ) {
                            Text(L("搜索", "Search"), fontSize = 11.sp)
                        }
                    }

                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .horizontalScroll(rememberScrollState()),
                        horizontalArrangement = Arrangement.spacedBy(6.dp)
                    ) {
                        trendingTabs.forEach { (catId, catLabel) ->
                            FilterChip(
                                selected = vm.trendingHFCategory == catId,
                                onClick = { vm.fetchTrendingHFModels(catId, forceRefresh = false, searchQuery = hfSearchQuery) },
                                label = { Text(catLabel, fontSize = 11.sp) }
                            )
                        }
                    }

                    if (vm.trendingHFModels.isEmpty()) {
                        Text(
                            text = if (vm.isLoadingTrendingHF) L("正在从 HuggingFace 实时拉取模型及参数量/显存评估...", "Fetching models, parameter counts & Colab VRAM fit...")
                            else L("未找到匹配模型，可点击「刷新」或更换搜索词。", "No models found. Tap 'Refresh' or try another keyword."),
                            fontSize = 11.sp,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    } else {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .horizontalScroll(rememberScrollState()),
                            horizontalArrangement = Arrangement.spacedBy(8.dp)
                        ) {
                            vm.trendingHFModels.forEach { item ->
                                val isSel = vm.customRepoInput == item.repoId
                                Surface(
                                    shape = RoundedCornerShape(10.dp),
                                    color = if (isSel) MaterialTheme.colorScheme.primary.copy(alpha = 0.14f)
                                    else MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.55f),
                                    border = BorderStroke(
                                        1.dp,
                                        if (isSel) MaterialTheme.colorScheme.primary else Color.Transparent
                                    ),
                                    modifier = Modifier
                                        .width(198.dp)
                                        .clickable {
                                            vm.customRepoInput = item.repoId
                                            vm.customIncludePatternInput = item.suggestedPattern
                                            vm.customDisplayNameInput = item.name
                                            vm.customModalityInput = item.modality
                                        }
                                ) {
                                    Column(
                                        modifier = Modifier.padding(horizontal = 10.dp, vertical = 7.dp),
                                        verticalArrangement = Arrangement.spacedBy(2.dp)
                                    ) {
                                        Text(
                                            text = (if (item.isGated) L("[受限] ", "[Gated] ") else "") + item.name + (if (item.paramLabel.isNotEmpty()) " · ${item.paramLabel}" else ""),
                                            fontSize = 12.sp,
                                            fontWeight = FontWeight.Bold,
                                            maxLines = 1,
                                            overflow = TextOverflow.Ellipsis
                                        )
                                        Text(
                                            text = item.repoId,
                                            fontSize = 10.sp,
                                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                                            maxLines = 1,
                                            overflow = TextOverflow.Ellipsis
                                        )
                                        Text(
                                            text = "${if (item.isGguf) "GGUF" else item.pipelineTag} · Likes ${item.likes}",
                                            fontSize = 10.sp,
                                            color = MaterialTheme.colorScheme.primary,
                                            maxLines = 1
                                        )
                                        Row(
                                            modifier = Modifier.fillMaxWidth(),
                                            horizontalArrangement = Arrangement.SpaceBetween,
                                            verticalAlignment = Alignment.CenterVertically
                                        ) {
                                            Text(
                                                text = item.localizedDeployLabel,
                                                fontSize = 10.sp,
                                                fontWeight = FontWeight.SemiBold,
                                                maxLines = 1,
                                                overflow = TextOverflow.Ellipsis,
                                                modifier = Modifier.weight(1f)
                                            )
                                            Text(
                                                text = L("详情", "Details"),
                                                fontSize = 10.sp,
                                                fontWeight = FontWeight.Bold,
                                                color = MaterialTheme.colorScheme.primary,
                                                modifier = Modifier
                                                    .clickable {
                                                        vm.customRepoInput = item.repoId
                                                        vm.customIncludePatternInput = item.suggestedPattern
                                                        vm.customDisplayNameInput = item.name
                                                        vm.customModalityInput = item.modality
                                                        vm.fetchHFModelDetail(item.repoId)
                                                    }
                                                    .padding(start = 4.dp)
                                            )
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                if (vm.showHFModelDetailDialog) {
                    AlertDialog(
                        onDismissRequest = { vm.showHFModelDetailDialog = false },
                        title = {
                            Text(
                                text = vm.activeHFModelDetail?.name ?: L("模型详情", "Model Details"),
                                style = MaterialTheme.typography.titleMedium,
                                fontWeight = FontWeight.Bold
                            )
                        },
                        text = {
                            Column(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .verticalScroll(rememberScrollState()),
                                verticalArrangement = Arrangement.spacedBy(8.dp)
                            ) {
                                if (vm.isLoadingHFModelDetail) {
                                    Text(L("正在从 HuggingFace 解析模型详情与分片体积...", "Inspecting HuggingFace model metadata & shards..."), fontSize = 12.sp)
                                } else {
                                    val d = vm.activeHFModelDetail
                                    if (d == null) {
                                        Text(L("无法获取该模型详情", "Failed to load model details"), fontSize = 12.sp)
                                    } else {
                                        Text("${d.repoId}  ·  ${d.paramLabel.ifEmpty { "N/A" }}  ·  ${d.localizedDeployLabel}", fontSize = 11.sp, fontWeight = FontWeight.SemiBold)
                                        Text("Arch: ${d.architecture.ifEmpty { d.pipelineTag }} | License: ${stripEmoji(d.license)} | Likes ${d.likes}", fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                        if (d.weightFiles.isNotEmpty()) {
                                            Text(L("权重与量化分片 (点击即可选用):", "Weight Shards (Tap to Select):"), fontSize = 11.sp, fontWeight = FontWeight.Bold)
                                            d.weightFiles.take(16).forEach { wf ->
                                                Surface(
                                                    shape = RoundedCornerShape(8.dp),
                                                    color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.6f),
                                                    modifier = Modifier
                                                        .fillMaxWidth()
                                                        .clickable {
                                                            vm.customRepoInput = d.repoId
                                                            vm.customIncludePatternInput = wf.filename
                                                            vm.customDisplayNameInput = d.name
                                                            vm.customModalityInput = d.modality
                                                            vm.showHFModelDetailDialog = false
                                                        }
                                                ) {
                                                    Column(modifier = Modifier.padding(horizontal = 8.dp, vertical = 5.dp)) {
                                                        Text(wf.filename, fontSize = 10.sp, fontFamily = FontFamily.Monospace, maxLines = 1, overflow = TextOverflow.Ellipsis)
                                                        Text("${String.format(java.util.Locale.US, "%.2f GB", wf.sizeGb)} · ${wf.localizedFit}", fontSize = 10.sp, color = MaterialTheme.colorScheme.primary)
                                                    }
                                                }
                                            }
                                        }
                                        if (d.readmeExcerpt.isNotEmpty()) {
                                            Text(L("模型说明摘要:", "README Excerpt:"), fontSize = 11.sp, fontWeight = FontWeight.Bold)
                                            Text(
                                                text = formatHFMarkdownForAndroid(
                                                    d.readmeExcerpt,
                                                    primaryColor = MaterialTheme.colorScheme.onSurface,
                                                    linkColor = MaterialTheme.colorScheme.primary
                                                ),
                                                fontSize = 10.sp,
                                                color = MaterialTheme.colorScheme.onSurfaceVariant
                                            )
                                        }
                                    }
                                }
                            }
                        },
                        confirmButton = {
                            TextButton(onClick = { vm.showHFModelDetailDialog = false }) {
                                Text(L("关闭", "Close"))
                            }
                        }
                    )
                }

                OutlinedTextField(
                    value = vm.customRepoInput,
                    onValueChange = { vm.customRepoInput = it },
                    label = { Text(L("HuggingFace Repo ID 或 URL", "HuggingFace Repo ID or URL")) },
                    placeholder = { Text(L("从上方实时热榜点选，或输入 owner/repo", "Pick from live trending above or enter owner/repo")) },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )

                OutlinedTextField(
                    value = vm.customIncludePatternInput,
                    onValueChange = { vm.customIncludePatternInput = it },
                    label = { Text(L("文件名过滤 (Include Pattern，可选)", "Include Pattern (Optional)")) },
                    placeholder = { Text("*Q4_K_M*.gguf / *.safetensors") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )

                OutlinedTextField(
                    value = vm.customDisplayNameInput,
                    onValueChange = { vm.customDisplayNameInput = it },
                    label = { Text(L("自定义显示名称 (可选)", "Display Name (Optional)")) },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )

                SingleLineDropdownPill(
                    selectedLabel = when (vm.customModalityInput) {
                        "llm_vlm" -> L("模态: 对话 / 视觉 / API", "Modality: Chat / Vision / API")
                        "image" -> L("模态: 图像生成 / 编辑", "Modality: Image Generation")
                        "video_audio" -> L("模态: 音视频生成", "Modality: Video + Audio")
                        else -> L("模态: 自动识别 (推荐)", "Modality: Auto-detect")
                    },
                    options = listOf(
                        DropdownChoice("auto", L("自动识别 (推荐)", "Auto-detect")),
                        DropdownChoice("llm_vlm", L("对话 / 视觉 / API (LLM/VLM)", "Chat / Vision / API")),
                        DropdownChoice("image", L("图像生成 / 编辑 (Image)", "Image Generation")),
                        DropdownChoice("video_audio", L("音视频生成 (Video+Audio)", "Video + Audio"))
                    ),
                    onSelect = { vm.customModalityInput = it }
                )

                OutlinedTextField(
                    value = vm.hfToken,
                    onValueChange = { vm.updateHfToken(it) },
                    label = { Text(L("HuggingFace Token (受限/需登录模型必填)", "HF Token (Required for Gated Repos)")) },
                    placeholder = { Text("hf_xxxxxxxxxxxxxxxxxxxxxxxx") },
                    visualTransformation = PasswordVisualTransformation(),
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    TextButton(
                        onClick = { vm.openExternalOrCustomTab(context, "https://huggingface.co/settings/tokens") },
                        contentPadding = PaddingValues(horizontal = 6.dp, vertical = 2.dp)
                    ) {
                        Text(L("🔑 获取 HF Token", "🔑 Get HF Token"), fontSize = 11.sp)
                    }
                    TextButton(
                        onClick = {
                            val clean = vm.customRepoInput.trim()
                            val url = if (clean.contains('/')) "https://huggingface.co/$clean"
                            else "https://huggingface.co/models?sort=trending"
                            vm.openExternalOrCustomTab(context, url)
                        },
                        contentPadding = PaddingValues(horizontal = 6.dp, vertical = 2.dp)
                    ) {
                        Text(L("🌐 打开模型页同意协议", "🌐 Open Repo & Agree"), fontSize = 11.sp)
                    }
                }

                if (vm.customModelErrorMessage.isNotEmpty()) {
                    Text(
                        text = vm.customModelErrorMessage,
                        color = MaterialTheme.colorScheme.error,
                        style = MaterialTheme.typography.bodySmall
                    )
                }
            }
        },
        confirmButton = {
            Button(
                onClick = { vm.registerCustomHFModel(autoDownload = vm.isConnected) },
                enabled = !vm.isRegisteringCustomModel && vm.customRepoInput.trim().isNotEmpty()
            ) {
                Text(
                    if (vm.isConnected) L("添加并拉取权重", "Add & Download")
                    else L("添加到模型中心", "Add Model")
                )
            }
        },
        dismissButton = {
            TextButton(onClick = { vm.showAddCustomModelDialog = false }) {
                Text(L("取消", "Cancel"))
            }
        }
    )
}

private fun formatHFMarkdownForAndroid(
    raw: String,
    primaryColor: Color,
    linkColor: Color
): AnnotatedString = buildAnnotatedString {
    val lines = raw
        .replace(Regex("\\[([^\\]]+)\\]\\([^\\)\\n]*$"), "$1")
        .lines()
        .map { it.trim() }
        .filter { it.isNotEmpty() }

    val tokenRegex = Regex("\\*\\*([^*]+)\\*\\*|`([^`]+)`|\\[([^\\]]+)\\]\\(([^\\)]+)\\)")

    lines.forEachIndexed { idx, line ->
        if (idx > 0) append("\n")
        val isHeading = line.startsWith("#") || (idx == 0 && line.length <= 60 && !line.endsWith(".") && !line.endsWith("。") && !line.startsWith("**"))
        val cleanLine = when {
            line.startsWith("#") -> line.trimStart('#', ' ')
            line.startsWith("- ") || line.startsWith("* ") || line.startsWith("+ ") -> "• " + line.substring(2).trimStart()
            line.startsWith(">") -> "▎ " + line.trimStart('>', ' ')
            else -> line
        }

        if (isHeading) {
            withStyle(SpanStyle(fontWeight = FontWeight.Bold, color = primaryColor)) {
                append(cleanLine.replace("**", "").replace("`", ""))
            }
        } else {
            var cursor = 0
            for (m in tokenRegex.findAll(cleanLine)) {
                if (m.range.first > cursor) {
                    append(cleanLine.substring(cursor, m.range.first))
                }
                val boldTxt = m.groups[1]?.value
                val codeTxt = m.groups[2]?.value
                val linkLbl = m.groups[3]?.value
                when {
                    boldTxt != null -> withStyle(SpanStyle(fontWeight = FontWeight.Bold, color = primaryColor)) {
                        append(boldTxt)
                    }
                    codeTxt != null -> withStyle(SpanStyle(fontFamily = FontFamily.Monospace, color = primaryColor)) {
                        append(codeTxt)
                    }
                    linkLbl != null -> withStyle(SpanStyle(color = linkColor, fontWeight = FontWeight.SemiBold, textDecoration = TextDecoration.Underline)) {
                        append(linkLbl)
                    }
                }
                cursor = m.range.last + 1
            }
            if (cursor < cleanLine.length) {
                append(cleanLine.substring(cursor).replace("**", ""))
            }
        }
    }
}

@Composable
private fun ModelVramReadinessCard(vm: StudioViewModel) {
    val spec = vm.activeModelSpec
    var showShards by remember { mutableStateOf(false) }

    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
    ) {
        Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = spec.name,
                        style = MaterialTheme.typography.titleSmall,
                        fontWeight = FontWeight.Bold,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis
                    )
                    Text(
                        text = spec.summary,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        maxLines = 2,
                        overflow = TextOverflow.Ellipsis
                    )
                }
                Spacer(Modifier.width(8.dp))
                Surface(
                    shape = CircleShape,
                    color = if (vm.isSelectedModelLoadedInVRAM) Color(0xFF10B981).copy(alpha = 0.16f)
                    else MaterialTheme.colorScheme.surfaceVariant
                ) {
                    Text(
                        text = if (vm.isSelectedModelLoadedInVRAM) L("已驻留显存", "In VRAM")
                        else "${vm.downloadedCount}/${vm.totalFileCount}",
                        fontSize = 11.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = if (vm.isSelectedModelLoadedInVRAM) Color(0xFF059669)
                        else MaterialTheme.colorScheme.onSurfaceVariant,
                        maxLines = 1,
                        softWrap = false,
                        modifier = Modifier.padding(horizontal = 9.dp, vertical = 4.dp)
                    )
                }
            }

            if (vm.isDownloadingWeights || vm.isLoadingModel) {
                LinearProgressIndicator(
                    progress = { vm.modelTaskProgress.coerceIn(0.03f, 1f) },
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(6.dp)
                        .clip(CircleShape)
                )
            }

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                FilledTonalButton(
                    onClick = { vm.startRemoteDownloadWeights() },
                    enabled = vm.isConnected && !vm.isDownloadingWeights && !vm.isLoadingModel,
                    modifier = Modifier.weight(1f),
                    contentPadding = PaddingValues(horizontal = 10.dp, vertical = 8.dp)
                ) {
                    Icon(Icons.Default.CloudDownload, contentDescription = null, modifier = Modifier.size(16.dp))
                    Spacer(Modifier.width(5.dp))
                    Text(
                        text = if (vm.allDownloaded) L("校验权重", "Verify") else L("1. 下载权重", "1. Download"),
                        maxLines = 1,
                        softWrap = false,
                        overflow = TextOverflow.Ellipsis
                    )
                }

                if (vm.isSelectedModelLoadedInVRAM) {
                    OutlinedButton(
                        onClick = { vm.unloadRemoteModelFromVRAM(spec.id) },
                        enabled = !vm.isUnloadingModel,
                        modifier = Modifier.weight(1f),
                        contentPadding = PaddingValues(horizontal = 10.dp, vertical = 8.dp)
                    ) {
                        Text(
                            text = L("卸载释放显存", "Unload VRAM"),
                            maxLines = 1,
                            softWrap = false,
                            overflow = TextOverflow.Ellipsis
                        )
                    }
                } else {
                    Button(
                        onClick = { vm.loadRemoteModelToVRAM() },
                        enabled = vm.isConnected && vm.allDownloaded && !vm.isLoadingModel && !vm.isDownloadingWeights,
                        modifier = Modifier.weight(1f),
                        contentPadding = PaddingValues(horizontal = 10.dp, vertical = 8.dp)
                    ) {
                        Icon(Icons.Default.Bolt, contentDescription = null, modifier = Modifier.size(16.dp))
                        Spacer(Modifier.width(4.dp))
                        Text(
                            text = L("2. 加载到显存", "2. Load VRAM"),
                            maxLines = 1,
                            softWrap = false,
                            overflow = TextOverflow.Ellipsis
                        )
                    }
                }
            }

            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .clickable { showShards = !showShards },
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = if (vm.drivePersisted) {
                        L("已开启 Google Drive 云盘自动持久化", "Google Drive Persistence Active")
                    } else {
                        L("分片明细 (${vm.downloadedCount}/${vm.totalFileCount})", "Weight Shards (${vm.downloadedCount}/${vm.totalFileCount})")
                    },
                    fontSize = 11.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                    modifier = Modifier.weight(1f)
                )
                Icon(
                    imageVector = if (showShards) Icons.Default.ExpandLess else Icons.Default.ExpandMore,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.size(16.dp)
                )
            }

            AnimatedVisibility(visible = showShards) {
                Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    if (spec.id == "minimax_h3") {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Text(
                                text = L("显存调度策略", "VRAM Offload"),
                                fontSize = 12.sp,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                                maxLines = 1
                            )
                            SingleLineDropdownPill(
                                selectedLabel = when (vm.selectedOffload) {
                                    "none" -> L("全显存极速 (96G 推荐)", "Full GPU (96G)")
                                    "cpu" -> L("CPU 内存卸载", "CPU RAM Offload")
                                    else -> L("智能磁盘卸载 (稳妥)", "Smart Disk Offload")
                                },
                                options = listOf(
                                    DropdownChoice("disk", L("智能磁盘卸载 (稳妥)", "Smart Disk Offload")),
                                    DropdownChoice("cpu", L("CPU 内存卸载", "CPU RAM Offload")),
                                    DropdownChoice("none", L("全显存极速 (96G 推荐)", "Full GPU (96G)"))
                                ),
                                onSelect = { vm.selectedOffload = it },
                                modifier = Modifier.width(190.dp)
                            )
                        }
                        Spacer(Modifier.height(4.dp))
                    }
                    vm.modelFiles.take(12).forEach { f ->
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Text(
                                text = (if (f.exists) "✓ " else "○ ") + f.name.substringAfterLast('/'),
                                fontSize = 11.sp,
                                fontFamily = FontFamily.Monospace,
                                color = if (f.exists) Color(0xFF10B981) else MaterialTheme.colorScheme.onSurfaceVariant,
                                maxLines = 1,
                                overflow = TextOverflow.Ellipsis,
                                modifier = Modifier.weight(1f)
                            )
                            f.localizedDesc?.let { desc ->
                                Spacer(Modifier.width(6.dp))
                                Text(
                                    text = desc,
                                    fontSize = 10.sp,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                                    maxLines = 1
                                )
                            }
                        }
                    }
                    if (vm.modelFiles.size > 12) {
                        Text(
                            text = L("…共 ${vm.modelFiles.size} 个权重文件", "…${vm.modelFiles.size} weight shards total"),
                            fontSize = 10.sp,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun VideoAndImageWorkspaceSection(vm: StudioViewModel) {
    val context = LocalContext.current
    val spec = vm.activeModelSpec
    val isVideo = spec.modality == ModelModality.VIDEO_AUDIO
    val needsPhotos = vm.taskModeId in listOf("fl2va", "i2i_edit")
    var showAdvancedParams by remember { mutableStateOf(false) }

    val pickFirstLauncher = rememberLauncherForActivityResult(ActivityResultContracts.PickVisualMedia()) { uri ->
        vm.pickKeyframeFromUri(context, uri, isFirstFrame = true)
    }
    val pickLastLauncher = rememberLauncherForActivityResult(ActivityResultContracts.PickVisualMedia()) { uri ->
        vm.pickKeyframeFromUri(context, uri, isFirstFrame = false)
    }

    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
    ) {
        Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            // Mode selector chips
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                spec.modes.forEach { mode ->
                    FilterChip(
                        selected = vm.taskModeId == mode.id,
                        onClick = { vm.taskModeId = mode.id },
                        label = { Text(mode.title, maxLines = 1, softWrap = false) }
                    )
                }
            }

            // Preset inspiration chips
            val matchingTemplates = PRESET_TEMPLATES.filter { it.category == spec.modality }
            if (matchingTemplates.isNotEmpty()) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .horizontalScroll(rememberScrollState()),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    matchingTemplates.forEach { tpl ->
                        Surface(
                            shape = CircleShape,
                            color = MaterialTheme.colorScheme.secondaryContainer.copy(alpha = 0.65f),
                            modifier = Modifier.clickable {
                                vm.visualPrompt = tpl.visual
                                if (isVideo) {
                                    vm.soundscapePrompt = tpl.soundscape
                                    vm.musicPrompt = tpl.music
                                }
                            }
                        ) {
                            Text(
                                text = "✦ ${tpl.name}",
                                fontSize = 11.sp,
                                maxLines = 1,
                                softWrap = false,
                                modifier = Modifier.padding(horizontal = 10.dp, vertical = 5.dp)
                            )
                        }
                    }
                }
            }

            // Photo Reference Slots (when Keyframes or Image Edit selected)
            if (needsPhotos) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    KeyframeSlotBox(
                        title = if (isVideo) L("首帧参考图", "Start Frame") else L("主参考图", "Reference 1"),
                        bitmap = vm.firstFrameBitmap,
                        onPick = {
                            pickFirstLauncher.launch(PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly))
                        },
                        onClear = { vm.firstFrameBitmap = null },
                        modifier = Modifier.weight(1f)
                    )
                    KeyframeSlotBox(
                        title = if (isVideo) L("尾帧参考图 (可选)", "End Frame (Opt)") else L("融合图 2 (可选)", "Reference 2 (Opt)"),
                        bitmap = vm.lastFrameBitmap,
                        onPick = {
                            pickLastLauncher.launch(PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly))
                        },
                        onClear = { vm.lastFrameBitmap = null },
                        modifier = Modifier.weight(1f)
                    )
                }
            }

            // Visual Prompt
            OutlinedTextField(
                value = vm.visualPrompt,
                onValueChange = { vm.visualPrompt = it },
                label = {
                    Text(
                        if (isVideo) L("画面与运镜提示词 (Visual & Camera)", "Visual & Camera Prompt")
                        else L("画面构图与文字排版提示词", "Image & Typography Prompt"),
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis
                    )
                },
                minLines = 3,
                maxLines = 6,
                modifier = Modifier.fillMaxWidth()
            )

            // Audio Prompts for MiniMax-H3
            if (isVideo) {
                OutlinedTextField(
                    value = vm.soundscapePrompt,
                    onValueChange = { vm.soundscapePrompt = it },
                    label = { Text(L("环境音效与对白 (32kHz 立体声)", "Soundscape, Foley & Speech"), maxLines = 1) },
                    minLines = 2,
                    maxLines = 3,
                    modifier = Modifier.fillMaxWidth()
                )
                OutlinedTextField(
                    value = vm.musicPrompt,
                    onValueChange = { vm.musicPrompt = it },
                    label = { Text(L("背景配乐风格 (BGM)", "Background Music"), maxLines = 1) },
                    minLines = 1,
                    maxLines = 2,
                    modifier = Modifier.fillMaxWidth()
                )
            }

            // Collapsible Resolution & Sampling Parameters
            Surface(
                shape = RoundedCornerShape(12.dp),
                color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.45f),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(modifier = Modifier.padding(11.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clickable { showAdvancedParams = !showAdvancedParams },
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.weight(1f)) {
                            Icon(Icons.Default.Tune, contentDescription = null, modifier = Modifier.size(16.dp))
                            Spacer(Modifier.width(6.dp))
                            val activeRes = if (isVideo) vm.selectedVideoResolution else vm.selectedImageResolution
                            Text(
                                text = "${activeRes.width}×${activeRes.height} · ${vm.inferenceSteps.toInt()} steps",
                                fontSize = 12.sp,
                                fontWeight = FontWeight.Medium,
                                maxLines = 1,
                                softWrap = false,
                                overflow = TextOverflow.Ellipsis
                            )
                        }
                        Icon(
                            imageVector = if (showAdvancedParams) Icons.Default.ExpandLess else Icons.Default.ExpandMore,
                            contentDescription = null,
                            modifier = Modifier.size(18.dp)
                        )
                    }

                    AnimatedVisibility(visible = showAdvancedParams) {
                        Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                            val resList = if (isVideo) VIDEO_RESOLUTIONS else IMAGE_RESOLUTIONS
                            val currentRes = if (isVideo) vm.selectedVideoResolution else vm.selectedImageResolution

                            Text(
                                text = L("输出画幅分辨率", "Output Resolution"),
                                fontSize = 12.sp,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                            SingleLineDropdownPill(
                                selectedLabel = currentRes.label,
                                options = resList.map { DropdownChoice(it, it.label) },
                                onSelect = { chosen ->
                                    if (isVideo) vm.selectedVideoResolution = chosen
                                    else vm.selectedImageResolution = chosen
                                },
                                modifier = Modifier.fillMaxWidth()
                            )

                            if (isVideo) {
                                Column {
                                    Text(
                                        text = L(
                                            "视频总帧数: ${vm.numFrames.toInt()} 帧 (约 ${String.format(Locale.US, "%.1f", vm.numFrames / vm.fps)}s)",
                                            "Frames: ${vm.numFrames.toInt()} (~${String.format(Locale.US, "%.1f", vm.numFrames / vm.fps)}s)"
                                        ),
                                        fontSize = 12.sp
                                    )
                                    Slider(
                                        value = vm.numFrames,
                                        onValueChange = { vm.numFrames = it },
                                        valueRange = 49f..193f
                                    )
                                }
                            }

                            Column {
                                Text(
                                    text = L("采样步数 (Steps): ${vm.inferenceSteps.toInt()}", "Sampling Steps: ${vm.inferenceSteps.toInt()}"),
                                    fontSize = 12.sp
                                )
                                Slider(
                                    value = vm.inferenceSteps,
                                    onValueChange = { vm.inferenceSteps = it },
                                    valueRange = if (spec.id == "z_image_turbo") 4f..16f else 15f..50f
                                )
                            }

                            if (!isVideo && vm.taskModeId == "i2i_edit") {
                                Column {
                                    Text(
                                        text = L(
                                            "重绘幅度 (Denoise): ${String.format(Locale.US, "%.2f", vm.denoisingStrength)}",
                                            "Denoising Strength: ${String.format(Locale.US, "%.2f", vm.denoisingStrength)}"
                                        ),
                                        fontSize = 12.sp
                                    )
                                    Slider(
                                        value = vm.denoisingStrength,
                                        onValueChange = { vm.denoisingStrength = it },
                                        valueRange = 0.20f..1.00f
                                    )
                                }
                            }

                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Text(L("随机种子 (Random Seed)", "Randomize Seed"), fontSize = 12.sp)
                                Switch(checked = vm.randomizeSeed, onCheckedChange = { vm.randomizeSeed = it })
                            }

                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Text(L("连抽张数 / 条数", "Batch Count"), fontSize = 12.sp)
                                Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                                    listOf(1, 2, 4).forEach { cnt ->
                                        FilterChip(
                                            selected = vm.batchCount == cnt,
                                            onClick = { vm.batchCount = cnt },
                                            label = { Text("${cnt}×", maxLines = 1) }
                                        )
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // Generate / Cancel CTA
            if (vm.isGenerating) {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    LinearProgressIndicator(
                        progress = { vm.progressValue.coerceIn(0.02f, 1f) },
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(7.dp)
                            .clip(CircleShape)
                    )
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = "${(vm.progressValue * 100).toInt()}% · ${formatDuration(vm.currentJobElapsed)}",
                            fontSize = 12.sp,
                            fontFamily = FontFamily.Monospace,
                            color = MaterialTheme.colorScheme.primary
                        )
                        Button(
                            onClick = { vm.cancelCurrentGeneration() },
                            colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.error)
                        ) {
                            Icon(Icons.Default.Stop, contentDescription = null, modifier = Modifier.size(16.dp))
                            Spacer(Modifier.width(4.dp))
                            Text(L("中断推理", "Stop"), maxLines = 1)
                        }
                    }
                }
            } else {
                Button(
                    onClick = { vm.startGeneration() },
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(48.dp),
                    shape = RoundedCornerShape(12.dp)
                ) {
                    Icon(Icons.Default.AutoAwesome, contentDescription = null, modifier = Modifier.size(18.dp))
                    Spacer(Modifier.width(8.dp))
                    Text(
                        text = if (isVideo) L("开始云端生成有声视频", "Generate Video + Stereo Audio")
                        else L("开始云端高清生图 / 修图", "Generate HD Image"),
                        fontWeight = FontWeight.Bold,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis
                    )
                }
            }
        }
    }
}

@Composable
internal fun KeyframeSlotBox(
    title: String,
    bitmap: android.graphics.Bitmap?,
    onPick: () -> Unit,
    onClear: () -> Unit,
    modifier: Modifier = Modifier
) {
    Surface(
        shape = RoundedCornerShape(12.dp),
        color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.55f),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
        modifier = modifier
            .height(112.dp)
            .clickable { onPick() }
    ) {
        Box(modifier = Modifier.fillMaxSize()) {
            if (bitmap != null) {
                Image(
                    bitmap = bitmap.asImageBitmap(),
                    contentDescription = title,
                    contentScale = ContentScale.Crop,
                    modifier = Modifier.fillMaxSize()
                )
                IconButton(
                    onClick = onClear,
                    modifier = Modifier
                        .align(Alignment.TopEnd)
                        .padding(4.dp)
                        .size(26.dp)
                        .clip(CircleShape)
                        .background(Color.Black.copy(alpha = 0.6f))
                ) {
                    Icon(Icons.Default.Close, contentDescription = "Clear", tint = Color.White, modifier = Modifier.size(14.dp))
                }
            } else {
                Column(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(8.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.Center
                ) {
                    Icon(
                        Icons.Default.AddPhotoAlternate,
                        contentDescription = null,
                        tint = MaterialTheme.colorScheme.primary,
                        modifier = Modifier.size(24.dp)
                    )
                    Spacer(Modifier.height(4.dp))
                    Text(
                        text = title,
                        fontSize = 11.sp,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis
                    )
                }
            }
        }
    }
}

// ============================================================================
// QWEN 3.8 27B (256K CONTEXT + THINKING + VISION + OPENAI/ANTHROPIC GATEWAY)
// ============================================================================

