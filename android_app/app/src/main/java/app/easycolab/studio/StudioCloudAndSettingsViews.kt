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

@Composable
internal fun QwenLlmWorkspaceSection(vm: StudioViewModel) {
    val context = LocalContext.current
    val spec = vm.activeModelSpec
    val pickVisionLauncher = rememberLauncherForActivityResult(ActivityResultContracts.PickVisualMedia()) { uri ->
        vm.pickKeyframeFromUri(context, uri, isFirstFrame = true)
    }

    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
    ) {
        Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                spec.modes.forEach { m ->
                    FilterChip(
                        selected = vm.taskModeId == m.id,
                        onClick = { vm.taskModeId = m.id },
                        label = { Text(m.title, maxLines = 1, softWrap = false) }
                    )
                }
            }

            // Dynamic 4K - 256K Context Slider
            Surface(
                shape = RoundedCornerShape(12.dp),
                color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.45f),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(modifier = Modifier.padding(11.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = L("上下文窗口: ${vm.contextLengthK}K Tokens", "Context Window: ${vm.contextLengthK}K Tokens"),
                            fontSize = 12.sp,
                            fontWeight = FontWeight.SemiBold,
                            maxLines = 1
                        )
                        TextButton(
                            onClick = { vm.syncContextLengthNow() },
                            contentPadding = PaddingValues(horizontal = 8.dp, vertical = 2.dp)
                        ) {
                            Text(L("同步至云端", "Sync"), fontSize = 11.sp, maxLines = 1)
                        }
                    }
                    Slider(
                        value = vm.contextLengthK.toFloat(),
                        onValueChange = { vm.updateContextLengthK(it.toInt()) },
                        valueRange = 4f..256f
                    )
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(Icons.Default.Psychology, contentDescription = null, modifier = Modifier.size(16.dp))
                            Spacer(Modifier.width(5.dp))
                            Text(L("深度思维链 (<think>)", "Thinking Mode"), fontSize = 12.sp, maxLines = 1)
                        }
                        Switch(checked = vm.enableThinking, onCheckedChange = { vm.updateEnableThinking(it) })
                    }
                }
            }

            if (vm.taskModeId == "api") {
                ApiGatewayPanel(vm = vm)
            } else {
                if (vm.taskModeId == "vlm") {
                    KeyframeSlotBox(
                        title = L("点击从手机相册选择待分析照片", "Tap to pick photo for Vision / Prompt Reverse"),
                        bitmap = vm.firstFrameBitmap,
                        onPick = {
                            pickVisionLauncher.launch(PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly))
                        },
                        onClear = { vm.firstFrameBitmap = null },
                        modifier = Modifier.fillMaxWidth()
                    )
                }

                // Chat conversation history
                if (vm.chatHistory.isNotEmpty()) {
                    Column(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clip(RoundedCornerShape(12.dp))
                            .background(MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.35f))
                            .padding(10.dp),
                        verticalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(
                                text = L("多轮对话 (${vm.chatHistory.size})", "Messages (${vm.chatHistory.size})"),
                                fontSize = 11.sp,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                            TextButton(
                                onClick = { vm.chatHistory.clear() },
                                contentPadding = PaddingValues(horizontal = 6.dp, vertical = 2.dp)
                            ) {
                                Icon(Icons.Default.DeleteSweep, contentDescription = null, modifier = Modifier.size(14.dp))
                                Spacer(Modifier.width(4.dp))
                                Text(L("清空", "Clear"), fontSize = 11.sp)
                            }
                        }

                        vm.chatHistory.forEach { turn ->
                            ChatBubbleRow(turn = turn)
                        }
                    }
                }

                // Quick prompt presets
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .horizontalScroll(rememberScrollState()),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    PRESET_TEMPLATES.filter { it.category == ModelModality.LLM_VLM }.forEach { tpl ->
                        Surface(
                            shape = CircleShape,
                            color = MaterialTheme.colorScheme.secondaryContainer.copy(alpha = 0.65f),
                            modifier = Modifier.clickable { vm.visualPrompt = tpl.visual }
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

                OutlinedTextField(
                    value = vm.visualPrompt,
                    onValueChange = { vm.visualPrompt = it },
                    label = { Text(L("输入问题、代码需求或分镜构思...", "Ask anything, code, or reverse-prompt..."), maxLines = 1) },
                    minLines = 2,
                    maxLines = 5,
                    modifier = Modifier.fillMaxWidth()
                )

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    if (vm.isGenerating) {
                        Button(
                            onClick = { vm.cancelCurrentGeneration() },
                            colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.error),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Icon(Icons.Default.Stop, contentDescription = null, modifier = Modifier.size(16.dp))
                            Spacer(Modifier.width(6.dp))
                            Text(L("停止生成 (${formatDuration(vm.currentJobElapsed, true)})", "Stop"))
                        }
                    } else {
                        Button(
                            onClick = { vm.startGeneration() },
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(46.dp)
                        ) {
                            Icon(Icons.AutoMirrored.Filled.Send, contentDescription = null, modifier = Modifier.size(16.dp))
                            Spacer(Modifier.width(6.dp))
                            Text(L("发送给云端 Qwen3.8", "Send to Cloud Qwen3.8"), fontWeight = FontWeight.Bold)
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun ChatBubbleRow(turn: ChatTurnItem) {
    val isUser = turn.role == "user"
    var showThought by remember { mutableStateOf(false) }

    Column(
        modifier = Modifier.fillMaxWidth(),
        horizontalAlignment = if (isUser) Alignment.End else Alignment.Start
    ) {
        Surface(
            shape = RoundedCornerShape(12.dp),
            color = if (isUser) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.surface
        ) {
            Column(modifier = Modifier.padding(10.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                if (turn.thinking.isNotBlank()) {
                    Surface(
                        shape = RoundedCornerShape(8.dp),
                        color = MaterialTheme.colorScheme.surfaceVariant,
                        modifier = Modifier.clickable { showThought = !showThought }
                    ) {
                        Column(modifier = Modifier.padding(8.dp)) {
                            Text(
                                text = if (showThought) L("▼ 收起思考过程", "▼ Hide Reasoning")
                                else L("▶ 查看思考过程 (${turn.thinking.length} 字)", "▶ View Reasoning (${turn.thinking.length} chars)"),
                                fontSize = 11.sp,
                                fontWeight = FontWeight.SemiBold,
                                color = MaterialTheme.colorScheme.primary
                            )
                            if (showThought) {
                                Spacer(Modifier.height(4.dp))
                                Text(
                                    text = turn.thinking,
                                    fontSize = 11.sp,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                            }
                        }
                    }
                }
                Text(
                    text = turn.content.ifEmpty { L("正在思考与生成...", "Thinking...") },
                    fontSize = 13.sp,
                    color = if (isUser) MaterialTheme.colorScheme.onPrimary else MaterialTheme.colorScheme.onSurface
                )
            }
        }
    }
}

@Composable
private fun ApiGatewayPanel(vm: StudioViewModel) {
    val context = LocalContext.current
    val base = vm.normalizedBaseURL.ifEmpty { "https://xxxx.gradio.live" }
    val displayBase = if (vm.maskServerURL) vm.maskedURLDisplay(base) else base
    val openAiEndpoint = "$base/v1"
    val anthropicEndpoint = base

    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Text(
            text = L(
                "已内置兼容 OpenAI SDK (/v1/chat/completions) 与 Anthropic Claude Code (/v1/messages) 双协议网关：",
                "Built-in dual-protocol gateway compatible with OpenAI (/v1) & Anthropic Claude Code (/v1/messages):"
            ),
            fontSize = 12.sp,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(L("启用 API Key 鉴权保护", "Enable Bearer API Key Auth"), fontSize = 12.sp)
            Switch(checked = vm.apiKeyEnabled, onCheckedChange = { vm.updateApiKeyEnabled(it) })
        }

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(6.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            OutlinedTextField(
                value = if (vm.maskServerURL) "sk-colab-••••••••••••" else vm.apiAccessKey,
                onValueChange = { if (!vm.maskServerURL) vm.updateApiAccessKey(it) },
                readOnly = vm.maskServerURL,
                label = { Text("API Key", maxLines = 1) },
                singleLine = true,
                modifier = Modifier.weight(1f)
            )
            IconButton(onClick = {
                vm.copyToClipboard(context, "API Key", vm.apiAccessKey, L("已复制 API Key", "API Key copied"))
            }) {
                Icon(Icons.Default.ContentCopy, contentDescription = "Copy")
            }
            IconButton(onClick = { vm.regenerateApiKey() }) {
                Icon(Icons.Default.Refresh, contentDescription = "Regenerate")
            }
        }

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            FilledTonalButton(
                onClick = {
                    vm.copyToClipboard(context, "OpenAI Base URL", openAiEndpoint, L("已复制 OpenAI Base URL", "Copied OpenAI /v1 URL"))
                },
                modifier = Modifier.weight(1f)
            ) {
                Text("Copy /v1", maxLines = 1, softWrap = false)
            }
            FilledTonalButton(
                onClick = {
                    val cmd = "export ANTHROPIC_BASE_URL=\"$anthropicEndpoint\"\nexport ANTHROPIC_API_KEY=\"${vm.apiAccessKey}\"\nclaude --model ${vm.selectedModelId}"
                    vm.copyToClipboard(context, "Claude Code Env", cmd, L("已复制 Claude Code 启动命令", "Copied Claude Code CLI setup"))
                },
                modifier = Modifier.weight(1f)
            ) {
                Text("Claude Code", maxLines = 1, softWrap = false)
            }
        }

        Text(
            text = "OpenAI Base: $displayBase/v1  ·  Requests: ${vm.apiRequestCount}",
            fontSize = 11.sp,
            fontFamily = FontFamily.Monospace,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis
        )
    }
}

// ============================================================================
// COMFYUI CLOUD STUDIO WORKSPACE
// ============================================================================

@Composable
internal fun ComfyStudioWorkspaceSection(vm: StudioViewModel) {
    val context = LocalContext.current

    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        // 1. ComfyUI Control & Canvas Card
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
                            text = L("云端 ComfyUI 节点工作台", "Cloud ComfyUI Node Studio"),
                            style = MaterialTheme.typography.titleSmall,
                            fontWeight = FontWeight.Bold,
                            maxLines = 1
                        )
                        Text(
                            text = localizeServerText(vm.comfyStatusMessage),
                            fontSize = 11.sp,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            maxLines = 2,
                            overflow = TextOverflow.Ellipsis
                        )
                    }
                    Surface(
                        shape = CircleShape,
                        color = if (vm.comfyRunning) Color(0xFF10B981).copy(alpha = 0.16f)
                        else MaterialTheme.colorScheme.surfaceVariant
                    ) {
                        Text(
                            text = if (vm.comfyRunning) L("运行中", "Running") else L("未启动", "Stopped"),
                            fontSize = 11.sp,
                            fontWeight = FontWeight.SemiBold,
                            color = if (vm.comfyRunning) Color(0xFF059669) else MaterialTheme.colorScheme.onSurfaceVariant,
                            maxLines = 1,
                            modifier = Modifier.padding(horizontal = 9.dp, vertical = 4.dp)
                        )
                    }
                }

                if (vm.comfyStarting || vm.comfyDownloadingWeight) {
                    LinearProgressIndicator(
                        progress = { vm.comfyProgress.coerceIn(0.03f, 1f) },
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
                    if (vm.comfyRunning) {
                        Button(
                            onClick = { vm.openComfyCanvas(context) },
                            enabled = vm.comfyPublicURL.isNotBlank(),
                            modifier = Modifier.weight(1.3f)
                        ) {
                            Icon(Icons.Default.OpenInBrowser, contentDescription = null, modifier = Modifier.size(16.dp))
                            Spacer(Modifier.width(5.dp))
                            Text(L("打开画布", "Open Canvas"), maxLines = 1, softWrap = false)
                        }
                        OutlinedButton(
                            onClick = { vm.syncRemoteComfyUIToDrive() },
                            enabled = !vm.comfySyncingDrive,
                            modifier = Modifier.weight(1f)
                        ) {
                            Icon(Icons.Default.CloudSync, contentDescription = null, modifier = Modifier.size(16.dp))
                            Spacer(Modifier.width(4.dp))
                            Text(L("同步云盘", "Sync"), maxLines = 1, softWrap = false)
                        }
                        IconButton(onClick = { vm.stopRemoteComfyUI() }) {
                            Icon(Icons.Default.Stop, contentDescription = "Stop", tint = MaterialTheme.colorScheme.error)
                        }
                    } else {
                        Button(
                            onClick = { vm.startRemoteComfyUI(forceRestart = false) },
                            enabled = vm.isConnected && !vm.comfyStarting,
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Icon(Icons.Default.PlayArrow, contentDescription = null, modifier = Modifier.size(18.dp))
                            Spacer(Modifier.width(6.dp))
                            Text(L("一键部署并启动云端 ComfyUI", "Start Cloud ComfyUI"), fontWeight = FontWeight.Bold, maxLines = 1)
                        }
                    }
                }
            }
        }

        // 2. 4 Preset Video Workflow Packs
        Card(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(16.dp),
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
        ) {
            Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Text(
                    text = L("一键预置视频工作流包 (自动配齐节点 + 权重 + 模板)", "1-Tap Preset Video Workflow Packs"),
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.Bold,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )

                vm.comfyPresetPacks.forEach { pack ->
                    Surface(
                        shape = RoundedCornerShape(12.dp),
                        color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.42f),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Column(modifier = Modifier.padding(11.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Text(
                                    text = pack.localizedTitle,
                                    fontSize = 13.sp,
                                    fontWeight = FontWeight.SemiBold,
                                    maxLines = 1,
                                    overflow = TextOverflow.Ellipsis,
                                    modifier = Modifier.weight(1f)
                                )
                                Spacer(Modifier.width(6.dp))
                                Text(
                                    text = "${pack.installedModels}/${pack.totalModels}",
                                    fontSize = 11.sp,
                                    fontFamily = FontFamily.Monospace,
                                    color = if (pack.ready) Color(0xFF10B981) else MaterialTheme.colorScheme.primary
                                )
                            }
                            Text(
                                text = pack.localizedScenario,
                                fontSize = 11.sp,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                                maxLines = 2,
                                overflow = TextOverflow.Ellipsis
                            )
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Text(
                                    text = "${pack.localizedBadge} · ~${String.format(Locale.US, "%.1f", pack.approxSizeGb)} GB",
                                    fontSize = 11.sp,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                                    maxLines = 1
                                )
                                FilledTonalButton(
                                    onClick = { vm.installComfyPresetPack(pack) },
                                    enabled = vm.isConnected && !vm.comfyDownloadingWeight,
                                    contentPadding = PaddingValues(horizontal = 12.dp, vertical = 6.dp)
                                ) {
                                    Text(
                                        text = if (pack.ready) L("已就绪 · 启动", "Ready · Open")
                                        else L("一键配齐", "Install Pack"),
                                        fontSize = 12.sp,
                                        maxLines = 1,
                                        softWrap = false
                                    )
                                }
                            }
                        }
                    }
                }
            }
        }

        // 3. Custom Cloud Weight Downloader + Recent Outputs Pull
        Card(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(16.dp),
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
        ) {
            Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Text(
                    text = L("云端高速补权重 & 成片拉取回手机", "Cloud 8-Thread Weight Downloader & Outputs"),
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.Bold,
                    maxLines = 1
                )

                OutlinedTextField(
                    value = vm.comfyWeightSourceInput,
                    onValueChange = { vm.comfyWeightSourceInput = it },
                    label = { Text(L("HuggingFace Repo 或直链 URL", "HF Repo or Direct Download URL"), maxLines = 1) },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    SingleLineDropdownPill(
                        selectedLabel = vm.comfyWeightSubfolder,
                        options = listOf(
                            "diffusion_models", "checkpoints", "loras", "vae", "text_encoders", "clip_vision"
                        ).map { DropdownChoice(it, it) },
                        onSelect = { vm.comfyWeightSubfolder = it },
                        modifier = Modifier.weight(1f)
                    )
                    FilledTonalButton(
                        onClick = { vm.startComfyWeightDownload() },
                        enabled = vm.isConnected && vm.comfyWeightSourceInput.isNotBlank() && !vm.comfyDownloadingWeight
                    ) {
                        Icon(Icons.Default.CloudDownload, contentDescription = null, modifier = Modifier.size(16.dp))
                        Spacer(Modifier.width(4.dp))
                        Text(L("云端下载", "Download"), maxLines = 1, softWrap = false)
                    }
                }

                if (vm.comfyRecentOutputs.isNotEmpty()) {
                    HorizontalDivider()
                    Text(
                        text = L("ComfyUI 最新成片 (点击一键拉回手机相册)", "Recent ComfyUI Outputs (Tap to pull to phone)"),
                        fontSize = 12.sp,
                        fontWeight = FontWeight.SemiBold
                    )
                    vm.comfyRecentOutputs.take(8).forEach { outItem ->
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(
                                text = outItem.filename,
                                fontSize = 12.sp,
                                maxLines = 1,
                                overflow = TextOverflow.Ellipsis,
                                modifier = Modifier.weight(1f)
                            )
                            Spacer(Modifier.width(8.dp))
                            FilledTonalButton(
                                onClick = { vm.pullComfyOutputToPhone(outItem) },
                                enabled = vm.comfyPullingOutputRelPath == null,
                                contentPadding = PaddingValues(horizontal = 10.dp, vertical = 4.dp)
                            ) {
                                if (vm.comfyPullingOutputRelPath == outItem.relPath) {
                                    CircularProgressIndicator(modifier = Modifier.size(14.dp), strokeWidth = 2.dp)
                                } else {
                                    Icon(Icons.Default.Download, contentDescription = null, modifier = Modifier.size(14.dp))
                                    Spacer(Modifier.width(4.dp))
                                    Text(L("存手机", "Pull"), fontSize = 11.sp, maxLines = 1)
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

// ============================================================================
// TAB 2: CLOUD GPU & BILLING MANAGEMENT
// ============================================================================

@Composable
fun CloudGpuTabScreen(vm: StudioViewModel) {
    val context = LocalContext.current

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background),
        contentPadding = PaddingValues(horizontal = 14.dp, vertical = 12.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        // 1. Native Headless Wake Card
        item {
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
            ) {
                Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.weight(1f)) {
                            Icon(
                                Icons.Default.Cloud,
                                contentDescription = null,
                                tint = MaterialTheme.colorScheme.primary,
                                modifier = Modifier.size(20.dp)
                            )
                            Spacer(Modifier.width(6.dp))
                            Text(
                                text = L("原生免网页云算力引擎", "Native Headless Colab Engine"),
                                style = MaterialTheme.typography.titleSmall,
                                fontWeight = FontWeight.Bold,
                                maxLines = 1,
                                overflow = TextOverflow.Ellipsis
                            )
                        }
                        IconButton(
                            onClick = { vm.openManualOAuthDialog(context) },
                            modifier = Modifier.size(30.dp)
                        ) {
                            Icon(
                                Icons.Default.Key,
                                contentDescription = "Manual OAuth Code",
                                tint = MaterialTheme.colorScheme.onSurfaceVariant,
                                modifier = Modifier.size(16.dp)
                            )
                        }
                    }

                    // Google Account Row
                    Surface(
                        shape = RoundedCornerShape(12.dp),
                        color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.45f),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Row(
                            modifier = Modifier.padding(horizontal = 12.dp, vertical = 10.dp),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Column(modifier = Modifier.weight(1f)) {
                                Text(
                                    text = L("Google Colab 账号", "Google Colab Account"),
                                    fontSize = 11.sp,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                                    maxLines = 1
                                )
                                Text(
                                    text = vm.displayAccountLabel,
                                    fontSize = 13.sp,
                                    fontWeight = FontWeight.SemiBold,
                                    maxLines = 1,
                                    overflow = TextOverflow.Ellipsis
                                )
                            }
                            Spacer(Modifier.width(8.dp))
                            if (vm.cliLoggedIn) {
                                OutlinedButton(
                                    onClick = { vm.logoutGoogleAccount() },
                                    contentPadding = PaddingValues(horizontal = 12.dp, vertical = 6.dp)
                                ) {
                                    Text(L("解绑", "Unbind"), fontSize = 12.sp, maxLines = 1, softWrap = false)
                                }
                            } else {
                                Button(
                                    onClick = { vm.startGoogleOAuthLogin(context) },
                                    enabled = !vm.isAuthenticatingGoogle,
                                    contentPadding = PaddingValues(horizontal = 12.dp, vertical = 6.dp)
                                ) {
                                    Text(L("一键绑定 Google", "Sign in Google"), fontSize = 12.sp, maxLines = 1, softWrap = false)
                                }
                            }
                        }
                    }

                    // CU Balance & Burn Rate Metrics
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(10.dp)
                    ) {
                        MetricTile(
                            label = L("剩余计算单元 (CU)", "Paid CU Balance"),
                            value = if (vm.officialCUBalance != null) String.format(Locale.US, "%.2f CU", vm.displayRemainingCU) else "--",
                            accent = Color(0xFF10B981),
                            modifier = Modifier.weight(1f)
                        )
                        MetricTile(
                            label = L("实时计费速率", "Hourly Burn Rate"),
                            value = String.format(Locale.US, "%.2f CU/h", vm.displayBurnRate),
                            accent = if (vm.displayBurnRate > 0.0) Color(0xFFF59E0B) else MaterialTheme.colorScheme.onSurfaceVariant,
                            modifier = Modifier.weight(1f)
                        )
                    }

                    // Target GPU Spec Selector (Single-line non-wrapping pill!)
                    val gpuOptions = listOf(
                        DropdownChoice("G4", "G4 · RTX PRO 6000 (96GB)"),
                        DropdownChoice("H100", "H100 · Hopper SXM (80GB)"),
                        DropdownChoice("A100", "A100 · Ampere SXM (80GB)"),
                        DropdownChoice("L4", "L4 · Ada Lovelace (24GB)"),
                        DropdownChoice("T4", "T4 · Turing (16GB)")
                    )
                    val activeGpuLabel = gpuOptions.firstOrNull { it.value == vm.wakeGPUChoice }?.label
                        ?: "G4 · RTX PRO 6000 (96GB)"

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(10.dp)
                    ) {
                        Text(
                            text = L("目标 GPU 规格", "Target GPU"),
                            fontSize = 13.sp,
                            fontWeight = FontWeight.Medium,
                            maxLines = 1,
                            softWrap = false
                        )
                        SingleLineDropdownPill(
                            selectedLabel = activeGpuLabel,
                            options = gpuOptions,
                            onSelect = { vm.updateWakeGPUChoice(it) },
                            modifier = Modifier.weight(1f)
                        )
                    }

                    Button(
                        onClick = { vm.wakeColabHeadless() },
                        enabled = vm.cliLoggedIn && !vm.isWakingColab,
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(48.dp),
                        shape = RoundedCornerShape(12.dp)
                    ) {
                        if (vm.isWakingColab) {
                            CircularProgressIndicator(
                                color = MaterialTheme.colorScheme.onPrimary,
                                strokeWidth = 2.dp,
                                modifier = Modifier.size(18.dp)
                            )
                            Spacer(Modifier.width(8.dp))
                            Text(L("正在云端分配并启动隧道...", "Provisioning Cloud GPU..."), maxLines = 1)
                        } else {
                            Icon(Icons.Default.Bolt, contentDescription = null, modifier = Modifier.size(18.dp))
                            Spacer(Modifier.width(6.dp))
                            Text(
                                text = L("一键免网页唤醒 ${vm.wakeGPUChoice} 云实例", "1-Tap Headless Wake (${vm.wakeGPUChoice})"),
                                fontWeight = FontWeight.Bold,
                                maxLines = 1,
                                overflow = TextOverflow.Ellipsis
                            )
                        }
                    }
                }
            }
        }

        // 2. Direct gradio.live Tunnel URL Card
        item {
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
            ) {
                Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(Icons.Default.Link, contentDescription = null, modifier = Modifier.size(18.dp))
                        Spacer(Modifier.width(6.dp))
                        Text(
                            text = L("服务端隧道直连地址 (gradio.live)", "Colab Tunnel Endpoint (gradio.live)"),
                            style = MaterialTheme.typography.titleSmall,
                            fontWeight = FontWeight.Bold,
                            maxLines = 1
                        )
                    }

                    OutlinedTextField(
                        value = vm.colabServerURL,
                        onValueChange = { vm.updateColabServerURL(it) },
                        placeholder = { Text("https://xxxx.gradio.live", maxLines = 1) },
                        visualTransformation = if (vm.maskServerURL && vm.colabServerURL.isNotEmpty()) {
                            PasswordVisualTransformation()
                        } else {
                            VisualTransformation.None
                        },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth()
                    )

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        FilledTonalButton(
                            onClick = { vm.triggerCheckStatus() },
                            modifier = Modifier.weight(1f)
                        ) {
                            Icon(Icons.Default.CheckCircle, contentDescription = null, modifier = Modifier.size(16.dp))
                            Spacer(Modifier.width(5.dp))
                            Text(L("连接并同步状态", "Connect & Sync"), maxLines = 1, softWrap = false)
                        }
                        OutlinedButton(
                            onClick = {
                                if (vm.colabServerURL.isNotBlank()) {
                                    vm.copyToClipboard(context, "Colab URL", vm.colabServerURL, L("已复制服务地址", "Tunnel URL copied"))
                                }
                            }
                        ) {
                            Icon(Icons.Default.ContentCopy, contentDescription = "Copy", modifier = Modifier.size(16.dp))
                        }
                    }
                }
            }
        }

        // 3. Smooth Bezier Telemetry Chart
        item {
            SmoothTelemetryChartCard(vm = vm)
        }

        // 4. Resident Models in VRAM Card
        if (vm.loadedModelsDetail.isNotEmpty()) {
            item {
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(16.dp),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
                ) {
                    Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text(
                            text = L("当前常驻显存模型 (${vm.loadedModelsDetail.size})", "Resident Models in VRAM (${vm.loadedModelsDetail.size})"),
                            style = MaterialTheme.typography.titleSmall,
                            fontWeight = FontWeight.Bold,
                            maxLines = 1
                        )
                        vm.loadedModelsDetail.forEach { m ->
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Column(modifier = Modifier.weight(1f)) {
                                    Text(m.localizedName, fontSize = 13.sp, fontWeight = FontWeight.SemiBold, maxLines = 1)
                                    Text(
                                        text = buildString {
                                            m.vramGb?.let { append(String.format(Locale.US, "%.1f GB VRAM", it)) }
                                            m.contextLength?.takeIf { it > 0 }?.let { append(" · ${it / 1024}K ctx") }
                                        },
                                        fontSize = 11.sp,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                                        maxLines = 1
                                    )
                                }
                                OutlinedButton(
                                    onClick = { vm.unloadRemoteModelFromVRAM(m.id) },
                                    enabled = !vm.isUnloadingModel,
                                    contentPadding = PaddingValues(horizontal = 10.dp, vertical = 4.dp)
                                ) {
                                    Text(L("卸载", "Unload"), fontSize = 11.sp, maxLines = 1)
                                }
                            }
                        }
                    }
                }
            }
        }

        // 5. Auto-Sleep CU Protection & Terminate All Cloud VMs
        item {
            val sleepChoices = listOf(
                DropdownChoice(15, L("闲置 15 分钟自动释放", "15 min Idle Auto-Stop")),
                DropdownChoice(30, L("闲置 30 分钟自动释放 (推荐)", "30 min Idle Auto-Stop")),
                DropdownChoice(60, L("闲置 60 分钟自动释放", "60 min Idle Auto-Stop")),
                DropdownChoice(0, L("关闭自动休眠", "Disable Auto-Sleep"))
            )
            val currentSleepLabel = sleepChoices.firstOrNull { it.value == vm.idleTimeoutMinutes }?.label
                ?: sleepChoices[1].label

            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
            ) {
                Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = L("防忘关机省额度保护", "Idle CU Protection"),
                            style = MaterialTheme.typography.titleSmall,
                            fontWeight = FontWeight.Bold,
                            maxLines = 1
                        )
                        Text(
                            text = vm.formattedIdleRemaining,
                            fontSize = 11.sp,
                            fontFamily = FontFamily.Monospace,
                            color = Color(0xFF10B981),
                            maxLines = 1
                        )
                    }

                    SingleLineDropdownPill(
                        selectedLabel = currentSleepLabel,
                        options = sleepChoices,
                        onSelect = { vm.setIdleTimeout(it) },
                        modifier = Modifier.fillMaxWidth()
                    )

                    Button(
                        onClick = { vm.showDisconnectConfirm = true },
                        colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.error),
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(46.dp),
                        shape = RoundedCornerShape(12.dp)
                    ) {
                        Icon(Icons.Default.PowerSettingsNew, contentDescription = null, modifier = Modifier.size(18.dp))
                        Spacer(Modifier.width(6.dp))
                        Text(
                            text = L("断开并彻底释放全部云实例 (0 CU/h)", "Terminate All Cloud VMs (0 CU/h)"),
                            fontWeight = FontWeight.Bold,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis
                        )
                    }
                }
            }
        }
    }

    if (vm.showDisconnectConfirm) {
        AlertDialog(
            onDismissRequest = { vm.showDisconnectConfirm = false },
            title = { Text(L("确认释放全部云端实例？", "Terminate All Cloud Instances?")) },
            text = {
                Text(
                    L(
                        "将自动把 ComfyUI 新产出同步回 Google Drive，随后彻底销毁账号下所有活跃 Colab GPU 实例，使每小时 CU 扣费立即归零。",
                        "Syncs ComfyUI outputs to Google Drive and unassigns all active Colab GPU runtimes so billing drops to 0.00 CU/h immediately."
                    )
                )
            },
            confirmButton = {
                Button(
                    onClick = {
                        vm.showDisconnectConfirm = false
                        vm.disconnectRemoteColab()
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.error)
                ) {
                    Text(L("确认释放", "Terminate Now"))
                }
            },
            dismissButton = {
                TextButton(onClick = { vm.showDisconnectConfirm = false }) {
                    Text(L("取消", "Cancel"))
                }
            }
        )
    }

    if (vm.showOAuthCodeDialog) {
        AlertDialog(
            onDismissRequest = { vm.showOAuthCodeDialog = false },
            title = { Text(L("手动授权码绑定 (备用通道)", "Manual Google OAuth Code")) },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Text(
                        text = L(
                            "若手机未安装支持自动跳回的浏览器，可复制下方链接在任意浏览器登录 Google，然后将页面显示的 4/0A... 授权码粘贴到此处：",
                            "If your browser cannot redirect automatically, copy the auth link, sign in, and paste the 4/0A... authorization code here:"
                        ),
                        fontSize = 12.sp
                    )
                    OutlinedButton(
                        onClick = { vm.copyManualOAuthLink(context) },
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Icon(Icons.Default.ContentCopy, contentDescription = null, modifier = Modifier.size(15.dp))
                        Spacer(Modifier.width(6.dp))
                        Text(L("复制 Google 授权链接", "Copy Google Auth URL"), maxLines = 1)
                    }
                    OutlinedTextField(
                        value = vm.oauthCodeText,
                        onValueChange = { vm.oauthCodeText = it },
                        placeholder = { Text("4/0A...", maxLines = 1) },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth()
                    )
                }
            },
            confirmButton = {
                Button(
                    onClick = { vm.submitManualOAuthCode() },
                    enabled = vm.oauthCodeText.isNotBlank() && !vm.isAuthenticatingGoogle
                ) {
                    Text(L("验证并绑定", "Verify Code"))
                }
            },
            dismissButton = {
                TextButton(onClick = { vm.showOAuthCodeDialog = false }) {
                    Text(L("关闭", "Close"))
                }
            }
        )
    }
}

