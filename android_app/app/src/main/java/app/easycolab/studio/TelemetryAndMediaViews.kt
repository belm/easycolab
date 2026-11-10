package app.easycolab.studio

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.media.MediaMetadataRetriever
import android.net.Uri
import android.view.ViewGroup
import android.widget.FrameLayout
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.GridItemSpan
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.DeleteOutline
import androidx.compose.material.icons.filled.Download
import androidx.compose.material.icons.filled.Image
import androidx.compose.material.icons.filled.Memory
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Share
import androidx.compose.material.icons.filled.VideoLibrary
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.clipToBounds
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.media3.common.MediaItem
import androidx.media3.common.Player
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.ui.PlayerView
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File
import java.util.Locale

private data class TelemetrySeriesItem(
    val label: String,
    val detail: String,
    val samples: List<Float>,
    val color: Color
)

@Composable
fun SmoothTelemetryChartCard(vm: StudioViewModel) {
    val series = listOf(
        TelemetrySeriesItem(
            label = "VRAM",
            detail = if (vm.vramTotalGB > 0) String.format(Locale.US, "%.1f/%.0fG", vm.vramUsedGB, vm.vramTotalGB) else "--",
            samples = vm.vramHistoryPct.toList(),
            color = Color(0xFF06B6D4)
        ),
        TelemetrySeriesItem(
            label = "RAM",
            detail = if (vm.ramTotalGB > 0) String.format(Locale.US, "%.1f/%.0fG", vm.ramUsedGB, vm.ramTotalGB) else "--",
            samples = vm.ramHistoryPct.toList(),
            color = Color(0xFF3B82F6)
        ),
        TelemetrySeriesItem(
            label = L("磁盘", "Disk"),
            detail = if (vm.diskTotalGB > 0) String.format(Locale.US, "%.0f/%.0fG", vm.diskUsedGB, vm.diskTotalGB) else "--",
            samples = vm.diskHistoryPct.toList(),
            color = Color(0xFFF97316)
        )
    )

    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
    ) {
        Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.weight(1f)) {
                    Icon(
                        Icons.Default.Memory,
                        contentDescription = null,
                        tint = Color(0xFF06B6D4),
                        modifier = Modifier.size(18.dp)
                    )
                    Spacer(Modifier.width(6.dp))
                    Text(
                        text = L("云端硬件实时遥测", "Live Cloud Telemetry"),
                        style = MaterialTheme.typography.titleSmall,
                        fontWeight = FontWeight.SemiBold,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis
                    )
                }

                Surface(
                    shape = CircleShape,
                    color = MaterialTheme.colorScheme.surfaceVariant,
                    modifier = Modifier.clickable { vm.combinedTelemetryChartMode = !vm.combinedTelemetryChartMode }
                ) {
                    Text(
                        text = if (vm.combinedTelemetryChartMode) L("同图叠加", "Overlay") else L("分栏曲线", "Split"),
                        style = MaterialTheme.typography.labelSmall,
                        fontWeight = FontWeight.Medium,
                        maxLines = 1,
                        softWrap = false,
                        modifier = Modifier.padding(horizontal = 10.dp, vertical = 5.dp)
                    )
                }
            }

            if (vm.combinedTelemetryChartMode) {
                BezierMultiLineCanvas(
                    series = series,
                    showArea = true,
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(104.dp)
                )
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    series.forEach { item ->
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Box(
                                modifier = Modifier
                                    .size(7.dp)
                                    .clip(CircleShape)
                                    .background(item.color)
                            )
                            Spacer(Modifier.width(4.dp))
                            Text(
                                text = "${item.label} ${item.detail}",
                                fontSize = 11.sp,
                                fontFamily = FontFamily.Monospace,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                                maxLines = 1,
                                softWrap = false
                            )
                        }
                    }
                }
            } else {
                series.forEach { item ->
                    Column(verticalArrangement = Arrangement.spacedBy(3.dp)) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Text(
                                text = item.label,
                                fontSize = 11.sp,
                                fontWeight = FontWeight.SemiBold,
                                color = item.color,
                                maxLines = 1
                            )
                            Text(
                                text = item.detail,
                                fontSize = 11.sp,
                                fontFamily = FontFamily.Monospace,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                                maxLines = 1
                            )
                        }
                        BezierMultiLineCanvas(
                            series = listOf(item),
                            showArea = true,
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(42.dp)
                        )
                    }
                }
            }

            if (vm.driveTotalGB > 0.0) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = L("Google Drive 云盘", "Google Drive"),
                        fontSize = 11.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        maxLines = 1
                    )
                    Text(
                        text = String.format(
                            Locale.US,
                            "%.1f / %.0f GB (%s %.1f GB)",
                            vm.driveUsedGB,
                            vm.driveTotalGB,
                            L("剩余", "Free"),
                            vm.driveFreeGB
                        ),
                        fontSize = 11.sp,
                        fontFamily = FontFamily.Monospace,
                        color = Color(0xFF10B981),
                        maxLines = 1
                    )
                }
            }
        }
    }
}

