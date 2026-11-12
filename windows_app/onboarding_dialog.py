"""
4-Step Interactive Onboarding Wizard (ColabGuideDialog, 860x580)
for the EasyColab Windows Client — 1:1 parity with macOS ColabGuideSheet.
"""
from __future__ import annotations

import webbrowser
from typing import List, Optional, Tuple

from PySide6.QtCore import Qt
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from windows_app.models import get_local_save_dir, is_en, open_path_in_os, tr
from windows_app.theme import DARK_PALETTE, LIGHT_PALETTE, build_stylesheet, draw_easycolab_icon_pixmap
from windows_app.viewmodel import EasyColabViewModel
from windows_app.widgets import PillBadge, StatusDot, set_btn_role


def get_onboarding_steps() -> List[Tuple[str, str, str]]:
    return [
        (
            tr("连接云端 96GB 显卡", "Connect 96GB Cloud GPU"),
            tr(
                "免开网页一键唤醒 G4 实例，或通过浏览器手动运行笔记本",
                "Wake a G4 runtime headless in 1 click, or run the notebook in browser",
            ),
            tr(
                "提示：首次绑定 Google 账号后，后续每次打开只需点一下「唤醒实例并部署」。",
                "Tip: After binding your Google account once, just click 'Wake & Deploy' next time.",
            ),
        ),
        (
            tr("下载与加载开源模型", "Download & Load Models"),
            tr(
                "Google Drive 权重持久化 + G4 176GB 内存热备与多模型共驻",
                "Google Drive weight persistence + G4 176GB RAM hot-cache & multi-model co-residency",
            ),
            tr(
                "提示：同一实例内可同时加载 Qwen3.8 对话网关与生图/生视频模型，零切换共存。",
                "Tip: Co-reside Qwen3.8 LLM gateway alongside image/video models in VRAM with zero switching.",
            ),
        ),
        (
            tr("四大模式快速上手", "Explore 4 Studio Modes"),
            tr(
                "有声视频、ComfyUI 中文傻瓜画布、百词极速对话网关与 2K 修图",
                "Audio-video generation, ComfyUI guided workflows, 100 tok/s LLM gateway & 2K image editing",
            ),
            tr(
                "提示：点击任意卡片按钮即可直接切换至对应创作工作台。",
                "Tip: Click any card button above to jump directly to that studio workspace.",
            ),
        ),
        (
            tr("作品保存与省额度秘籍", "Media Saving & CU Tips"),
            tr(
                "成片自动回传本地 Videos 目录 + 30 分钟闲置自动释放实例",
                "Outputs auto-download to local Videos folder + 30-min idle auto-shutdown",
            ),
            tr(
                "提示：创作结束后点击左下角「释放全部实例」，确保计费速率立即归零。",
                "Tip: Click 'Release All Runtimes' at bottom-left when finished so CU burn drops to zero immediately.",
            ),
        ),
    ]


