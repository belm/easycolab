package app.easycolab.studio

import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.viewModels
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.slideOutVertically
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.Cloud
import androidx.compose.material.icons.filled.Terminal
import androidx.compose.material.icons.filled.VideoLibrary
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner

private val EasyColabLightColors = lightColorScheme(
    primary = Color(0xFF2563EB),
    onPrimary = Color.White,
    secondary = Color(0xFF0891B2),
    background = Color(0xFFF3F5F9),
    surface = Color.White,
    surfaceVariant = Color(0xFFE5EAF2)
)

private val EasyColabDarkColors = darkColorScheme(
    primary = Color(0xFF60A5FA),
    onPrimary = Color(0xFF0B192C),
    secondary = Color(0xFF22D3EE),
    background = Color(0xFF0B1120),
    surface = Color(0xFF141D2F),
    surfaceVariant = Color(0xFF1E293B)
)

class MainActivity : ComponentActivity() {

    private val studioViewModel: StudioViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        consumeOAuthIntentIfPresent(intent)

        setContent {
            val darkTheme = isSystemInDarkTheme()
            MaterialTheme(
                colorScheme = if (darkTheme) EasyColabDarkColors else EasyColabLightColors
            ) {
                EasyColabRootApp(vm = studioViewModel)
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        consumeOAuthIntentIfPresent(intent)
    }

    private fun consumeOAuthIntentIfPresent(incoming: Intent?) {
        if (incoming != null && studioViewModel.handleOAuthCallbackIntent(incoming)) {
            incoming.data = null
        }
    }
}

@Composable
fun EasyColabRootApp(vm: StudioViewModel) {
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current

    DisposableEffect(lifecycleOwner) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_RESUME) {
                vm.onAppResumed(context)
            }
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose {
            lifecycleOwner.lifecycle.removeObserver(observer)
        }
    }

    Box(modifier = Modifier.fillMaxSize()) {
        Scaffold(
            bottomBar = {
                NavigationBar {
                    NavigationBarItem(
                        selected = vm.selectedTab == AppTab.CREATE,
                        onClick = { vm.selectedTab = AppTab.CREATE },
                        icon = { Icon(Icons.Default.AutoAwesome, contentDescription = null) },
                        label = { Text(L("创作台", "Create"), maxLines = 1, softWrap = false, overflow = TextOverflow.Ellipsis) }
                    )
                    NavigationBarItem(
                        selected = vm.selectedTab == AppTab.CLOUD,
                        onClick = { vm.selectedTab = AppTab.CLOUD },
                        icon = { Icon(Icons.Default.Cloud, contentDescription = null) },
                        label = { Text(L("云算力", "Cloud"), maxLines = 1, softWrap = false, overflow = TextOverflow.Ellipsis) }
                    )
                    NavigationBarItem(
                        selected = vm.selectedTab == AppTab.GALLERY,
                        onClick = { vm.selectedTab = AppTab.GALLERY },
                        icon = { Icon(Icons.Default.VideoLibrary, contentDescription = null) },
                        label = { Text(L("作品库", "Gallery"), maxLines = 1, softWrap = false, overflow = TextOverflow.Ellipsis) }
                    )
                    NavigationBarItem(
                        selected = vm.selectedTab == AppTab.SETTINGS,
                        onClick = { vm.selectedTab = AppTab.SETTINGS },
                        icon = { Icon(Icons.Default.Terminal, contentDescription = null) },
                        label = { Text(L("设置", "Console"), maxLines = 1, softWrap = false, overflow = TextOverflow.Ellipsis) }
                    )
                }
            }
        ) { innerPadding ->
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(innerPadding)
            ) {
                when (vm.selectedTab) {
                    AppTab.CREATE -> CreateTabScreen(vm = vm)
                    AppTab.CLOUD -> CloudGpuTabScreen(vm = vm)
                    AppTab.GALLERY -> GalleryTabScreen(vm = vm)
                    AppTab.SETTINGS -> ConsoleAndSettingsTabScreen(vm = vm)
                }
            }
        }

        // Floating Toast Banner
        AnimatedVisibility(
            visible = vm.toastBanner != null,
            enter = slideInVertically(initialOffsetY = { -it }) + fadeIn(),
            exit = slideOutVertically(targetOffsetY = { -it }) + fadeOut(),
            modifier = Modifier
                .align(Alignment.TopCenter)
                .statusBarsPadding()
                .padding(top = 10.dp, start = 20.dp, end = 20.dp)
        ) {
            Surface(
                shape = CircleShape,
                color = Color(0xFF0F172A).copy(alpha = 0.92f),
                shadowElevation = 6.dp
            ) {
                Text(
                    text = vm.toastBanner.orEmpty(),
                    color = Color.White,
                    fontSize = 13.sp,
                    fontWeight = FontWeight.Medium,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                    modifier = Modifier.padding(horizontal = 16.dp, vertical = 9.dp)
                )
            }
        }
    }

    if (vm.showOnboardingDialog) {
        OnboardingGuideDialog(
            onDismiss = { vm.setOnboardingVisible(false) },
            onJumpToCloud = {
                vm.setOnboardingVisible(false)
                vm.selectedTab = AppTab.CLOUD
            }
        )
    }
}