@Composable
private fun BezierMultiLineCanvas(
    series: List<TelemetrySeriesItem>,
    showArea: Boolean,
    modifier: Modifier = Modifier
) {
    Canvas(
        modifier = modifier
            .clip(RoundedCornerShape(10.dp))
            .background(MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.45f))
    ) {
        val w = size.width
        val h = size.height
        val padY = 6.dp.toPx()
        val usableH = (h - padY * 2f).coerceAtLeast(4f)

        listOf(0.25f, 0.5f, 0.75f).forEach { frac ->
            val y = padY + usableH * (1f - frac)
            drawLine(
                color = Color.Gray.copy(alpha = 0.16f),
                start = Offset(0f, y),
                end = Offset(w, y),
                strokeWidth = 1f
            )
        }

        series.forEach { item ->
            val pts = if (item.samples.size >= 2) item.samples else listOf(0f, 0f)
            val stepX = w / (pts.size - 1).coerceAtLeast(1).toFloat()
            val coords = pts.mapIndexed { idx, v ->
                Offset(
                    x = idx * stepX,
                    y = padY + usableH * (1f - v.coerceIn(0f, 1f))
                )
            }

            val linePath = Path().apply {
                moveTo(coords.first().x, coords.first().y)
                for (i in 1 until coords.size) {
                    val prev = coords[i - 1]
                    val cur = coords[i]
                    val midX = (prev.x + cur.x) * 0.5f
                    cubicTo(midX, prev.y, midX, cur.y, cur.x, cur.y)
                }
            }

            if (showArea) {
                val areaPath = Path().apply {
                    addPath(linePath)
                    lineTo(coords.last().x, h)
                    lineTo(coords.first().x, h)
                    close()
                }
                drawPath(
                    path = areaPath,
                    brush = Brush.verticalGradient(
                        colors = listOf(item.color.copy(alpha = 0.24f), item.color.copy(alpha = 0.01f)),
                        startY = 0f,
                        endY = h
                    )
                )
            }

            drawPath(
                path = linePath,
                color = item.color,
                style = Stroke(width = 2.2.dp.toPx(), cap = StrokeCap.Round)
            )
        }
    }
}

@Composable
fun ExoVideoPlayerView(
    videoFile: File,
    autoPlay: Boolean = true,
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    val exoPlayer = remember(context) {
        ExoPlayer.Builder(context).build().apply {
            repeatMode = Player.REPEAT_MODE_ONE
        }
    }

    LaunchedEffect(videoFile.absolutePath) {
        exoPlayer.setMediaItem(MediaItem.fromUri(Uri.fromFile(videoFile)))
        exoPlayer.prepare()
        exoPlayer.playWhenReady = autoPlay
    }

    DisposableEffect(exoPlayer) {
        onDispose {
            exoPlayer.release()
        }
    }

    AndroidView(
        factory = { ctx ->
            PlayerView(ctx).apply {
                player = exoPlayer
                useController = true
                clipChildren = true
                clipToPadding = true
                layoutParams = FrameLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT,
                    ViewGroup.LayoutParams.MATCH_PARENT
                )
            }
        },
        update = { view ->
            if (view.player !== exoPlayer) {
                view.player = exoPlayer
            }
        },
        modifier = modifier
            .clipToBounds()
            .clip(RoundedCornerShape(12.dp))
            .background(Color.Black)
    )
}