class ColabGuideDialog(QDialog):
    """Modal 4-step interactive onboarding guide with live bilingual toggle."""

    def __init__(self, vm: EasyColabViewModel, initial_step: int = 0, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.vm = vm
        self._step = max(0, min(3, initial_step))
        self.setFixedSize(860, 580)
        self.setModal(True)

        self._pal = DARK_PALETTE if vm.dark_mode else LIGHT_PALETTE
        self._root_layout = QHBoxLayout(self)
        self._root_layout.setContentsMargins(0, 0, 0, 0)
        self._root_layout.setSpacing(0)

        self._populate_ui()

        self.vm.state_changed.connect(self._refresh_live_health)
        self.vm.language_changed.connect(self._on_language_changed)
        self.vm.theme_changed.connect(self._on_language_changed)
        self.finished.connect(self._disconnect_vm_signals)

    def _disconnect_vm_signals(self) -> None:
        for sig, slot in (
            (self.vm.state_changed, self._refresh_live_health),
            (self.vm.language_changed, self._on_language_changed),
            (self.vm.theme_changed, self._on_language_changed),
        ):
            try:
                sig.disconnect(slot)
            except Exception:
                pass

    @staticmethod
    def _clear_layout(layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.hide()
                w.setParent(None)
                w.deleteLater()
            elif item.layout() is not None:
                ColabGuideDialog._clear_layout(item.layout())

    def _on_language_changed(self) -> None:
        saved_step = self._step
        self._clear_layout(self._root_layout)
        self._step = saved_step
        self._populate_ui()

    def _populate_ui(self) -> None:
        pal = DARK_PALETTE if self.vm.dark_mode else LIGHT_PALETTE
        self._pal = pal
        self.setWindowTitle(tr("EasyColab 快速上手指南", "EasyColab Quick Start Guide"))
        self.setStyleSheet(build_stylesheet(pal))

        steps = get_onboarding_steps()

        # ── Left Navigation Pane (236px) ──
        left = QWidget()
        left.setObjectName("LeftSidebarContainer")
        left.setFixedWidth(236)
        left_lay = QVBoxLayout(left)
        left_lay.setContentsMargins(16, 18, 16, 16)
        left_lay.setSpacing(10)

        brand_row = QHBoxLayout()
        brand_row.setSpacing(10)
        icon_lbl = QLabel()
        icon_lbl.setPixmap(draw_easycolab_icon_pixmap(34))
        brand_row.addWidget(icon_lbl)
        brand_txt_col = QVBoxLayout()
        brand_txt_col.setSpacing(1)
        b_title = QLabel(tr("EasyColab 指南", "EasyColab Guide"))
        b_title.setStyleSheet("font-size: 14px; font-weight: 700;")
        b_sub = QLabel(tr("3 分钟零基础快速上手", "3-minute beginner walkthrough"))
        b_sub.setStyleSheet(f"font-size: 11px; color: {pal.text_secondary};")
        brand_txt_col.addWidget(b_title)
        brand_txt_col.addWidget(b_sub)
        brand_row.addLayout(brand_txt_col, 1)
        left_lay.addLayout(brand_row)
        left_lay.addSpacing(6)

        self._nav_buttons: List[QPushButton] = []
        for idx, (st_title, _sub, _tip) in enumerate(steps):
            btn = QPushButton(f"0{idx + 1}  {st_title}")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(38)
            btn.clicked.connect(lambda _checked=False, i=idx: self.set_step(i))
            left_lay.addWidget(btn)
            self._nav_buttons.append(btn)

        left_lay.addStretch(1)

        # Live health card at bottom-left
        health = QFrame()
        health.setObjectName("SidebarCard")
        h_lay = QVBoxLayout(health)
        h_lay.setContentsMargins(10, 9, 10, 9)
        h_lay.setSpacing(6)
        h_hdr = QLabel(tr("当前环境状态", "Environment Status"))
        h_hdr.setStyleSheet(f"font-size: 11px; font-weight: 700; color: {pal.text_secondary};")
        h_lay.addWidget(h_hdr)

        acc_row = QHBoxLayout()
        acc_row.setSpacing(6)
        self.acc_dot = StatusDot("#10B981" if self.vm.cli_logged_in else "#F59E0B", size=8)
        self.acc_lbl = QLabel()
        self.acc_lbl.setStyleSheet("font-size: 11px;")
        acc_row.addWidget(self.acc_dot)
        acc_row.addWidget(self.acc_lbl, 1)
        h_lay.addLayout(acc_row)

        gpu_row = QHBoxLayout()
        gpu_row.setSpacing(6)
        self.gpu_dot = StatusDot("#10B981" if self.vm.is_connected else "#F59E0B", size=8)
        self.gpu_lbl = QLabel()
        self.gpu_lbl.setStyleSheet("font-size: 11px;")
        gpu_row.addWidget(self.gpu_dot)
        gpu_row.addWidget(self.gpu_lbl, 1)
        h_lay.addLayout(gpu_row)

        left_lay.addWidget(health)
        self._root_layout.addWidget(left)

        # ── Right Content Pane ──
        right = QWidget()
        right.setObjectName("CenterWorkspaceContainer")
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(24, 20, 24, 18)
        right_lay.setSpacing(12)

        # Top header
        top_row = QHBoxLayout()
        top_row.setSpacing(8)
        title_col = QVBoxLayout()
        title_col.setSpacing(4)
        badge_fg = "#60A5FA" if pal.is_dark else "#2563EB"
        self.step_badge = PillBadge("STEP 01 / 04", fg=badge_fg, bg="rgba(59, 130, 246, 0.14)", mono=True)
        self.step_badge.setFixedWidth(104)
        title_col.addWidget(self.step_badge)
        self.step_title_lbl = QLabel()
        self.step_title_lbl.setStyleSheet("font-size: 18px; font-weight: 700;")
        title_col.addWidget(self.step_title_lbl)
        self.step_sub_lbl = QLabel()
        self.step_sub_lbl.setStyleSheet(f"font-size: 12px; color: {pal.text_secondary};")
        title_col.addWidget(self.step_sub_lbl)
        top_row.addLayout(title_col, 1)

        self.lang_btn = set_btn_role(QPushButton("EN" if not is_en() else "中文"), "pill")
        self.lang_btn.setFixedHeight(28)
        self.lang_btn.setToolTip(tr("切换界面为英文 (Switch to English)", "Switch UI to Chinese (切换为中文)"))
        self.lang_btn.clicked.connect(self.vm.toggle_language)
        top_row.addWidget(self.lang_btn, 0, Qt.AlignmentFlag.AlignTop)

        self.close_btn = set_btn_role(QPushButton(tr("关闭", "Close")), "ghost")
        self.close_btn.setFixedHeight(28)
        self.close_btn.clicked.connect(self._close_and_mark_seen)
        top_row.addWidget(self.close_btn, 0, Qt.AlignmentFlag.AlignTop)
        right_lay.addLayout(top_row)

        # Stacked 4 pages inside ScrollArea
        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_step_1())
        self.stack.addWidget(self._build_step_2())
        self.stack.addWidget(self._build_step_3())
        self.stack.addWidget(self._build_step_4())
        right_lay.addWidget(self.stack, 1)

        # Bottom navigation bar
        bot = QHBoxLayout()
        bot.setSpacing(10)
        self.tip_lbl = QLabel()
        self.tip_lbl.setWordWrap(True)
        self.tip_lbl.setStyleSheet(f"font-size: 11.5px; color: {pal.text_secondary};")
        bot.addWidget(self.tip_lbl, 1)

        self.prev_btn = QPushButton(tr("上一步", "Previous"))
        self.prev_btn.clicked.connect(lambda: self.set_step(self._step - 1))
        bot.addWidget(self.prev_btn)

        self.next_btn = set_btn_role(QPushButton(tr("下一步", "Next")), "primary")
        self.next_btn.clicked.connect(self._on_next_clicked)
        bot.addWidget(self.next_btn)

        right_lay.addLayout(bot)
        self._root_layout.addWidget(right, 1)

        self._refresh_live_health()
        self.set_step(self._step)

    def _make_card(self, title: str, desc: str, action_widget: Optional[QWidget] = None) -> QFrame:
        card = QFrame()
        card.setObjectName("WorkspaceCard")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(6)
        t = QLabel(title)
        t.setStyleSheet("font-size: 13px; font-weight: 700;")
        lay.addWidget(t)
        d = QLabel(desc)
        d.setWordWrap(True)
        d.setStyleSheet(f"font-size: 12px; color: {self._pal.text_secondary}; line-height: 1.4;")
        lay.addWidget(d)
        if action_widget is not None:
            lay.addWidget(action_widget)
        return card

    def _wrap_scroll(self, cards: List[QWidget]) -> QScrollArea:
        sc = QScrollArea()
        sc.setWidgetResizable(True)
        body = QWidget()
        v = QVBoxLayout(body)
        v.setContentsMargins(0, 2, 6, 2)
        v.setSpacing(10)
        for c in cards:
            v.addWidget(c)
        v.addStretch(1)
        sc.setWidget(body)
        return sc

    def _build_step_1(self) -> QWidget:
        # Card 1: OAuth bind
        row1 = QWidget()
        r1 = QHBoxLayout(row1)
        r1.setContentsMargins(0, 2, 0, 0)
        self.bind_now_btn = set_btn_role(QPushButton(tr("现在去绑定 Google 账号", "Bind Google Account Now")), "primary")
        self.bind_now_btn.clicked.connect(self._action_bind_account)
        self.bound_ok_lbl = QLabel(tr("你的 Google 账号已完成绑定", "Google account connected"))
        self.bound_ok_lbl.setStyleSheet("color: #059669; font-weight: 600; font-size: 12px;")
        r1.addWidget(self.bind_now_btn)
        r1.addWidget(self.bound_ok_lbl)
        r1.addStretch(1)
        c1 = self._make_card(
            tr("1. 绑定 Google 账号（仅首次需要一次）", "1. Bind Google Account (One-time setup)"),
            tr(
                "点击左侧「绑定」按钮完成官方 OAuth 授权，凭证仅加密保存在你本机的 ~/.config/colab-cli/token.json，自动同步真实 CU 计算单元余额。",
                "Click 'Bind' in the left sidebar to complete official OAuth login. Credentials stay locally in ~/.config/colab-cli/token.json and sync live CU balance.",
            ),
            row1,
        )

        # Card 2: One-click G4 wake
        row2 = QWidget()
        r2 = QHBoxLayout(row2)
        r2.setContentsMargins(0, 2, 0, 0)
        self.wake_now_btn = set_btn_role(QPushButton(tr("立即一键唤醒 G4 并部署", "Wake G4 & Deploy Now")), "primary")
        self.wake_now_btn.clicked.connect(self._action_wake_g4)
        r2.addWidget(self.wake_now_btn)
        r2.addStretch(1)
        c2 = self._make_card(
            tr("2. 选择 G4 机型并点击「唤醒实例并部署」（免开网页）", "2. Select G4 & Click 'Wake & Deploy' (Headless)"),
            tr(
                "自动分配 NVIDIA RTX PRO 6000 Blackwell (96GB 显存 + 176GB 内存)，上传多模型加速引擎并返回加密隧道，全程无需打开浏览器。",
                "Automatically allocates an NVIDIA RTX PRO 6000 Blackwell (96GB VRAM + 176GB RAM), deploys the multi-model server, and connects via encrypted tunnel without opening a browser.",
            ),
            row2,
        )

        # Card 3: Manual notebook fallback
        row3 = QWidget()
        r3 = QHBoxLayout(row3)
        r3.setContentsMargins(0, 2, 0, 0)
        r3.setSpacing(8)
        exp_btn = QPushButton(tr("导出 / 定位 .ipynb 笔记本", "Export / Reveal .ipynb Notebook"))
        exp_btn.clicked.connect(self.vm.export_or_reveal_notebook)
        colab_btn = QPushButton(tr("打开 Google Colab 官网", "Open Google Colab Web"))
        colab_btn.clicked.connect(lambda: webbrowser.open("https://colab.research.google.com/"))
        r3.addWidget(exp_btn)
        r3.addWidget(colab_btn)
        r3.addStretch(1)
        c3 = self._make_card(
            tr("备选方案：通过 Google Colab 网页端手动运行笔记本", "Alternative: Run Notebook Manually in Google Colab Browser"),
            tr(
                "若你使用 Colab 免费层或习惯浏览器操作，可上传内置的 EasyColab_Server.ipynb 运行，再将生成的 https://xxxx.gradio.live 粘贴到左侧连接。",
                "If using Colab Free tier or preferring browser notebooks, upload EasyColab_Server.ipynb, run it, and paste the https://xxxx.gradio.live URL into the left sidebar.",
            ),
            row3,
        )
        return self._wrap_scroll([c1, c2, c3])

    def _build_step_2(self) -> QWidget:
        c1 = self._make_card(
            tr("1. 先点「下载权重」：一次存入 Google Drive，永久免重下", "1. Click 'Download Weights': Persist Once in Google Drive"),
            tr(
                "内置 8 线程高速并发下载器。若账号已授权云盘，模型权重与 ComfyUI 节点会自动持久化在 Google Drive，下次唤醒新实例秒级复用。",
                "Built-in 8-thread concurrent downloader. With Google Drive authorized, model weights & ComfyUI nodes persist across sessions for instant reuse.",
            ),
        )
        c2 = self._make_card(
            tr("2. 再点「加载到显存」：96GB 显存 + 176GB 内存热备加速", "2. Click 'Load to VRAM': 96GB VRAM + 176GB RAM Hot Cache"),
            tr(
                "G4 实例支持多模型同时驻留显存（如 Qwen3.8 对话网关 + 生图/视频模型共驻）；MiniMax-H3 自动启用 176GB DDR5 双主干热备，连抽无需重读磁盘。",
                "G4 runtimes support multi-model VRAM co-residency (e.g. Qwen3.8 API gateway + image/video models), with 176GB DDR5 RAM hot-caching for MiniMax-H3.",
            ),
        )
        c3 = self._make_card(
            tr("3. 右侧实时日志与左侧折线图监控", "3. Live Telemetry Splines & Real-Time Run Logs"),
            tr(
                "左侧实时绘制 GPU 显存 / 系统内存 / 磁盘空间平滑折线走势（支持同屏/分项切换与悬停查看），右侧终端实时回显云端进度流。",
                "Left sidebar plots smooth GPU VRAM / System RAM / Disk curves (combined or split view with hover tooltips) while the right terminal streams live cloud logs.",
            ),
        )
        return self._wrap_scroll([c1, c2, c3])

    def _build_step_3(self) -> QWidget:
        items = [
            (
                tr("MiniMax-H3 · 4～15 秒电影级原生有声视频", "MiniMax-H3 · 4–15s Cinematic Native Audio-Video"),
                tr(
                    "同步生成 24 FPS 高清动态画面与 32 kHz 立体声环境音、对白及配乐，支持文生音视频与首尾帧过渡控镜。",
                    "Generates 24 FPS HD video synced with 32 kHz stereo ambient SFX, dialogue & music, supporting Text-to-Video+Audio and First/Last-Frame transitions.",
                ),
                tr("切换至 MiniMax-H3 视频工作台", "Switch to MiniMax-H3 Video Studio"),
                "minimax_h3",
            ),
            (
                tr("ComfyUI 节点工作台 · 预置 4 套零基础中文傻瓜工作流", "ComfyUI Node Studio · 4 Guided Ready-to-Run Workflow Packs"),
                tr(
                    "内置万相 Wan2.2、MiniMax-H3 Turbo、LTX-2.3、混元 Hunyuan1.5 四套中文工作流包，一键配齐模型并在浏览器全屏创作。",
                    "Built-in Wan2.2, MiniMax-H3 Turbo, LTX-2.3 & HunyuanVideo 1.5 workflow packs — install weights in 1 click and create in fullscreen browser canvas.",
                ),
                tr("切换至 ComfyUI 节点工作台", "Switch to ComfyUI Node Studio"),
                "comfyui_studio",
            ),
            (
                tr(
                    "Qwen3.8-27B (GGUF 100 tok/s) · 视觉对话与 Claude/OpenAI 网关",
                    "Qwen3.8-27B (GGUF 100 tok/s) · Vision Chat & Claude/OpenAI Gateway",
                ),
                tr(
                    "支持最高 256K 上下文、深度思考链与看图反推提示词，同时提供 OpenAI (/v1) 与 Anthropic (/v1/messages) 双协议公网接口。",
                    "Up to 256K context, deep chain-of-thought & vision prompt analysis, plus dual OpenAI (/v1) & Anthropic (/v1/messages) public API endpoints.",
                ),
                tr("切换至 Qwen3.8-GGUF 极速对话与网关", "Switch to Qwen3.8-GGUF Chat & Gateway"),
                "qwen38_27b_gguf",
            ),
            (
                tr(
                    "Qwen-Image-2.1 / Z-Image-Turbo / MiniMax-H3-Image · 2K 海报与 4K 直出修图",
                    "Qwen-Image-2.1 / Z-Image-Turbo / MiniMax-H3-Image · 2K Posters & Native 4K",
                ),
                tr(
                    "支持精准中英文海报排版直出、双图自然语言融合修图、8 步极速写实摄影与 MiniMax-H3-Image 6 步 4K 直出。",
                    "Accurate bilingual poster typography, dual-image fusion editing, 8-step turbo photorealism & MiniMax-H3-Image native 4K in 6 steps.",
                ),
                tr("切换至 Qwen-Image-2.1 图像工作台", "Switch to Qwen-Image-2.1 Image Studio"),
                "qwen_image_21",
            ),
        ]
        cards: List[QWidget] = []
        for title, desc, btn_txt, mid in items:
            row = QWidget()
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 2, 0, 0)
            b = set_btn_role(QPushButton(btn_txt), "primary")
            b.clicked.connect(lambda _c=False, m=mid: self._jump_to_model(m))
            rl.addWidget(b)
            rl.addStretch(1)
            cards.append(self._make_card(title, desc, row))
        return self._wrap_scroll(cards)

    def _build_step_4(self) -> QWidget:
        save_dir = get_local_save_dir()
        row1 = QWidget()
        r1 = QHBoxLayout(row1)
        r1.setContentsMargins(0, 2, 0, 0)
        open_dir_btn = QPushButton(tr("打开本地作品输出目录", "Open Local Output Folder"))
        open_dir_btn.clicked.connect(lambda: open_path_in_os(save_dir))
        r1.addWidget(open_dir_btn)
        r1.addStretch(1)
        c1 = self._make_card(
            tr("1. 生成作品自动回传本机 + 云盘双保险", "1. Auto-Download to Local PC + Cloud Backup"),
            tr(
                f"所有生成的 MP4 有声视频与 PNG 高清海报都会第一时间自动下载至本机 {save_dir}，即使云端关机也永不丢失。",
                f"All generated MP4 audio-videos and PNG HD images automatically download to {save_dir} on your computer, safe even after cloud shutdown.",
            ),
            row1,
        )
        c2 = self._make_card(
            tr(
                "2. 开启 30 分钟自动休眠 + 用完点「释放全部实例」立省 CU 额度",
                "2. 30-Min Idle Auto-Sleep + 'Release All Runtimes' to Save CU",
            ),
            tr(
                "内置闲置自动释放看门狗（默认 30 分钟无操作自动销毁实例）。当天创作结束时，点击左下角红色「释放全部实例」即可立即停止计费。",
                "Built-in idle watchdog (auto-terminates runtime after 30 min idle by default). Click the red 'Release All Runtimes' button when done to stop CU billing immediately.",
            ),
        )
        c3 = self._make_card(
            tr("3. 隐私打码开关与免费 Cloudflare 加密公网隧道", "3. Privacy Masking Toggle & Free Encrypted Cloudflare Tunnel"),
            tr(
                "录屏或截图分享前，可点击左侧服务地址旁的「打码」按钮一键隐藏 *.gradio.live 与 *.trycloudflare.com 域名及邮箱，防止他人蹭用算力。",
                "Before screen-recording or sharing screenshots, click 'Mask' next to the server URL to hide *.gradio.live / *.trycloudflare.com domains and your email.",
            ),
        )
        return self._wrap_scroll([c1, c2, c3])

    def _refresh_live_health(self) -> None:
        self.acc_dot.set_color("#10B981" if self.vm.cli_logged_in else "#F59E0B")
        acc_txt = (
            tr(f"Google 账号：{self.vm.display_account_label}", f"Google Account: {self.vm.display_account_label}")
            if self.vm.cli_logged_in
            else tr("Google 账号：待绑定", "Google Account: Not bound")
        )
        self.acc_lbl.setToolTip(acc_txt)
        self.acc_lbl.setText(QFontMetrics(self.acc_lbl.font()).elidedText(acc_txt, Qt.TextElideMode.ElideRight, 162))

        self.gpu_dot.set_color("#10B981" if self.vm.is_connected else "#F59E0B")
        gpu_txt = (
            tr(f"云端算力：{self.vm.gpu_name}", f"Cloud GPU: {self.vm.gpu_name}")
            if self.vm.is_connected
            else tr("云端算力：尚未唤醒连接", "Cloud GPU: Not connected")
        )
        self.gpu_lbl.setToolTip(gpu_txt)
        self.gpu_lbl.setText(QFontMetrics(self.gpu_lbl.font()).elidedText(gpu_txt, Qt.TextElideMode.ElideRight, 162))

        self.bind_now_btn.setVisible(not self.vm.cli_logged_in)
        self.bound_ok_lbl.setVisible(self.vm.cli_logged_in)
        self.wake_now_btn.setEnabled(self.vm.cli_logged_in and not self.vm.is_connected and not self.vm.is_waking_colab)

    def set_step(self, idx: int) -> None:
        steps = get_onboarding_steps()
        self._step = max(0, min(len(steps) - 1, idx))
        self.stack.setCurrentIndex(self._step)
        st_title, st_sub, st_tip = steps[self._step]
        self.step_badge.setText(f"STEP 0{self._step + 1} / 04")
        self.step_title_lbl.setText(st_title)
        self.step_sub_lbl.setText(st_sub)
        self.tip_lbl.setText(st_tip)
        self.prev_btn.setEnabled(self._step > 0)
        self.next_btn.setText(tr("开始创作", "Start Creating") if self._step == 3 else tr("下一步", "Next"))

        pal = DARK_PALETTE if self.vm.dark_mode else LIGHT_PALETTE
        for i, btn in enumerate(self._nav_buttons):
            if i == self._step:
                btn.setStyleSheet(
                    f"QPushButton {{ text-align: left; padding-left: 10px; font-weight: 700; "
                    f"background-color: {pal.selected_card_bg}; border: 1px solid {pal.selected_card_border}; border-radius: 7px; }}"
                )
            else:
                btn.setStyleSheet(
                    "QPushButton { text-align: left; padding-left: 10px; background: transparent; border: 1px solid transparent; }"
                    f"QPushButton:hover {{ background-color: {pal.hover_fill}; border-radius: 7px; }}"
                )

    def _on_next_clicked(self) -> None:
        if self._step < 3:
            self.set_step(self._step + 1)
        else:
            self._close_and_mark_seen()

    def _action_bind_account(self) -> None:
        self._close_and_mark_seen()
        self.vm.start_google_oauth_login()

    def _action_wake_g4(self) -> None:
        self.vm.set_wake_gpu_choice("G4")
        self._close_and_mark_seen()
        self.vm.wake_colab_headless()

    def _jump_to_model(self, model_id: str) -> None:
        self.vm.select_model(model_id)
        self._close_and_mark_seen()

    def _close_and_mark_seen(self) -> None:
        self.vm.mark_onboarding_seen()
        self.accept()

    def closeEvent(self, event) -> None:
        self._disconnect_vm_signals()
        self.vm.mark_onboarding_seen()
        super().closeEvent(event)