@Composable
private fun OnboardingGuideDialog(
    onDismiss: () -> Unit,
    onJumpToCloud: () -> Unit
) {
    var step by remember { mutableIntStateOf(0) }
    val steps = listOf(
        Triple(
            L("1. 一键绑定 Google 账号", "1. 1-Tap Google Sign-In"),
            L("在「云算力」页点击绑定 Google 账号，通过系统安全标签页完成授权后将自动跳回 App，实时同步付费 CU 余额。", "Sign in with Google via Chrome Custom Tabs — redirects right back to the app and syncs your paid CU balance."),
            "☁️"
        ),
        Triple(
            L("2. 免网页唤醒 G4 (96GB) 实例", "2. Headless G4 (96GB) Wake"),
            L("无需在手机浏览器打开 Colab 网页，一键分配 96GB 显存的 RTX PRO 6000 实例并自动挂载 Google Drive 云盘持久化权重。", "Provision an RTX PRO 6000 (96GB) VM headlessly with automatic rclone Google Drive weight persistence."),
            "⚡"
        ),
        Triple(
            L("3. 5 大多模态引擎 + ComfyUI", "3. 5 Multimodal Engines + ComfyUI"),
            L("畅玩 MiniMax-H3 有声视频、MiniMax-H3-Image 4K 直出、Z-Image 8 步生图、Qwen-Image 修图、Qwen3.8 256K 推理与 4 套预置视频工作流包。", "Create stereo audio-videos, native 4K images, posters, photo edits, 256K CoT reasoning, and 4 preset ComfyUI video packs."),
            "🎬"
        ),
        Triple(
            L("4. 自动存相册 & 零闲置扣费", "4. Auto-Save & Zero Idle Drain"),
            L("生成成片自动存入手机系统相册；闲置超时自动关机，也可随时一键销毁所有云端实例将扣费归零 (0.00 CU/h)。", "Outputs auto-save to Android Gallery; idle auto-sleep and 1-tap VM termination protect your CU balance."),
            "🛡️"
        )
    )

    val (title, body, iconText) = steps[step]

    AlertDialog(
        onDismissRequest = onDismiss,
        title = {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(iconText, fontSize = 22.sp)
                Spacer(Modifier.width(8.dp))
                Text(title, fontWeight = FontWeight.Bold, fontSize = 17.sp)
            }
        },
        text = {
            Column {
                Text(body, fontSize = 14.sp, lineHeight = 20.sp)
                Spacer(Modifier.height(12.dp))
                Text(
                    text = "${step + 1} / ${steps.size}",
                    fontSize = 12.sp,
                    color = MaterialTheme.colorScheme.primary,
                    fontWeight = FontWeight.SemiBold
                )
            }
        },
        confirmButton = {
            if (step < steps.lastIndex) {
                Button(onClick = { step += 1 }) {
                    Text(L("下一步", "Next"))
                }
            } else {
                Button(onClick = onJumpToCloud) {
                    Text(L("前往云算力绑定", "Go to Cloud Tab"))
                }
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text(L("跳过", "Skip"))
            }
        },
        shape = RoundedCornerShape(20.dp)
    )
}