@Composable
fun MediaStageCard(vm: StudioViewModel) {
    val file = vm.currentMediaFile ?: return
    if (!file.exists()) return
    val context = LocalContext.current
    val isVideo = file.extension.equals("mp4", ignoreCase = true)
    var showDeleteConfirm by remember(file.absolutePath) { mutableStateOf(false) }

    if (showDeleteConfirm) {
        AlertDialog(
            onDismissRequest = { showDeleteConfirm = false },
            title = { Text(L("确认删除该作品？", "Delete this media item?")) },
            text = {
                Text(
                    L(
                        "将从 EasyColab 本地作品库中移除「${file.name}」（已存入系统相册的副本不受影响）。",
                        "Remove \"${file.name}\" from EasyColab's local gallery (copies already saved to Android Gallery are unaffected)."
                    )
                )
            },
            confirmButton = {
                TextButton(
                    onClick = {
                        showDeleteConfirm = false
                        vm.deleteLocalMediaFile(file)
                    },
                    colors = ButtonDefaults.textButtonColors(contentColor = MaterialTheme.colorScheme.error)
                ) {
                    Text(L("确认删除", "Delete"), fontWeight = FontWeight.Bold)
                }
            },
            dismissButton = {
                TextButton(onClick = { showDeleteConfirm = false }) {
                    Text(L("取消", "Cancel"))
                }
            }
        )
    }

    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
    ) {
        Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = file.name,
                    style = MaterialTheme.typography.labelMedium,
                    fontWeight = FontWeight.SemiBold,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                    modifier = Modifier.weight(1f)
                )
                vm.lastCompletedElapsed?.let { sec ->
                    Spacer(Modifier.width(8.dp))
                    Text(
                        text = formatDuration(sec, compact = true),
                        fontSize = 11.sp,
                        fontFamily = FontFamily.Monospace,
                        color = Color(0xFF10B981),
                        maxLines = 1
                    )
                }
            }

            if (isVideo) {
                ExoVideoPlayerView(
                    videoFile = file,
                    autoPlay = true,
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(250.dp)
                )
            } else {
                val bmp = vm.currentPreviewBitmap
                if (bmp != null) {
                    Image(
                        bitmap = bmp.asImageBitmap(),
                        contentDescription = file.name,
                        contentScale = ContentScale.Fit,
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(280.dp)
                            .clip(RoundedCornerShape(12.dp))
                            .background(Color.Black.copy(alpha = 0.9f))
                    )
                }
            }

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                FilledTonalButton(
                    onClick = { vm.saveMediaToSystemGallery(file, silent = false) },
                    modifier = Modifier.weight(1f),
                    shape = RoundedCornerShape(10.dp),
                    contentPadding = PaddingValues(horizontal = 8.dp, vertical = 8.dp)
                ) {
                    Icon(Icons.Default.Download, contentDescription = null, modifier = Modifier.size(16.dp))
                    Spacer(Modifier.width(4.dp))
                    Text(L("存相册", "Save"), fontSize = 12.sp, maxLines = 1, overflow = TextOverflow.Ellipsis)
                }
                FilledTonalButton(
                    onClick = { vm.shareMediaFile(context, file) },
                    modifier = Modifier.weight(1f),
                    shape = RoundedCornerShape(10.dp),
                    contentPadding = PaddingValues(horizontal = 8.dp, vertical = 8.dp)
                ) {
                    Icon(Icons.Default.Share, contentDescription = null, modifier = Modifier.size(16.dp))
                    Spacer(Modifier.width(4.dp))
                    Text(L("分享", "Share"), fontSize = 12.sp, maxLines = 1, overflow = TextOverflow.Ellipsis)
                }
                FilledTonalButton(
                    onClick = { showDeleteConfirm = true },
                    modifier = Modifier.weight(0.85f),
                    shape = RoundedCornerShape(10.dp),
                    colors = ButtonDefaults.filledTonalButtonColors(
                        containerColor = MaterialTheme.colorScheme.error.copy(alpha = 0.14f),
                        contentColor = MaterialTheme.colorScheme.error
                    ),
                    contentPadding = PaddingValues(horizontal = 8.dp, vertical = 8.dp)
                ) {
                    Icon(Icons.Default.DeleteOutline, contentDescription = null, modifier = Modifier.size(16.dp))
                    Spacer(Modifier.width(4.dp))
                    Text(L("删除", "Delete"), fontSize = 12.sp, maxLines = 1, overflow = TextOverflow.Ellipsis)
                }
            }
        }
    }
}