@Composable
private fun MetricTile(
    label: String,
    value: String,
    accent: Color,
    modifier: Modifier = Modifier
) {
    Surface(
        shape = RoundedCornerShape(12.dp),
        color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.45f),
        modifier = modifier
    ) {
        Column(modifier = Modifier.padding(horizontal = 12.dp, vertical = 9.dp)) {
            Text(
                text = label,
                fontSize = 11.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis
            )
            Spacer(Modifier.height(2.dp))
            Text(
                text = value,
                fontSize = 16.sp,
                fontWeight = FontWeight.Bold,
                fontFamily = FontFamily.Monospace,
                color = accent,
                maxLines = 1
            )
        }
    }
}

// ============================================================================
// TAB 4: LIVE CONSOLE & SETTINGS
// ============================================================================

@Composable
fun ConsoleAndSettingsTabScreen(vm: StudioViewModel) {
    val context = LocalContext.current
    var showCustomOAuthDialog by remember { mutableStateOf(false) }
    var customOAuthText by remember { mutableStateOf("") }

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background),
        contentPadding = PaddingValues(horizontal = 14.dp, vertical = 12.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        // 1. Live Server Terminal Console
        item {
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(containerColor = Color(0xFF0F172A))
            ) {
                Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = L("云端实时终端日志 (${vm.formattedUptime})", "Live Cloud Console (${vm.formattedUptime})"),
                            fontSize = 12.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color(0xFF38BDF8),
                            maxLines = 1
                        )
                        IconButton(
                            onClick = {
                                vm.copyToClipboard(
                                    context,
                                    "EasyColab Logs",
                                    vm.liveConsoleLines.joinToString("\n"),
                                    L("已复制终端日志", "Console logs copied")
                                )
                            },
                            modifier = Modifier.size(28.dp)
                        ) {
                            Icon(
                                Icons.Default.ContentCopy,
                                contentDescription = "Copy Logs",
                                tint = Color(0xFF94A3B8),
                                modifier = Modifier.size(15.dp)
                            )
                        }
                    }

                    Column(
                        modifier = Modifier
                            .fillMaxWidth()
                            .heightIn(min = 150.dp, max = 230.dp)
                            .verticalScroll(rememberScrollState()),
                        verticalArrangement = Arrangement.spacedBy(3.dp)
                    ) {
                        vm.liveConsoleLines.takeLast(60).forEach { line ->
                            Text(
                                text = localizeServerText(line),
                                fontSize = 11.sp,
                                fontFamily = FontFamily.Monospace,
                                color = Color(0xFFE2E8F0)
                            )
                        }
                    }
                }
            }
        }

        // 2. Preferences Card
        item {
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
            ) {
                Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    Text(
                        text = L("偏好设置", "Preferences"),
                        style = MaterialTheme.typography.titleSmall,
                        fontWeight = FontWeight.Bold
                    )

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column(modifier = Modifier.weight(1f)) {
                            Text(L("出片自动存入系统相册", "Auto-Save to Android Gallery"), fontSize = 13.sp, fontWeight = FontWeight.Medium)
                            Text(
                                L("视频存入 Movies/EasyColab，图片存入 Pictures/EasyColab", "Videos -> Movies/EasyColab, Images -> Pictures/EasyColab"),
                                fontSize = 11.sp,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                        Switch(checked = vm.autoSaveToGallery, onCheckedChange = { vm.updateAutoSaveToGallery(it) })
                    }

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column(modifier = Modifier.weight(1f)) {
                            Text(L("直播 / 录屏隐私打码模式", "Streamer Privacy Mask"), fontSize = 13.sp, fontWeight = FontWeight.Medium)
                            Text(
                                L("自动隐藏 gradio.live 地址、邮箱与 API Key", "Masks tunnel URL, account email & API key"),
                                fontSize = 11.sp,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                        Switch(checked = vm.maskServerURL, onCheckedChange = { vm.updateMaskServerURL(it) })
                    }

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(L("界面语言 (Language)", "Interface Language"), fontSize = 13.sp, fontWeight = FontWeight.Medium)
                        Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                            FilterChip(
                                selected = !LanguageManager.isEN,
                                onClick = { LanguageManager.setLanguage(AppLanguage.ZH, context) },
                                label = { Text("中文") }
                            )
                            FilterChip(
                                selected = LanguageManager.isEN,
                                onClick = { LanguageManager.setLanguage(AppLanguage.EN, context) },
                                label = { Text("English") }
                            )
                        }
                    }

                    OutlinedTextField(
                        value = vm.hfToken,
                        onValueChange = { vm.updateHfToken(it) },
                        label = { Text(L("HuggingFace Token (受限仓库可选)", "HuggingFace Token (Optional)"), maxLines = 1) },
                        placeholder = { Text("hf_...") },
                        visualTransformation = PasswordVisualTransformation(),
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth()
                    )
                }
            }
        }

        // 3. Tools & Open-Source Export
        item {
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
            ) {
                Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Text(
                        text = L("高级配置与便携工具", "Advanced & Portable Tools"),
                        style = MaterialTheme.typography.titleSmall,
                        fontWeight = FontWeight.Bold
                    )

                    FilledTonalButton(
                        onClick = { vm.shareBundledNotebook(context) },
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Icon(Icons.Default.Share, contentDescription = null, modifier = Modifier.size(16.dp))
                        Spacer(Modifier.width(6.dp))
                        Text(L("导出离线 EasyColab_Server.ipynb 脚本", "Export EasyColab_Server.ipynb"), maxLines = 1)
                    }

                    OutlinedButton(
                        onClick = { showCustomOAuthDialog = true },
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Icon(Icons.Default.Key, contentDescription = null, modifier = Modifier.size(16.dp))
                        Spacer(Modifier.width(6.dp))
                        Text(
                            text = if (vm.hasCustomOAuth) L("管理自定义 Google OAuth JSON (已启用)", "Custom Google OAuth JSON (Active)")
                            else L("导入自定义 Google OAuth JSON (可选)", "Custom Google OAuth JSON (Optional)"),
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis
                        )
                    }

                    OutlinedButton(
                        onClick = { vm.setOnboardingVisible(true) },
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Icon(Icons.AutoMirrored.Filled.HelpOutline, contentDescription = null, modifier = Modifier.size(16.dp))
                        Spacer(Modifier.width(6.dp))
                        Text(L("重新查看 4 步新手引导", "Reopen 4-Step Quick Guide"), maxLines = 1)
                    }
                }
            }
        }
    }

    if (showCustomOAuthDialog) {
        AlertDialog(
            onDismissRequest = { showCustomOAuthDialog = false },
            title = { Text(L("自定义 Google OAuth 客户端 JSON", "Custom Google OAuth Client JSON")) },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(
                        text = L(
                            "默认无需配置即可直接使用。如需使用自己在 Google Cloud Console 创建的桌面端 client_secret.json，可粘贴于此（留空保存即恢复默认）：",
                            "Built-in OAuth works out of the box. Paste your own Desktop client_secret.json to override, or save empty to restore default:"
                        ),
                        fontSize = 12.sp
                    )
                    OutlinedTextField(
                        value = customOAuthText,
                        onValueChange = { customOAuthText = it },
                        placeholder = { Text("{\"installed\":{\"client_id\":\"...\"}}") },
                        minLines = 4,
                        maxLines = 8,
                        modifier = Modifier.fillMaxWidth()
                    )
                }
            },
            confirmButton = {
                Button(onClick = {
                    vm.saveCustomOAuthConfig(customOAuthText)
                    showCustomOAuthDialog = false
                }) {
                    Text(L("保存", "Save"))
                }
            },
            dismissButton = {
                TextButton(onClick = { showCustomOAuthDialog = false }) {
                    Text(L("取消", "Cancel"))
                }
            }
        )
    }
}