@Composable
fun GalleryTabScreen(vm: StudioViewModel) {
    val context = LocalContext.current
    var pendingDeleteItem by remember { mutableStateOf<LocalMediaItem?>(null) }

    pendingDeleteItem?.let { target ->
        AlertDialog(
            onDismissRequest = { pendingDeleteItem = null },
            title = { Text(L("确认删除该作品？", "Delete this media item?")) },
            text = {
                Text(
                    L(
                        "将从 EasyColab 本地作品库中移除「${target.filename}」（已存入系统相册的副本不受影响）。",
                        "Remove \"${target.filename}\" from EasyColab's local gallery (copies already saved to Android Gallery are unaffected)."
                    )
                )
            },
            confirmButton = {
                TextButton(
                    onClick = {
                        pendingDeleteItem = null
                        vm.deleteLocalMedia(target)
                    },
                    colors = ButtonDefaults.textButtonColors(contentColor = MaterialTheme.colorScheme.error)
                ) {
                    Text(L("确认删除", "Delete"), fontWeight = FontWeight.Bold)
                }
            },
            dismissButton = {
                TextButton(onClick = { pendingDeleteItem = null }) {
                    Text(L("取消", "Cancel"))
                }
            }
        )
    }

    LazyVerticalGrid(
        columns = GridCells.Adaptive(minSize = 156.dp),
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background),
        contentPadding = PaddingValues(horizontal = 14.dp, vertical = 12.dp),
        horizontalArrangement = Arrangement.spacedBy(10.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        item(span = { GridItemSpan(maxLineSpan) }) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = L("本地作品库", "Local Gallery"),
                        style = MaterialTheme.typography.titleLarge,
                        fontWeight = FontWeight.Bold,
                        maxLines = 1
                    )
                    Text(
                        text = L(
                            "共 ${vm.localMediaItems.size} 个作品 · 支持一键导出系统相册与分享",
                            "${vm.localMediaItems.size} items · 1-tap export to Android Gallery & Share"
                        ),
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis
                    )
                }
                IconButton(onClick = { vm.refreshLocalMedia() }) {
                    Icon(Icons.Default.Refresh, contentDescription = "Refresh")
                }
            }
        }

        if (vm.currentMediaFile != null) {
            item(span = { GridItemSpan(maxLineSpan) }) {
                MediaStageCard(vm = vm)
            }
        }

        if (vm.localMediaItems.isEmpty()) {
            item(span = { GridItemSpan(maxLineSpan) }) {
                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(top = 24.dp),
                    shape = RoundedCornerShape(16.dp),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
                ) {
                    Column(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(vertical = 40.dp, horizontal = 20.dp),
                        horizontalAlignment = Alignment.CenterHorizontally,
                        verticalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        Icon(
                            Icons.Default.VideoLibrary,
                            contentDescription = null,
                            tint = MaterialTheme.colorScheme.primary.copy(alpha = 0.7f),
                            modifier = Modifier.size(40.dp)
                        )
                        Text(
                            text = L("暂无已下载作品", "No Downloaded Media Yet"),
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.SemiBold
                        )
                        Text(
                            text = L(
                                "在「创作台」生成有声视频、海报图片或拉取 ComfyUI 成片后，将自动保存在此处。",
                                "Generated stereo videos, images, and pulled ComfyUI outputs appear here automatically."
                            ),
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
            }
        } else {
            items(vm.localMediaItems, key = { it.file.absolutePath }) { item ->
                val isSelected = vm.currentMediaFile?.absolutePath == item.file.absolutePath
                GalleryThumbCard(
                    item = item,
                    isSelected = isSelected,
                    onSelect = { vm.selectMedia(item.file) },
                    onSave = { vm.saveMediaToSystemGallery(item.file, silent = false) },
                    onShare = { vm.shareMediaFile(context, item.file) },
                    onDelete = { pendingDeleteItem = item }
                )
            }
        }
    }
}

@Composable
private fun GalleryThumbCard(
    item: LocalMediaItem,
    isSelected: Boolean,
    onSelect: () -> Unit,
    onSave: () -> Unit,
    onShare: () -> Unit,
    onDelete: () -> Unit
) {
    var thumbBitmap by remember(item.file.absolutePath) { mutableStateOf<Bitmap?>(null) }

    LaunchedEffect(item.file.absolutePath) {
        thumbBitmap = withContext(Dispatchers.IO) {
            try {
                if (item.isImage) {
                    val opts = BitmapFactory.Options().apply { inSampleSize = 2 }
                    BitmapFactory.decodeFile(item.file.absolutePath, opts)
                } else {
                    val retriever = MediaMetadataRetriever()
                    try {
                        retriever.setDataSource(item.file.absolutePath)
                        retriever.getFrameAtTime(200_000L, MediaMetadataRetriever.OPTION_CLOSEST_SYNC)
                    } finally {
                        retriever.release()
                    }
                }
            } catch (_: Exception) {
                null
            }
        }
    }

    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(14.dp),
        border = if (isSelected) BorderStroke(2.dp, MaterialTheme.colorScheme.primary) else null,
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
    ) {
        Column {
            // Only the preview & metadata zone triggers selection, preventing touch competition with action buttons
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .clickable { onSelect() }
            ) {
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .aspectRatio(1.15f)
                        .background(Color(0xFF111827))
                ) {
                    if (thumbBitmap != null) {
                        Image(
                            bitmap = thumbBitmap!!.asImageBitmap(),
                            contentDescription = item.filename,
                            contentScale = ContentScale.Crop,
                            modifier = Modifier.fillMaxSize()
                        )
                    } else {
                        Icon(
                            imageVector = if (item.isImage) Icons.Default.Image else Icons.Default.VideoLibrary,
                            contentDescription = null,
                            tint = Color.White.copy(alpha = 0.5f),
                            modifier = Modifier
                                .size(32.dp)
                                .align(Alignment.Center)
                        )
                    }

                    if (!item.isImage) {
                        Surface(
                            shape = CircleShape,
                            color = Color.Black.copy(alpha = 0.55f),
                            modifier = Modifier
                                .align(Alignment.Center)
                                .size(34.dp)
                        ) {
                            Box(contentAlignment = Alignment.Center) {
                                Icon(
                                    Icons.Default.PlayArrow,
                                    contentDescription = null,
                                    tint = Color.White,
                                    modifier = Modifier.size(20.dp)
                                )
                            }
                        }
                    }

                    item.elapsedSeconds?.let { sec ->
                        Surface(
                            shape = RoundedCornerShape(6.dp),
                            color = Color.Black.copy(alpha = 0.68f),
                            modifier = Modifier
                                .align(Alignment.BottomEnd)
                                .padding(6.dp)
                        ) {
                            Text(
                                text = formatDuration(sec, compact = true),
                                color = Color(0xFF34D399),
                                fontSize = 10.sp,
                                fontFamily = FontFamily.Monospace,
                                maxLines = 1,
                                modifier = Modifier.padding(horizontal = 5.dp, vertical = 2.dp)
                            )
                        }
                    }
                }

                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 8.dp, vertical = 6.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = item.filename,
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Medium,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                        modifier = Modifier.weight(1f)
                    )
                    Spacer(Modifier.width(6.dp))
                    Text(
                        text = String.format(Locale.US, "%.1f MB", item.fileSizeMb),
                        fontSize = 10.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        maxLines = 1
                    )
                }
            }

            HorizontalDivider(color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.65f))

            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 4.dp, vertical = 3.dp),
                horizontalArrangement = Arrangement.SpaceEvenly,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Surface(
                    onClick = onSave,
                    shape = RoundedCornerShape(8.dp),
                    color = Color.Transparent,
                    modifier = Modifier
                        .weight(1f)
                        .height(34.dp)
                ) {
                    Box(contentAlignment = Alignment.Center) {
                        Icon(
                            Icons.Default.Download,
                            contentDescription = L("存入相册", "Save to Gallery"),
                            tint = MaterialTheme.colorScheme.primary,
                            modifier = Modifier.size(18.dp)
                        )
                    }
                }
                Surface(
                    onClick = onShare,
                    shape = RoundedCornerShape(8.dp),
                    color = Color.Transparent,
                    modifier = Modifier
                        .weight(1f)
                        .height(34.dp)
                ) {
                    Box(contentAlignment = Alignment.Center) {
                        Icon(
                            Icons.Default.Share,
                            contentDescription = L("分享", "Share"),
                            tint = MaterialTheme.colorScheme.onSurface,
                            modifier = Modifier.size(17.dp)
                        )
                    }
                }
                Surface(
                    onClick = onDelete,
                    shape = RoundedCornerShape(8.dp),
                    color = Color.Transparent,
                    modifier = Modifier
                        .weight(1f)
                        .height(34.dp)
                ) {
                    Box(contentAlignment = Alignment.Center) {
                        Icon(
                            Icons.Default.DeleteOutline,
                            contentDescription = L("删除", "Delete"),
                            tint = MaterialTheme.colorScheme.error,
                            modifier = Modifier.size(18.dp)
                        )
                    }
                }
            }
        }
    }
}
