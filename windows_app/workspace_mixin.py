"""
Main 3-Column Studio Window (1480x900) for the EasyColab Windows Client.
Implements 1:1 feature & layout parity with macOS EasyColabStudio.swift:
  - Left Sidebar (356px): Colab Instance + Telemetry Spline Charts, CU & Idle Sleep,
    Open Model Center (6 models + co-residency + weight shard manager), Adaptive Params.
  - Center Studio Workspace: Mode Switcher + MiniMax-H3 Video/Audio Studio, ComfyUI
    4-Pack Node Studio, Qwen3.8 Chat/VLM/Dual-Protocol API Gateway, Qwen-Image & Z-Image.
  - Right Collapsible Run Log Panel (352px): Live task progress + color-coded dark terminal.
"""
from __future__ import annotations

import html
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QAction, QFontMetrics, QGuiApplication, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QStackedWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
    QMainWindow,
)

from windows_app.models import (
    COMFY_WEIGHT_SUBFOLDERS,
    GPU_CHOICES,
    IMAGE_RESOLUTIONS,
    MODEL_SPEC_MAP,
    OPEN_MODEL_CATALOG,
    PRESET_TEMPLATES,
    VIDEO_DURATION_PRESETS,
    VIDEO_RESOLUTIONS,
    ComfyOutputMediaItem,
    ComfyPresetPackItem,
    ModelModality,
    OpenModelSpec,
    format_duration,
    format_uptime_hms,
    get_idle_timeout_choices,
    get_lang,
    get_local_save_dir,
    is_en,
    open_path_in_os,
    snap_video_frames,
    tr,
)
from windows_app.onboarding_dialog import ColabGuideDialog
from windows_app.theme import (
    DARK_PALETTE,
    LIGHT_PALETTE,
    StudioPalette,
    build_app_icon,
    build_stylesheet,
    draw_easycolab_icon_pixmap,
    icon_glyph,
    metric_threshold_color,
)
from windows_app.viewmodel import EasyColabViewModel
from windows_app.widgets import (
    AutoHeightStackedWidget,
    CollapsibleBox,
    CombinedTelemetryChartWidget,
    FrameDropWell,
    MediaPreviewWidget,
    ModeRadioCard,
    PillBadge,
    SidebarCard,
    SingleMetricChartWidget,
    StatusDot,
    WorkspaceCard,
    set_btn_role,
)




class WorkspaceMixin:
    # ═══════════════════════════════════════════════════════════════════════════
    # 2. CENTER STUDIO WORKSPACE (Top Bar + Mode Switcher + 4 Studios)
    # ═══════════════════════════════════════════════════════════════════════════

    def _build_center_workspace(self) -> QWidget:
        container = QWidget()
        container.setObjectName("CenterWorkspaceContainer")
        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)

        # Top 42px Workspace Bar
        top_bar = QFrame()
        top_bar.setObjectName("WorkspaceTopBar")
        top_bar.setFixedHeight(42)
        tb_lay = QHBoxLayout(top_bar)
        tb_lay.setContentsMargins(16, 0, 14, 0)
        tb_lay.setSpacing(8)

        self.ws_top_dot = StatusDot("#64748B", size=8)
        tb_lay.addWidget(self.ws_top_dot)
        self.ws_top_summary = QLabel(tr("开源多模型云端工作台", "Open Multi-Model Cloud AI Studio"))
        self.ws_top_summary.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.ws_top_summary.setStyleSheet("font-size: 12px; font-weight: 600;")
        tb_lay.addWidget(self.ws_top_summary, 1)

        self.preset_btn = QPushButton(tr("示例模板", "Presets"))
        self.preset_menu = QMenu(self)
        self.preset_btn.setMenu(self.preset_menu)
        tb_lay.addWidget(self.preset_btn)

        open_out_btn = QPushButton(tr("本地输出目录", "Output Folder"))
        open_out_btn.clicked.connect(lambda: open_path_in_os(get_local_save_dir()))
        tb_lay.addWidget(open_out_btn)

        guide_top_btn = QPushButton(tr("使用指南", "User Guide"))
        guide_top_btn.clicked.connect(lambda: self.open_onboarding_guide(0))
        tb_lay.addWidget(guide_top_btn)

        self.toggle_log_btn = set_btn_role(QPushButton(tr("日志栏", "Logs")), "ghost")
        self.toggle_log_btn.setToolTip(tr("折叠 / 展开右侧实时运行日志面板", "Collapse / expand right live run log panel"))
        self.toggle_log_btn.clicked.connect(self._toggle_right_log_panel)
        tb_lay.addWidget(self.toggle_log_btn)
        vbox.addWidget(top_bar)

        # Scrollable Studio Canvas
        self.ws_scroll = QScrollArea()
        self.ws_scroll.setWidgetResizable(True)
        self.ws_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        canvas = QWidget()
        self.ws_inner_vbox = QVBoxLayout(canvas)
        self.ws_inner_vbox.setContentsMargins(20, 16, 20, 22)
        self.ws_inner_vbox.setSpacing(14)

        # Universal Top Mode Switcher Card
        self.ws_inner_vbox.addWidget(self._build_mode_switcher_card())

        # Modality Studio Stack:
        # 0 = MiniMax-H3 Video/Audio, 1 = ComfyUI Studio, 2 = Qwen LLM/VLM/API, 3 = Image Studio
        self.studio_stack = AutoHeightStackedWidget()
        self.studio_stack.addWidget(self._build_video_audio_studio())
        self.studio_stack.addWidget(self._build_comfyui_studio())
        self.studio_stack.addWidget(self._build_qwen_llm_studio())
        self.studio_stack.addWidget(self._build_image_studio())
        self.ws_inner_vbox.addWidget(self.studio_stack)

        # Shared Media Preview + History Bottom Split (shown for Video, Image & ComfyUI)
        self.shared_media_split = self._build_shared_media_bottom_split()
        self.ws_inner_vbox.addWidget(self.shared_media_split)
        self.ws_inner_vbox.addStretch(1)

        self.ws_scroll.setWidget(canvas)
        vbox.addWidget(self.ws_scroll, 1)
        return container

    def _build_mode_switcher_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("WorkspaceCard")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(10)

        top = QHBoxLayout()
        top.setSpacing(8)
        self.ms_title_lbl = QLabel()
        self.ms_title_lbl.setStyleSheet("font-size: 16px; font-weight: 800;")
        top.addWidget(self.ms_title_lbl)

        self.ms_repo_pill = PillBadge("", fg="#64748B", bg="rgba(148,163,184,0.16)", mono=True)
        top.addWidget(self.ms_repo_pill)
        top.addStretch(1)

        self.ms_coresident_pill = PillBadge("", fg="#2563EB", bg="rgba(59,130,246,0.14)")
        self.ms_coresident_pill.setVisible(False)
        top.addWidget(self.ms_coresident_pill)

        self.ms_vram_pill = PillBadge(tr("待加载至显存", "Not Loaded in VRAM"), fg="#D97706", bg="rgba(245,158,11,0.14)")
        top.addWidget(self.ms_vram_pill)
        lay.addLayout(top)

        self.ms_summary_lbl = QLabel()
        self.ms_summary_lbl.setWordWrap(True)
        self.ms_summary_lbl.setStyleSheet("font-size: 12px; color: #64748B;")
        lay.addWidget(self.ms_summary_lbl)

        self.mode_buttons_row = QHBoxLayout()
        self.mode_buttons_row.setSpacing(10)
        lay.addLayout(self.mode_buttons_row)
        return card

    # ─── Studio A: MiniMax-H3 Video + Audio Studio ───────────────────────────

    def _build_video_audio_studio(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(14)

        # Reference First/Last Frame Drop Wells (fl2va only)
        self.video_frames_card = WorkspaceCard(
            tr("首尾关键帧参考图", "Start & End Keyframe References"),
            tr(
                "上传起始首帧或结束尾帧（至少 1 张），精准控制画面构图与镜头过渡",
                "Upload a start frame and/or end frame (at least 1) for precise composition & camera transition",
            ),
        )
        wells_row = QHBoxLayout()
        wells_row.setSpacing(12)
        self.video_first_well = FrameDropWell(
            tr("起始首帧 (Index 0)", "Start Frame (Index 0)"),
            tr("拖拽或点击选择首帧图像", "Drop or click to select start frame"),
        )
        self.video_last_well = FrameDropWell(
            tr("结束尾帧 (可选 · Index -1)", "End Frame (Optional · Index -1)"),
            tr("拖拽或点击选择尾帧图像", "Drop or click to select end frame"),
        )
        wells_row.addWidget(self.video_first_well, 1)
        wells_row.addWidget(self.video_last_well, 1)
        self.video_frames_card.body.addLayout(wells_row)
        lay.addWidget(self.video_frames_card)

        # Multimodal Prompt Composer
        p_card = WorkspaceCard(
            tr("镜头与多模态提示词", "Camera & Multimodal Audio-Video Prompt"),
            tr(
                "描述画面主体、镜头运动、光影风格，并可同步指定环境音效/台词对白与背景配乐",
                "Describe visual subjects, camera motion, and lighting, plus synced soundscape/dialogue & background score",
            ),
        )
        p_card.body.addWidget(
            QLabel(tr("视觉画面与运镜描述 (Visual & Camera Prompt)", "Visual & Camera Motion Prompt"))
        )
        self.vid_visual_edit = QPlainTextEdit(self.vm.visual_prompt)
        self.vid_visual_edit.setPlaceholderText(
            tr("输入主体、构图、运镜与光影风格描述...", "Describe subject, framing, camera movement, and lighting...")
        )
        self.vid_visual_edit.setFixedHeight(92)
        self.vid_visual_edit.textChanged.connect(self._on_vid_visual_edited)
        p_card.body.addWidget(self.vid_visual_edit)

        aud_row = QHBoxLayout()
        aud_row.setSpacing(12)

        sc_col = QVBoxLayout()
        sc_col.setSpacing(4)
        sc_col.addWidget(QLabel(tr("环境音效与台词对白（可选）", "Soundscape & Dialogue (Optional)")))
        self.vid_sound_edit = QPlainTextEdit(self.vm.soundscape_prompt)
        self.vid_sound_edit.setPlaceholderText(
            tr(
                "如：列车驶过铁轨撞击声、风吹树叶沙沙声、人物轻声感叹...",
                "e.g. Rhythmic train clatter over steel tracks, rustling leaves, soft spoken dialogue...",
            )
        )
        self.vid_sound_edit.setFixedHeight(64)
        self.vid_sound_edit.textChanged.connect(
            lambda: setattr(self.vm, "soundscape_prompt", self.vid_sound_edit.toPlainText())
        )
        sc_col.addWidget(self.vid_sound_edit)
        aud_row.addLayout(sc_col, 1)

        mu_col = QVBoxLayout()
        mu_col.setSpacing(4)
        mu_col.addWidget(QLabel(tr("背景音乐风格（可选）", "Background Music Style (Optional)")))
        self.vid_music_edit = QPlainTextEdit(self.vm.music_prompt)
        self.vid_music_edit.setPlaceholderText(
            tr(
                "如：温柔怀旧的独奏钢琴与温暖木吉他弦乐...",
                "e.g. Gentle nostalgic solo piano with warm acoustic guitar and ambient strings...",
            )
        )
        self.vid_music_edit.setFixedHeight(64)
        self.vid_music_edit.textChanged.connect(
            lambda: setattr(self.vm, "music_prompt", self.vid_music_edit.toPlainText())
        )
        mu_col.addWidget(self.vid_music_edit)
        aud_row.addLayout(mu_col, 1)

        p_card.body.addLayout(aud_row)
        p_card.body.addLayout(self._build_generate_action_bar("vid"))
        lay.addWidget(p_card)
        return page

    # ─── Studio B: ComfyUI 4-Card Node Studio ────────────────────────────────

    def _build_comfyui_studio(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(14)

        # Card 1: Fullscreen Node Canvas
        self.cfy_status_badge = PillBadge(tr("未启动", "Stopped"), fg="#64748B", bg="rgba(148,163,184,0.16)")
        c1 = WorkspaceCard(
            tr("云端 ComfyUI 全屏节点画布", "Cloud ComfyUI Fullscreen Node Canvas"),
            tr(
                "一键部署 ComfyUI + Manager 并自动开通 Cloudflare HTTPS 加密隧道，复用客户端保活与自动休眠",
                "1-click deploy ComfyUI + Manager over an encrypted Cloudflare HTTPS tunnel with desktop keepalive & auto-sleep",
            ),
            trailing=self.cfy_status_badge,
        )
        self.cfy_launch_btn = set_btn_role(
            QPushButton(
                tr(
                    "一键拉起云端 ComfyUI 并在浏览器打开全屏画布",
                    "1-Click Launch Cloud ComfyUI & Open Fullscreen Canvas in Browser",
                )
            ),
            "primary",
        )
        self.cfy_launch_btn.setFixedHeight(38)
        self.cfy_launch_btn.clicked.connect(lambda: self.vm.start_comfyui(force_restart=False, auto_open_browser=True))
        c1.body.addWidget(self.cfy_launch_btn)

        self.cfy_running_bar = QWidget()
        rb_lay = QHBoxLayout(self.cfy_running_bar)
        rb_lay.setContentsMargins(0, 0, 0, 0)
        rb_lay.setSpacing(8)
        open_cfy_btn = set_btn_role(
            QPushButton(tr("在浏览器打开全屏节点画布", "Open Fullscreen Canvas in Browser")), "success"
        )
        open_cfy_btn.setFixedHeight(34)
        open_cfy_btn.clicked.connect(self._open_comfy_browser)
        copy_cfy_btn = QPushButton(tr("复制画布链接", "Copy Canvas URL"))
        copy_cfy_btn.clicked.connect(self._copy_comfy_url)
        restart_cfy_btn = QPushButton(tr("重启生效", "Restart ComfyUI"))
        restart_cfy_btn.clicked.connect(lambda: self.vm.start_comfyui(force_restart=True, auto_open_browser=False))
        rb_lay.addWidget(open_cfy_btn, 1)
        rb_lay.addWidget(copy_cfy_btn)
        rb_lay.addWidget(restart_cfy_btn)
        c1.body.addWidget(self.cfy_running_bar)

        self.cfy_main_prog = QProgressBar()
        self.cfy_main_prog.setRange(0, 100)
        self.cfy_main_prog.setVisible(False)
        c1.body.addWidget(self.cfy_main_prog)

        self.cfy_tunnel_lbl = QLabel(tr("云端 ComfyUI 尚未启动", "Cloud ComfyUI not started"))
        self.cfy_tunnel_lbl.setWordWrap(True)
        self.cfy_tunnel_lbl.setStyleSheet("font-family: Consolas, monospace; font-size: 11.5px; color: #94A3B8;")
        c1.body.addWidget(self.cfy_tunnel_lbl)
        lay.addWidget(c1)

        # Card 2: 4 Preset Workflow Packs
        self.cfy_packs_badge = PillBadge(
            tr("已就绪 0 / 4 套", "0 / 4 Packs Ready"), fg="#2563EB", bg="rgba(59,130,246,0.14)"
        )
        c2 = WorkspaceCard(
            tr(
                "预置图生视频 / 首尾帧运镜工作流包（一键配齐模型与中文画布）",
                "Preset I2V & First/Last-Frame Workflow Packs (1-Click Models + Guided Templates)",
            ),
            tr(
                "零基础免找权重、免配节点：一键高速拉取全套模型并自动生成中文指引工作流模板",
                "Zero manual setup: 1-click high-speed download of official weights + ready-to-run guided workflow templates",
            ),
            trailing=self.cfy_packs_badge,
        )
        steps_row = QHBoxLayout()
        steps_row.setSpacing(8)
        for st_txt in (
            tr("1. 点击下方「一键配齐模型与工作流」", "1. Click '1-Click Install Models & Workflows' below"),
            tr("2. 在画布最左侧点「工作流」选中文模板", "2. Open 'Workflows' sidebar in ComfyUI & pick a template"),
            tr("3. 上传 1~2 张图片点右上角「运行」出片", "3. Upload 1-2 images & click 'Run' to generate"),
        ):
            chip = QFrame()
            chip.setObjectName("SubtlePanel")
            chip.setMinimumHeight(42)
            cl = QHBoxLayout(chip)
            cl.setContentsMargins(10, 6, 10, 6)
            lbl = QLabel(st_txt)
            lbl.setWordWrap(True)
            lbl.setStyleSheet("font-size: 11px; color: #64748B;")
            cl.addWidget(lbl)
            steps_row.addWidget(chip, 1)
        c2.body.addLayout(steps_row)

        self.cfy_packs_widget = QWidget()
        self.cfy_packs_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.cfy_packs_container = QVBoxLayout(self.cfy_packs_widget)
        self.cfy_packs_container.setContentsMargins(0, 0, 0, 0)
        self.cfy_packs_container.setSpacing(8)
        for init_pack in self.vm.comfy_preset_packs:
            self.cfy_packs_container.addWidget(self._build_comfy_pack_row(init_pack))
        c2.body.addWidget(self.cfy_packs_widget)
        lay.addWidget(c2)

        # Card 3: Google Drive Symlink & Persistence
        sync_drv_btn = QPushButton(tr("立即同步至云盘", "Sync to Drive Now"))
        sync_drv_btn.clicked.connect(self.vm.sync_comfy_drive)
        c3 = WorkspaceCard(
            tr("Google Drive 自动软链与跨实例持久化", "Google Drive Auto-Symlink & Cross-Runtime Persistence"),
            tr(
                "云端路径: /content/drive/MyDrive/EasyColab_ComfyUI（销毁换卡后自动挂载复用）",
                "Cloud path: /content/drive/MyDrive/EasyColab_ComfyUI (auto-reused across fresh GPU runtimes)",
            ),
            trailing=sync_drv_btn,
        )
        tiles_row = QHBoxLayout()
        tiles_row.setSpacing(10)
        self.cfy_tile_models = self._make_metric_tile(
            tr("models/* 模型权重库", "models/* Weight Library"), tr("0 个文件", "0 files")
        )
        self.cfy_tile_nodes = self._make_metric_tile(
            tr("custom_nodes 自定义节点", "custom_nodes Extensions"), tr("0 个插件", "0 nodes")
        )
        self.cfy_tile_wfs = self._make_metric_tile(
            tr("workflows 工作流存档", "workflows Saved Templates"), tr("0 套模板", "0 templates")
        )
        tiles_row.addWidget(self.cfy_tile_models[0], 1)
        tiles_row.addWidget(self.cfy_tile_nodes[0], 1)
        tiles_row.addWidget(self.cfy_tile_wfs[0], 1)
        c3.body.addLayout(tiles_row)
        lay.addWidget(c3)

        # Card 4: 8-Thread Custom Weight Downloader
        c4 = WorkspaceCard(
            tr("8 线程极速下载权重至 ComfyUI 云盘目录", "8-Thread High-Speed Weight Downloader to ComfyUI Drive"),
            tr(
                "支持粘贴 Hugging Face / Civitai 直链 URL，或填写 HF Repo ID + 文件子路径直接拉取至对应子目录",
                "Paste a direct Hugging Face / Civitai URL, or enter an HF Repo ID + filename to pull directly into ComfyUI",
            ),
        )
        dl_row1 = QHBoxLayout()
        dl_row1.setSpacing(8)
        dl_row1.addWidget(QLabel(tr("目标目录", "Target Folder")))
        self.cfy_subfolder_combo = QComboBox()
        for sf in COMFY_WEIGHT_SUBFOLDERS:
            self.cfy_subfolder_combo.addItem(f"models/{sf}", sf)
        dl_row1.addWidget(self.cfy_subfolder_combo)
        self.cfy_src_input = QLineEdit()
        self.cfy_src_input.setPlaceholderText(
            tr(
                "模型直链 https://... 或 HF 仓库如 Kijai/WanVideo_comfy",
                "Direct URL https://... or HF Repo ID e.g. Kijai/WanVideo_comfy",
            )
        )
        dl_row1.addWidget(self.cfy_src_input, 1)
        c4.body.addLayout(dl_row1)

        dl_row2 = QHBoxLayout()
        dl_row2.setSpacing(8)
        self.cfy_fname_input = QLineEdit()
        self.cfy_fname_input.setPlaceholderText(
            tr(
                "可选：仓库内文件子路径或保存文件名 (如 Wan2_2-I2V-14B.safetensors)",
                "Optional: subpath in repo or target filename (e.g. Wan2_2-I2V-14B.safetensors)",
            )
        )
        dl_row2.addWidget(self.cfy_fname_input, 1)
        self.cfy_dl_weight_btn = set_btn_role(
            QPushButton(tr("8 线程下载至云盘", "8-Thread Download")), "primary"
        )
        self.cfy_dl_weight_btn.clicked.connect(self._on_comfy_custom_dl)
        dl_row2.addWidget(self.cfy_dl_weight_btn)
        c4.body.addLayout(dl_row2)
        lay.addWidget(c4)
        return page

    def _make_metric_tile(self, label: str, val: str) -> tuple[QFrame, QLabel]:
        f = QFrame()
        f.setObjectName("SubtlePanel")
        l = QVBoxLayout(f)
        l.setContentsMargins(12, 8, 12, 8)
        l.setSpacing(2)
        t = QLabel(label)
        t.setStyleSheet("font-size: 11px; color: #94A3B8;")
        v = QLabel(val)
        v.setStyleSheet("font-size: 14px; font-weight: 700; font-family: Consolas, monospace;")
        l.addWidget(t)
        l.addWidget(v)
        return f, v

    # ─── Studio C: Qwen3.8 Chat, VLM & Dual-Protocol API Gateway ─────────────

    def _build_qwen_llm_studio(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(14)

        self.qwen_mode_stack = AutoHeightStackedWidget()

        # Subpage 0: Chat & VLM Interactive Studio
        chat_page = QWidget()
        cp_lay = QVBoxLayout(chat_page)
        cp_lay.setContentsMargins(0, 0, 0, 0)
        cp_lay.setSpacing(14)

        # VLM Image Drop Wells (shown only when task_mode_id == "vlm")
        self.vlm_images_card = WorkspaceCard(
            tr("待分析视觉图像", "Vision Input Images"),
            tr(
                "拖入 1~2 张图片进行构图光影解析、OCR 识别或反推专业生图/生视频 Prompt",
                "Drop 1-2 images for composition analysis, OCR extraction, or reverse-engineering T2I/T2V prompts",
            ),
        )
        vlm_row = QHBoxLayout()
        vlm_row.setSpacing(12)
        self.vlm_img1_well = FrameDropWell(
            tr("输入图像 1", "Input Image 1"),
            tr("拖拽或点击选择图片", "Drop or click to select image"),
        )
        self.vlm_img2_well = FrameDropWell(
            tr("对比图像 2 (可选)", "Comparison Image 2 (Optional)"),
            tr("拖拽或点击选择第二张图片", "Drop or click to select second image"),
        )
        vlm_row.addWidget(self.vlm_img1_well, 1)
        vlm_row.addWidget(self.vlm_img2_well, 1)
        self.vlm_images_card.body.addLayout(vlm_row)
        cp_lay.addWidget(self.vlm_images_card)

        # Prompt Composer
        q_card = WorkspaceCard(
            tr("问题与指令输入", "Prompt & Instruction Input"),
            tr(
                "支持最高 256K 超长上下文、深度思考链推理、代码架构设计与分镜脚本创作 (Ctrl+Enter 发送)",
                "Supports up to 256K context, deep chain-of-thought reasoning, architecture design & storyboards (Ctrl+Enter)",
            ),
        )
        self.llm_prompt_edit = QPlainTextEdit()
        self.llm_prompt_edit.setPlaceholderText(
            tr("输入问题、代码需求或视觉分析指令...", "Enter your question, coding spec, or visual analysis prompt...")
        )
        self.llm_prompt_edit.setFixedHeight(86)
        self.llm_prompt_edit.textChanged.connect(self._on_llm_prompt_edited)
        q_card.body.addWidget(self.llm_prompt_edit)
        q_card.body.addLayout(self._build_generate_action_bar("llm"))
        cp_lay.addWidget(q_card)

        # Multi-turn Conversation Card
        conv_hdr_btns = QWidget()
        ch_lay = QHBoxLayout(conv_hdr_btns)
        ch_lay.setContentsMargins(0, 0, 0, 0)
        ch_lay.setSpacing(6)
        to_api_btn = QPushButton(tr("API 接入配置", "API Gateway Setup"))
        to_api_btn.clicked.connect(lambda: self.vm.set_task_mode("api"))
        clr_chat_btn = QPushButton(tr("清空对话", "Clear Chat"))
        clr_chat_btn.clicked.connect(self._clear_chat_history)
        ch_lay.addWidget(to_api_btn)
        ch_lay.addWidget(clr_chat_btn)

        conv_card = WorkspaceCard(
            tr("对话与深度推理记录", "Conversation & Deep Reasoning Transcript"),
            tr(
                "实时流式输出长思维链 (Thinking Process) 与最终回复",
                "Live streaming of chain-of-thought (Thinking Process) and final response",
            ),
            trailing=conv_hdr_btns,
        )
        self.chat_turns_container = QVBoxLayout()
        self.chat_turns_container.setSpacing(10)
        conv_card.body.addLayout(self.chat_turns_container)
        cp_lay.addWidget(conv_card)
        self.qwen_mode_stack.addWidget(chat_page)

        # Subpage 1: OpenAI + Anthropic Dual-Protocol API Gateway
        self.qwen_mode_stack.addWidget(self._build_api_gateway_page())

        lay.addWidget(self.qwen_mode_stack)
        return page

    def _build_api_gateway_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(14)

        self.api_req_count_lbl = QLabel(tr("累计 API 请求: 0 次", "Total API Requests: 0"))
        self.api_req_count_lbl.setStyleSheet(
            "font-size: 11.5px; font-weight: 600; color: #64748B; font-family: Consolas, monospace;"
        )
        auth_card = WorkspaceCard(
            tr("网关安全鉴权与运行状态", "API Gateway Authentication & Status"),
            tr(
                "公网隧道开启期间，建议保持密钥鉴权开启以保护你的 Colab 算力单元 (CU)",
                "Keep API Key authentication enabled while the public tunnel is live to protect your Colab Compute Units (CU)",
            ),
            trailing=self.api_req_count_lbl,
        )
        top_r = QHBoxLayout()
        self.api_auth_chk = QCheckBox(
            tr("启用 API Key 鉴权（同时校验 Bearer 与 x-api-key）", "Require API Key Auth (validates Bearer & x-api-key)")
        )
        self.api_auth_chk.setChecked(self.vm.api_key_enabled)
        self.api_auth_chk.setEnabled(False)
        top_r.addWidget(self.api_auth_chk)
        top_r.addStretch(1)
        self.api_coresident_hint = QLabel("")
        self.api_coresident_hint.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.api_coresident_hint.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.api_coresident_hint.setStyleSheet("font-size: 11.5px;")
        top_r.addWidget(self.api_coresident_hint, 1)
        auth_card.body.addLayout(top_r)

        self.api_key_row_w = QWidget()
        kr = QHBoxLayout(self.api_key_row_w)
        kr.setContentsMargins(0, 0, 0, 0)
        kr.setSpacing(8)
        kr.addWidget(QLabel(tr("访问密钥", "API Key")))
        self.api_key_input = QLineEdit(self.vm.api_access_key)
        self.api_key_input.setStyleSheet("font-family: Consolas, monospace;")
        self.api_key_input.returnPressed.connect(lambda: self._sync_api_key_clicked())
        kr.addWidget(self.api_key_input, 1)

        sync_k_btn = QPushButton(tr("同步到云端", "Sync to Cloud"))
        sync_k_btn.clicked.connect(self._sync_api_key_clicked)
        regen_k_btn = QPushButton(tr("重新生成", "Regenerate"))
        regen_k_btn.clicked.connect(self._regen_api_key_clicked)
        copy_k_btn = set_btn_role(QPushButton(tr("复制密钥", "Copy Key")), "primary")
        copy_k_btn.clicked.connect(
            lambda: self._copy_text(
                self.vm.api_access_key,
                tr("已复制 API Key 到剪贴板。", "Copied API Key to clipboard."),
            )
        )
        kr.addWidget(sync_k_btn)
        kr.addWidget(regen_k_btn)
        kr.addWidget(copy_k_btn)
        auth_card.body.addWidget(self.api_key_row_w)
        lay.addWidget(auth_card)

        # Side-by-side Protocol Cards
        proto_row = QHBoxLayout()
        proto_row.setSpacing(14)

        # Left: OpenAI Compatible Protocol
        oai_card = WorkspaceCard(
            tr("OpenAI 兼容协议", "OpenAI-Compatible Protocol"),
            tr(
                "兼容 OpenAI SDK、Cursor、Cherry Studio、Chatbox 等客户端",
                "Compatible with OpenAI SDK, Cursor, Cherry Studio, Chatbox & standard tools",
            ),
        )
        self.oai_base_lbl = self._add_endpoint_copy_row(
            oai_card.body, "Base URL", lambda: self._api_snippets()["oai_base"]
        )
        self.oai_chat_lbl = self._add_endpoint_copy_row(
            oai_card.body, tr("Chat 接口", "Chat URL"), lambda: self._api_snippets()["oai_chat"]
        )
        self.oai_model_lbl = self._add_endpoint_copy_row(
            oai_card.body, tr("模型名称", "Model ID"), lambda: self._api_snippets()["repo"]
        )
        oai_desc = QLabel(
            tr(
                "支持 stream 流式输出、reasoning_content 深度思考链、image_url 视觉输入与 Function Calling；加载生图模型时亦支持 /v1/images/generations。",
                "Supports SSE streaming, reasoning_content CoT, image_url vision inputs & Function Calling; also serves /v1/images/generations when an image model is loaded.",
            )
        )
        oai_desc.setWordWrap(True)
        oai_desc.setStyleSheet("font-size: 11px; color: #64748B;")
        oai_card.body.addWidget(oai_desc)
        self.oai_code_box = self._make_readonly_code_view()
        oai_card.body.addWidget(self.oai_code_box)
        oai_btns = QHBoxLayout()
        b_py = QPushButton(tr("复制 Python 代码", "Copy Python SDK"))
        b_py.clicked.connect(
            lambda: self._copy_text(
                self._api_snippets()["oai_py"],
                tr("已复制 OpenAI Python 调用代码。", "Copied OpenAI Python snippet."),
            )
        )
        b_ocurl = QPushButton(tr("复制 curl 命令", "Copy curl"))
        b_ocurl.clicked.connect(
            lambda: self._copy_text(
                self._api_snippets()["oai_curl"],
                tr("已复制 OpenAI curl 测试命令。", "Copied OpenAI curl command."),
            )
        )
        oai_btns.addWidget(b_py)
        oai_btns.addWidget(b_ocurl)
        oai_btns.addStretch(1)
        oai_card.body.addLayout(oai_btns)
        proto_row.addWidget(oai_card, 1)

        # Right: Anthropic Messages Protocol
        ant_card = WorkspaceCard(
            tr("Anthropic Messages 协议", "Anthropic Messages Protocol"),
            tr(
                "原生实现 /v1/messages，兼容 Anthropic SDK 与 Claude Code",
                "Native /v1/messages endpoint for Anthropic SDK & Claude Code CLI",
            ),
        )
        self.ant_base_lbl = self._add_endpoint_copy_row(
            ant_card.body, "Base URL", lambda: self._api_snippets()["ant_base"]
        )
        self.ant_msg_lbl = self._add_endpoint_copy_row(
            ant_card.body, "Messages", lambda: self._api_snippets()["ant_msg"]
        )
        self._add_endpoint_copy_row(
            ant_card.body,
            tr("鉴权请求头", "Auth Header"),
            lambda: tr("x-api-key 或 Authorization: Bearer", "x-api-key or Authorization: Bearer"),
        )
        ant_desc = QLabel(
            tr(
                "完整支持 Anthropic SSE 事件流（thinking_delta 思考块、text_delta 文本块、tool_use 工具块）及 /v1/messages/count_tokens 接口。",
                "Full Anthropic SSE streaming (thinking_delta, text_delta, tool_use blocks) plus /v1/messages/count_tokens.",
            )
        )
        ant_desc.setWordWrap(True)
        ant_desc.setStyleSheet("font-size: 11px; color: #64748B;")
        ant_card.body.addWidget(ant_desc)
        self.ant_code_box = self._make_readonly_code_view()
        ant_card.body.addWidget(self.ant_code_box)
        ant_btns = QHBoxLayout()
        b_ps = QPushButton(tr("复制 PowerShell 配置", "Copy PowerShell Env"))
        b_ps.clicked.connect(
            lambda: self._copy_text(
                self._api_snippets()["claude_ps"],
                tr("已复制 Windows PowerShell Claude Code 配置。", "Copied Windows PowerShell Claude Code env."),
            )
        )
        b_sh = QPushButton(tr("复制 Bash 配置", "Copy Bash Env"))
        b_sh.clicked.connect(
            lambda: self._copy_text(
                self._api_snippets()["claude_sh"],
                tr("已复制 Bash ANTHROPIC_BASE_URL 配置。", "Copied Bash ANTHROPIC_BASE_URL env."),
            )
        )
        b_acurl = QPushButton(tr("复制 Anthropic curl", "Copy Anthropic curl"))
        b_acurl.clicked.connect(
            lambda: self._copy_text(
                self._api_snippets()["ant_curl"],
                tr("已复制 Anthropic /v1/messages curl 命令。", "Copied Anthropic /v1/messages curl command."),
            )
        )
        ant_btns.addWidget(b_ps)
        ant_btns.addWidget(b_sh)
        ant_btns.addWidget(b_acurl)
        ant_btns.addStretch(1)
        ant_card.body.addLayout(ant_btns)
        proto_row.addWidget(ant_card, 1)

        lay.addLayout(proto_row)
        return page

    def _add_endpoint_copy_row(self, parent_layout: QVBoxLayout, label: str, val_getter) -> QLabel:
        row = QHBoxLayout()
        row.setSpacing(6)
        k = QLabel(label)
        k.setFixedWidth(74)
        k.setStyleSheet("font-size: 11px; color: #64748B;")
        row.addWidget(k)
        v = QLabel(val_getter())
        v.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        v.setStyleSheet("font-family: Consolas, monospace; font-size: 11px;")
        v.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        row.addWidget(v, 1)
        cp = QPushButton(tr("复制", "Copy"))
        cp.setFixedHeight(24)
        cp.clicked.connect(
            lambda: self._copy_text(
                val_getter(),
                tr(f"已复制 {label} 到剪贴板。", f"Copied {label} to clipboard."),
            )
        )
        row.addWidget(cp)
        parent_layout.addLayout(row)
        return v

    @staticmethod
    def _make_readonly_code_view() -> QPlainTextEdit:
        ed = QPlainTextEdit()
        ed.setObjectName("CodeSnippetBox")
        ed.setReadOnly(True)
        ed.setFixedHeight(168)
        return ed

    # ─── Studio D: Qwen-Image-2.1 & Z-Image-Turbo Studio ─────────────────────

    def _build_image_studio(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(14)

        self.img_refs_card = WorkspaceCard(
            tr("指令修图 / 风格重绘参考图", "Instruction Edit / Img2Img Reference Images"),
            tr(
                "上传原图后输入自然语言修改指令（Qwen-Image-2.1 支持双图主体融合）",
                "Upload source image(s) and enter natural-language edit instructions (Qwen-Image-2.1 supports dual-image fusion)",
            ),
        )
        r_row = QHBoxLayout()
        r_row.setSpacing(12)
        self.img_ref1_well = FrameDropWell(
            tr("主参考图 1 (必选)", "Primary Reference 1 (Required)"),
            tr("拖拽或点击上传主参考图", "Drop or click to upload primary image"),
        )
        self.img_ref2_well = FrameDropWell(
            tr("融合参考图 2 (可选)", "Fusion Reference 2 (Optional)"),
            tr("拖拽或点击上传第二张融合参考图", "Drop or click to upload second fusion image"),
        )
        r_row.addWidget(self.img_ref1_well, 1)
        r_row.addWidget(self.img_ref2_well, 1)
        self.img_refs_card.body.addLayout(r_row)
        lay.addWidget(self.img_refs_card)

        p_card = WorkspaceCard(
            tr("画面与海报排版提示词", "Image & Typography Generation Prompt"),
            tr(
                "支持复杂构图、高质感商业摄影及精准中英文海报文字直出",
                "Supports complex scene composition, commercial photography & accurate Chinese/English poster typography",
            ),
        )
        p_card.body.addWidget(QLabel(tr("正向提示词 (Prompt)", "Positive Prompt")))
        self.img_visual_edit = QPlainTextEdit(self.vm.visual_prompt)
        self.img_visual_edit.setPlaceholderText(
            tr(
                "描述画面主体、光影质感、镜头语言或需要排版的双引号文字...",
                "Describe subject, lighting, camera lens, or quoted poster text to render...",
            )
        )
        self.img_visual_edit.setFixedHeight(92)
        self.img_visual_edit.textChanged.connect(self._on_img_visual_edited)
        p_card.body.addWidget(self.img_visual_edit)

        p_card.body.addWidget(
            QLabel(
                tr(
                    "反向提示词 Negative Prompt（可选，排除低质或多余元素）",
                    "Negative Prompt (Optional — exclude artifacts or unwanted elements)",
                )
            )
        )
        self.img_neg_edit = QPlainTextEdit(self.vm.negative_prompt)
        self.img_neg_edit.setPlaceholderText(
            tr(
                "如：blurry, low quality, watermark, deformed hands...",
                "e.g. blurry, low quality, watermark, deformed hands...",
            )
        )
        self.img_neg_edit.setFixedHeight(48)
        self.img_neg_edit.textChanged.connect(
            lambda: setattr(self.vm, "negative_prompt", self.img_neg_edit.toPlainText())
        )
        p_card.body.addWidget(self.img_neg_edit)

        p_card.body.addLayout(self._build_generate_action_bar("img"))
        lay.addWidget(p_card)
        return page

    def _build_generate_action_bar(self, prefix: str) -> QVBoxLayout:
        box = QVBoxLayout()
        box.setSpacing(6)
        row = QHBoxLayout()
        row.setSpacing(10)

        gen_btn = set_btn_role(QPushButton(tr("开始生成", "Generate")), "primary")
        gen_btn.setFixedHeight(38)
        gen_btn.clicked.connect(self._trigger_generate)
        row.addWidget(gen_btn, 1)

        stop_btn = set_btn_role(QPushButton(tr("停止推理", "Stop")), "danger")
        stop_btn.setFixedHeight(38)
        stop_btn.setFixedWidth(96)
        stop_btn.clicked.connect(self.vm.cancel_current_generation)
        row.addWidget(stop_btn)
        box.addLayout(row)

        prog = QProgressBar()
        prog.setRange(0, 100)
        prog.setVisible(False)
        box.addWidget(prog)

        setattr(self, f"{prefix}_gen_btn", gen_btn)
        setattr(self, f"{prefix}_stop_btn", stop_btn)
        setattr(self, f"{prefix}_prog_bar", prog)
        return box

    def _build_shared_media_bottom_split(self) -> QWidget:
        wrap = QWidget()
        hbox = QHBoxLayout(wrap)
        hbox.setContentsMargins(0, 0, 0, 0)
        hbox.setSpacing(14)

        self.media_preview = MediaPreviewWidget()
        hbox.addWidget(self.media_preview, 1)

        # Right side stack: Page 0 = Local Media Gallery (254px), Page 1 = ComfyUI Cloud Outputs + Local (290px)
        self.right_gallery_stack = QStackedWidget()
        self.right_gallery_stack.setFixedWidth(268)

        # Page 0: Local History Gallery
        loc_card = WorkspaceCard(
            tr("本机成片库", "Local Media Library"),
            tr("自动保存至 Videos/EasyColab", "Auto-saved to Videos/EasyColab"),
        )
        loc_scroll = QScrollArea()
        loc_scroll.setWidgetResizable(True)
        loc_scroll.setMinimumHeight(250)
        loc_w = QWidget()
        self.local_gallery_lay = QVBoxLayout(loc_w)
        self.local_gallery_lay.setContentsMargins(0, 0, 4, 0)
        self.local_gallery_lay.setSpacing(6)
        loc_scroll.setWidget(loc_w)
        loc_card.body.addWidget(loc_scroll)
        self.right_gallery_stack.addWidget(loc_card)

        # Page 1: ComfyUI Cloud Outputs
        cfy_out_card = WorkspaceCard(
            tr("ComfyUI 云端输出成片", "ComfyUI Cloud Outputs"),
            tr("一键拉回本机播放与永久保存", "1-click pull to local library & preview"),
        )
        cfy_scroll = QScrollArea()
        cfy_scroll.setWidgetResizable(True)
        cfy_scroll.setMinimumHeight(250)
        cfy_w = QWidget()
        self.comfy_outputs_lay = QVBoxLayout(cfy_w)
        self.comfy_outputs_lay.setContentsMargins(0, 0, 4, 0)
        self.comfy_outputs_lay.setSpacing(6)
        cfy_scroll.setWidget(cfy_w)
        cfy_out_card.body.addWidget(cfy_scroll)
        self.right_gallery_stack.addWidget(cfy_out_card)

        hbox.addWidget(self.right_gallery_stack)
        return wrap


    def _show_custom_model_menu(self, btn: QPushButton, pos: object, model_id: str) -> None:
        menu = QMenu(self)
        act_del = QAction(tr("移除该自定义模型", "Remove Custom Model"), self)
        act_del.triggered.connect(lambda: self.vm.remove_custom_hf_model(model_id))
        menu.addAction(act_del)
        menu.exec(btn.mapToGlobal(pos))  # type: ignore[arg-type]

    def _open_add_custom_model_dialog(self) -> None:
        dlg = QDialog(self)
        dlg.setWindowTitle(tr("添加自定义 HuggingFace 模型仓库", "Add Custom HuggingFace Repository"))
        dlg.setMinimumWidth(640)
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(10)

        sub = QLabel(
            tr(
                "支持从下方实时拉取 HuggingFace 热门趋势模型一键填入，或输入任意 Repo ID。若为需登录/受限模型 (Gated Repo)，请填写 HF Token 并同意模型页协议。",
                "Pick from live HuggingFace trending models below or enter any Repo ID. For gated/private repos, enter your HF Token and accept the license on HuggingFace.",
            )
        )
        sub.setWordWrap(True)
        sub.setStyleSheet("font-size: 11.5px; color: #64748B;")
        lay.addWidget(sub)

        trend_hdr = QHBoxLayout()
        trend_hdr.addWidget(
            QLabel(
                tr(
                    "HuggingFace 实时热榜与搜索 (含参数量 & Colab 显存部署评估)",
                    "Live HuggingFace Trending & Search (with Params & Colab Fit)",
                )
            )
        )
        trend_hdr.addStretch(1)
        cat_combo = QComboBox()
        cat_combo.addItem(tr("综合热榜", "Trending All"), "all")
        cat_combo.addItem(tr("GGUF 量化", "GGUF"), "gguf")
        cat_combo.addItem(tr("对话 / 视觉", "LLM / VLM"), "llm")
        cat_combo.addItem(tr("生图 / 视频", "Image / Video"), "image_video")
        cat_combo.setFixedWidth(124)
        trend_hdr.addWidget(cat_combo)

        refresh_trend_btn = QPushButton(tr("刷新热榜", "Refresh"))
        trend_hdr.addWidget(refresh_trend_btn)
        lay.addLayout(trend_hdr)

        search_row = QHBoxLayout()
        search_edit = QLineEdit()
        search_edit.setPlaceholderText(
            tr(
                "搜索 HuggingFace 模型 (如 Qwen3 GGUF / DeepSeek 9B / Flux)，回车在线检索...",
                "Search HuggingFace models (e.g. Qwen3 GGUF / DeepSeek 9B), press Enter...",
            )
        )
        search_row.addWidget(search_edit, 1)
        search_btn = QPushButton(tr("在线搜索", "Search HF"))
        search_row.addWidget(search_btn)
        lay.addLayout(search_row)

        trend_scroll = QScrollArea()
        trend_scroll.setWidgetResizable(True)
        trend_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        trend_scroll.setFixedHeight(185)
        trend_container = QWidget()
        trend_grid = QGridLayout(trend_container)
        trend_grid.setContentsMargins(6, 6, 6, 6)
        trend_grid.setHorizontalSpacing(8)
        trend_grid.setVerticalSpacing(7)
        trend_grid.setColumnStretch(0, 1)
        trend_grid.setColumnStretch(1, 1)
        trend_scroll.setWidget(trend_container)
        lay.addWidget(trend_scroll)

        repo_hdr = QHBoxLayout()
        repo_hdr.addWidget(QLabel(tr("1. HuggingFace 仓库地址 (Repo ID 或 URL)", "1. HuggingFace Repo ID or URL")))
        repo_hdr.addStretch(1)
        inspect_repo_btn = set_btn_role(
            QPushButton(tr("查看该模型详情与分片体积", "Inspect Model Details & Shards")), "ghost"
        )
        repo_hdr.addWidget(inspect_repo_btn)
        lay.addLayout(repo_hdr)
        repo_edit = QLineEdit()
        repo_edit.setPlaceholderText(
            tr("从上方实时热榜点选，或输入任意 Owner/Repo", "Click a trending card above or enter any Owner/Repo")
        )
        lay.addWidget(repo_edit)

        lay.addWidget(
            QLabel(
                tr(
                    "2. 文件名 / 通配符过滤 (Include Pattern，可选)",
                    "2. Filename / Wildcard Filter (Include Pattern, Optional)",
                )
            )
        )
        pat_edit = QLineEdit()
        pat_edit.setPlaceholderText(
            tr(
                "留空默认智能选择；或填 *Q4_K_M*.gguf, *IQ2_XS*.gguf, *.safetensors",
                "Blank = auto-select; or *Q4_K_M*.gguf, *IQ2_XS*.gguf, *.safetensors",
            )
        )
        lay.addWidget(pat_edit)

        row3 = QHBoxLayout()
        col_name = QVBoxLayout()
        col_name.addWidget(QLabel(tr("3. 自定义显示名称 (可选)", "3. Display Name (Optional)")))
        name_edit = QLineEdit()
        name_edit.setPlaceholderText(tr("留空使用仓库名称", "Blank = repo short name"))
        col_name.addWidget(name_edit)
        row3.addLayout(col_name, 1)

        col_mod = QVBoxLayout()
        col_mod.addWidget(QLabel(tr("4. 任务模态", "4. Task Modality")))
        mod_combo = QComboBox()
        mod_combo.addItem(tr("自动识别 (推荐)", "Auto-detect"), "auto")
        mod_combo.addItem(tr("对话 / 视觉 / API (LLM/VLM)", "Chat / Vision / API"), "llm_vlm")
        mod_combo.addItem(tr("文生图 / 图像编辑 (Image)", "Image Generation"), "image")
        mod_combo.addItem(tr("音视频生成 (Video+Audio)", "Video + Audio"), "video_audio")
        col_mod.addWidget(mod_combo)
        row3.addLayout(col_mod, 1)
        lay.addLayout(row3)

        tok_hdr = QHBoxLayout()
        tok_hdr.addWidget(
            QLabel(
                tr(
                    "5. HuggingFace Token (受限/需登录模型必填，自动保存)",
                    "5. HuggingFace Token (Required for Gated/Private Repos)",
                )
            )
        )
        tok_hdr.addStretch(1)
        get_tok_btn = set_btn_role(QPushButton(tr("获取 HF Token", "Get HF Token")), "ghost")
        get_tok_btn.clicked.connect(lambda: webbrowser.open("https://huggingface.co/settings/tokens"))
        tok_hdr.addWidget(get_tok_btn)

        open_repo_btn = set_btn_role(
            QPushButton(tr("打开模型主页同意协议", "Open Repo & Accept License")), "ghost"
        )

        def _open_repo_license() -> None:
            r_clean = repo_edit.text().strip()
            url = (
                f"https://huggingface.co/{r_clean}"
                if "/" in r_clean
                else "https://huggingface.co/models?sort=trending"
            )
            webbrowser.open(url)

        open_repo_btn.clicked.connect(_open_repo_license)
        tok_hdr.addWidget(open_repo_btn)
        lay.addLayout(tok_hdr)

        tok_edit = QLineEdit(self.vm.hf_token)
        tok_edit.setEchoMode(QLineEdit.EchoMode.Password)
        tok_edit.setPlaceholderText("hf_xxxxxxxxxxxxxxxxxxxxxxxx")
        tok_edit.textChanged.connect(self.vm.set_hf_token)
        lay.addWidget(tok_edit)

        def _clear_trend_grid() -> None:
            while trend_grid.count():
                item = trend_grid.takeAt(0)
                w = item.widget() if item else None
                if w is not None:
                    w.deleteLater()

        def _select_trend_item(data: dict) -> None:
            repo_edit.setText(str(data.get("repo_id") or ""))
            pat_edit.setText(str(data.get("suggested_pattern") or ""))
            name_edit.setText(str(data.get("name") or ""))
            mod_val = str(data.get("modality") or "auto")
            m_idx = mod_combo.findData(mod_val)
            if m_idx >= 0:
                mod_combo.setCurrentIndex(m_idx)

        def _show_model_detail_dialog(target_repo: str) -> None:
            r_clean = (target_repo or "").strip()
            if not r_clean:
                return
            det_dlg = QDialog(dlg)
            det_dlg.setWindowTitle(tr(f"模型详情 — {r_clean}", f"Model Details — {r_clean}"))
            det_dlg.setMinimumWidth(600)
            det_lay = QVBoxLayout(det_dlg)
            det_lay.setContentsMargins(16, 16, 16, 16)
            det_lay.setSpacing(10)

            status_lbl = QLabel(
                tr("正在从 HuggingFace Hub 解析模型详情、张量参数与分片体积...", "Inspecting HuggingFace model metadata, parameters & shards...")
            )
            status_lbl.setWordWrap(True)
            det_lay.addWidget(status_lbl)

            files_scroll = QScrollArea()
            files_scroll.setWidgetResizable(True)
            files_scroll.setFixedHeight(170)
            files_wrap = QWidget()
            files_vbox = QVBoxLayout(files_wrap)
            files_vbox.setContentsMargins(6, 6, 6, 6)
            files_vbox.setSpacing(5)
            files_scroll.setWidget(files_wrap)
            det_lay.addWidget(files_scroll)

            readme_box = QTextBrowser()
            readme_box.setReadOnly(True)
            readme_box.setOpenExternalLinks(True)
            readme_box.setFixedHeight(115)
            det_lay.addWidget(readme_box)

            btm = QHBoxLayout()
            open_hf_btn = QPushButton(tr("在浏览器打开 HuggingFace 主页", "Open on HuggingFace"))
            open_hf_btn.clicked.connect(lambda: webbrowser.open(f"https://huggingface.co/{r_clean}"))
            btm.addWidget(open_hf_btn)
            btm.addStretch(1)
            close_det_btn = QPushButton(tr("关闭", "Close"))
            close_det_btn.clicked.connect(det_dlg.accept)
            btm.addWidget(close_det_btn)
            det_lay.addLayout(btm)

            def _on_detail(d: dict) -> None:
                if not isinstance(d, dict) or not d.get("ok"):
                    status_lbl.setText(
                        tr("无法获取该模型详情，请检查 Repo ID 或填写 HF Token。", "Failed to load model details. Check Repo ID or HF Token.")
                    )
                    return
                p_lbl = str(d.get("param_label") or tr("未标注", "N/A"))
                dep_lbl = strip_emoji(tr(str(d.get("deploy_label_zh") or ""), str(d.get("deploy_label_en") or "")))
                arch = str(d.get("architecture") or d.get("pipeline_tag") or "-")
                ctx_k = int(d.get("context_length") or 0) // 1024
                ctx_str = f" · {ctx_k}K" if ctx_k > 0 else ""
                lic = strip_emoji(str(d.get("license") or "-"))
                stor = float(d.get("used_storage_gb") or 0.0)
                status_lbl.setText(
                    f"<b>{d.get('repo_id')}</b> &nbsp; | &nbsp; "
                    f"{tr('参数量', 'Params')}: <b>{p_lbl}</b> &nbsp; | &nbsp; "
                    f"<b>{dep_lbl}</b><br>"
                    f"{tr('架构/上下文', 'Arch/Context')}: {arch}{ctx_str} &nbsp; · &nbsp; "
                    f"License: {lic} &nbsp; · &nbsp; "
                    f"{tr('仓库总大小', 'Repo Size')}: {stor:.1f} GB &nbsp; · &nbsp; "
                    f"Likes: {d.get('likes', 0)} &nbsp; Downloads: {d.get('downloads', 0)}"
                )
                wfiles = d.get("weight_files") or []
                if not wfiles:
                    files_vbox.addWidget(
                        QLabel(tr("未列出单独的顶层 .gguf/.safetensors 分片，添加后将按完整仓库拉取。", "No top-level .gguf/.safetensors shards listed."))
                    )
                else:
                    for wf in wfiles:
                        fn = str(wf.get("filename") or "")
                        sgb = float(wf.get("size_gb") or 0.0)
                        fit_txt = strip_emoji(tr(str(wf.get("fit_zh") or ""), str(wf.get("fit_en") or "")))
                        row_w = QHBoxLayout()
                        lbl = QLabel(f"{fn}   ({sgb:.2f} GB · {fit_txt})")
                        lbl.setStyleSheet("font-family: Consolas, monospace; font-size: 11px;")
                        row_w.addWidget(lbl, 1)
                        use_btn = QPushButton(tr("选用此文件", "Select File"))

                        def _pick_wf(_c: bool = False, fname: str = fn, det: dict = d) -> None:
                            repo_edit.setText(str(det.get("repo_id") or ""))
                            pat_edit.setText(fname)
                            name_edit.setText(str(det.get("name") or ""))
                            det_dlg.accept()

                        use_btn.clicked.connect(_pick_wf)
                        row_w.addWidget(use_btn)
                        files_vbox.addLayout(row_w)
                readme_box.setMarkdown(str(d.get("readme_excerpt") or tr("暂无 README 摘要", "No README excerpt available.")))

            self.vm.fetch_hf_model_detail(r_clean, on_loaded=_on_detail)
            det_dlg.exec()

        inspect_repo_btn.clicked.connect(lambda: _show_model_detail_dialog(repo_edit.text().strip()))

        def _populate_trending(items: list) -> None:
            _clear_trend_grid()
            if not items:
                empty_lbl = QLabel(
                    tr("未获取到匹配模型，可更换搜索词、点击刷新或直接输入 Repo ID", "No models found; try another keyword, click Refresh, or enter Repo ID below")
                )
                empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                empty_lbl.setStyleSheet("font-size: 11.5px; color: #64748B; padding: 18px;")
                trend_grid.addWidget(empty_lbl, 0, 0, 1, 2)
                return
            for idx, m in enumerate(items):
                if not isinstance(m, dict):
                    continue
                rid = str(m.get("repo_id") or "")
                m_name = str(m.get("name") or rid)
                lock_tag = tr("[受限] ", "[Gated] ") if m.get("is_gated") else ""
                p_lbl = str(m.get("param_label") or "")
                p_part = f"[{p_lbl}]" if p_lbl else ""
                tag = "GGUF" if m.get("is_gguf") else str(m.get("pipeline_tag") or "")
                likes = int(m.get("likes") or 0)
                dep_lbl = strip_emoji(
                    tr(
                        str(m.get("deploy_label_zh") or "显存待探测"),
                        str(m.get("deploy_label_en") or "VRAM TBD"),
                    )
                )
                cell_frame = QFrame()
                cell_lay = QHBoxLayout(cell_frame)
                cell_lay.setContentsMargins(0, 0, 0, 0)
                cell_lay.setSpacing(4)
                card_btn = QPushButton(f"{lock_tag}{m_name} {p_part}  [{tag} · Likes {likes}]\n{rid}\n{dep_lbl}")
                card_btn.setToolTip(f"{rid}\n{dep_lbl}")
                card_btn.setStyleSheet(
                    "QPushButton { text-align: left; padding: 6px 8px; border-radius: 7px; font-size: 11px; }"
                )
                card_btn.clicked.connect(lambda _c=False, d=m: _select_trend_item(d))
                cell_lay.addWidget(card_btn, 1)

                info_btn = QPushButton(tr("详情", "Details"))
                info_btn.setFixedWidth(52)
                info_btn.setToolTip(tr("查看模型参数、架构、分片体积与 README 详情", "View model parameters, shards & README details"))
                info_btn.clicked.connect(
                    lambda _c=False, d=m: (_select_trend_item(d), _show_model_detail_dialog(str(d.get("repo_id") or "")))
                )
                cell_lay.addWidget(info_btn)
                trend_grid.addWidget(cell_frame, idx // 2, idx % 2)

        def _trigger_fetch(force: bool = False) -> None:
            cat_val = str(cat_combo.currentData() or "all")
            sq_val = search_edit.text().strip()
            _clear_trend_grid()
            loading_lbl = QLabel(
                tr("正在从 HuggingFace Hub 实时拉取模型及参数量/显存评估...", "Fetching models, parameter counts & Colab VRAM fit from HuggingFace Hub...")
            )
            loading_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            loading_lbl.setStyleSheet("font-size: 11.5px; color: #64748B; padding: 18px;")
            trend_grid.addWidget(loading_lbl, 0, 0, 1, 2)
            self.vm.fetch_trending_hf_models(
                cat_val, force_refresh=force, on_loaded=_populate_trending, search_query=sq_val
            )

        cat_combo.currentIndexChanged.connect(lambda _i: _trigger_fetch(False))
        refresh_trend_btn.clicked.connect(lambda: _trigger_fetch(True))
        search_btn.clicked.connect(lambda: _trigger_fetch(True))
        search_edit.returnPressed.connect(lambda: _trigger_fetch(True))
        _trigger_fetch(False)

        btn_row = QHBoxLayout()
        cancel_btn = QPushButton(tr("取消", "Cancel"))
        cancel_btn.clicked.connect(dlg.reject)
        btn_row.addWidget(cancel_btn)
        btn_row.addStretch(1)

        add_btn = QPushButton(tr("添加到模型中心", "Add to Model Center"))

        def do_add(auto_dl: bool = False) -> None:
            r_txt = repo_edit.text().strip()
            if not r_txt:
                return
            self.vm.set_hf_token(tok_edit.text().strip())
            self.vm.register_custom_hf_model(
                repo_id=r_txt,
                include_pattern=pat_edit.text().strip(),
                display_name=name_edit.text().strip(),
                modality=str(mod_combo.currentData() or "auto"),
                auto_download=auto_dl,
            )
            dlg.accept()

        add_btn.clicked.connect(lambda: do_add(False))
        btn_row.addWidget(add_btn)

        if self.vm.is_connected:
            dl_btn = set_btn_role(
                QPushButton(tr("添加并立即下载权重", "Add & Download Weights Now")), "primary"
            )
            dl_btn.clicked.connect(lambda: do_add(True))
            btn_row.addWidget(dl_btn)

        lay.addLayout(btn_row)
        dlg.exec()


    def _refresh_comfyui_studio_cards(self) -> None:
        if self.vm.comfy_running:
            if self.vm.comfy_queue_running > 0 or self.vm.comfy_queue_pending > 0:
                self.cfy_status_badge.setText(
                    tr(
                        f"队列渲染中 ({self.vm.comfy_queue_running} 运行 / {self.vm.comfy_queue_pending} 排队)",
                        f"Rendering ({self.vm.comfy_queue_running} running / {self.vm.comfy_queue_pending} queued)",
                    )
                )
                self.cfy_status_badge.set_badge_style("#60A5FA", "rgba(59,130,246,0.16)")
            else:
                self.cfy_status_badge.setText(tr("画布在线待命", "Canvas Online"))
                self.cfy_status_badge.set_badge_style("#10B981", "rgba(16,185,129,0.16)")
        elif self.vm.comfy_starting:
            self.cfy_status_badge.setText(tr("正在部署启动...", "Deploying..."))
            self.cfy_status_badge.set_badge_style("#F59E0B", "rgba(245,158,11,0.16)")
        else:
            self.cfy_status_badge.setText(tr("未启动", "Stopped"))
            self.cfy_status_badge.set_badge_style("#94A3B8", "rgba(148,163,184,0.16)")

        self.cfy_launch_btn.setVisible(not self.vm.comfy_running)
        self.cfy_launch_btn.setEnabled(not self.vm.comfy_starting)
        self.cfy_running_bar.setVisible(self.vm.comfy_running)

        busy = self.vm.comfy_starting or self.vm.comfy_downloading_weight or bool(self.vm.comfy_installing_pack_id)
        self.cfy_main_prog.setVisible(busy)
        self.cfy_main_prog.setValue(int(self.vm.comfy_progress * 100))

        tunnel_str = self.vm.masked_url(self.vm.comfy_public_url) if self.vm.comfy_public_url else ""
        tunnel_tag = tr(f"  |  画布隧道: {tunnel_str}", f"  |  Tunnel: {tunnel_str}") if tunnel_str else ""
        self.cfy_tunnel_lbl.setText(f"{self.vm.comfy_status_message}{tunnel_tag}")

        # Preset Packs
        ready_cnt = sum(1 for p in self.vm.comfy_preset_packs if p.ready)
        total_packs = len(self.vm.comfy_preset_packs)
        self.cfy_packs_badge.setText(
            tr(f"已就绪 {ready_cnt} / {total_packs} 套", f"{ready_cnt} / {total_packs} Packs Ready")
        )
        packs_sig = (
            get_lang(),
            tuple(
                (p.id, p.ready, p.installed_models, p.total_models, p.workflows_installed)
                for p in self.vm.comfy_preset_packs
            ),
            self.vm.comfy_installing_pack_id,
            int(self.vm.comfy_progress * 100) if self.vm.comfy_installing_pack_id else 0,
            self.vm.comfy_downloading_weight,
            self.vm.dark_mode,
        )
        if packs_sig != self._last_packs_sig:
            self._last_packs_sig = packs_sig
            self._clear_layout(self.cfy_packs_container)
            for pack in self.vm.comfy_preset_packs:
                self.cfy_packs_container.addWidget(self._build_comfy_pack_row(pack))
            self.cfy_packs_widget.updateGeometry()

        self.cfy_tile_models[1].setText(
            tr(f"{self.vm.comfy_models_count} 个文件", f"{self.vm.comfy_models_count} files")
        )
        self.cfy_tile_nodes[1].setText(
            tr(f"{self.vm.comfy_custom_nodes_count} 个插件", f"{self.vm.comfy_custom_nodes_count} nodes")
        )
        self.cfy_tile_wfs[1].setText(
            tr(f"{self.vm.comfy_workflows_count} 套模板", f"{self.vm.comfy_workflows_count} templates")
        )

        # Cloud outputs list
        out_sig = (get_lang(), tuple((o.rel_path, o.mtime) for o in self.vm.comfy_recent_outputs))
        if out_sig != self._last_cfy_out_sig:
            self._last_cfy_out_sig = out_sig
            self._clear_layout(self.comfy_outputs_lay)
            if not self.vm.comfy_recent_outputs:
                empty = QLabel(tr("云端 output 目录暂无新成片", "No new outputs in cloud output/ folder"))
                empty.setStyleSheet("color: #64748B; font-size: 11.5px; padding: 12px;")
                self.comfy_outputs_lay.addWidget(empty)
            else:
                for item in self.vm.comfy_recent_outputs:
                    self.comfy_outputs_lay.addWidget(self._build_comfy_output_row(item))
            self.comfy_outputs_lay.addStretch(1)

    def _build_comfy_pack_row(self, pack: ComfyPresetPackItem) -> QFrame:
        f = QFrame()
        f.setObjectName("SubtlePanel")
        f.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        f.setMinimumHeight(88)
        hl = QHBoxLayout(f)
        hl.setContentsMargins(12, 10, 12, 10)
        hl.setSpacing(12)

        left = QVBoxLayout()
        left.setSpacing(4)
        t_row = QHBoxLayout()
        t_row.setSpacing(6)
        tl = QLabel(pack.title)
        tl.setStyleSheet("font-size: 12.5px; font-weight: 700;")
        t_row.addWidget(tl)
        is_dark = self.vm.dark_mode
        bg_col = "rgba(16,185,129,0.14)" if pack.is_primary_recommended else "rgba(59,130,246,0.14)"
        if pack.is_primary_recommended:
            fg_col = "#10B981" if is_dark else "#059669"
        else:
            fg_col = "#60A5FA" if is_dark else "#2563EB"
        t_row.addWidget(PillBadge(pack.badge, fg=fg_col, bg=bg_col))
        t_row.addStretch(1)
        left.addLayout(t_row)

        sc = QLabel(pack.scenario)
        sc.setWordWrap(True)
        sc.setStyleSheet("font-size: 11.5px; color: #64748B;")
        left.addWidget(sc)

        meta_prefix = tr(
            f"权重 {pack.installed_models}/{pack.total_models} · 约 {pack.approx_size_gb:.1f} GB  |  ",
            f"Weights {pack.installed_models}/{pack.total_models} · ~{pack.approx_size_gb:.1f} GB  |  ",
        )
        meta = QLabel(meta_prefix + " · ".join(pack.workflows))
        meta.setWordWrap(True)
        meta.setStyleSheet("font-family: Consolas, monospace; font-size: 10.5px; color: #64748B;")
        left.addWidget(meta)
        hl.addLayout(left, 1)

        right = QVBoxLayout()
        right.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        is_installing = self.vm.comfy_installing_pack_id == pack.id
        if pack.ready and not is_installing:
            open_b = set_btn_role(QPushButton(tr("打开画布直接使用", "Open in Canvas")), "success")
            open_b.clicked.connect(self._on_comfy_side_primary)
            rew_b = QPushButton(tr("重写中文模板", "Rewrite Templates"))
            rew_b.clicked.connect(lambda _c=False, pid=pack.id: self.vm.install_comfy_pack(pid, open_when_ready=False))
            right.addWidget(open_b)
            right.addWidget(rew_b)
        else:
            pct = int(self.vm.comfy_progress * 100)
            lbl = (
                tr(f"正在配齐 ({pct}%)...", f"Installing ({pct}%)...")
                if is_installing
                else tr("一键配齐模型与工作流", "1-Click Install Models & Workflows")
            )
            inst_b = set_btn_role(QPushButton(lbl), "primary")
            inst_b.setEnabled(not is_installing and not self.vm.comfy_downloading_weight)
            inst_b.clicked.connect(lambda _c=False, pid=pack.id: self.vm.install_comfy_pack(pid, open_when_ready=True))
            right.addWidget(inst_b)
        hl.addLayout(right)
        return f

    def _build_comfy_output_row(self, item: ComfyOutputMediaItem) -> QFrame:
        f = QFrame()
        f.setObjectName("SubtlePanel")
        hl = QHBoxLayout(f)
        hl.setContentsMargins(8, 6, 8, 6)
        hl.setSpacing(6)
        ic = tr("[视频]", "[Vid]") if item.media_type == "video" else tr("[图片]", "[Img]")
        lbl = QLabel(f"{ic} {item.filename}\n{item.size_mb:.1f} MB")
        lbl.setStyleSheet("font-size: 11px;")
        hl.addWidget(lbl, 1)
        pull_b = set_btn_role(QPushButton(tr("拉回", "Pull")), "primary")
        pull_b.setFixedWidth(56)
        pull_b.clicked.connect(lambda _c=False, it=item: self.vm.pull_comfy_output_media(it))
        hl.addWidget(pull_b)
        return f

    def _api_snippets(self) -> Dict[str, str]:
        base_host = self.vm.normalized_base_url or "https://xxxx.gradio.live"
        shown_host = self.vm.masked_url(base_host)
        oai_base_real = f"{base_host}/v1"
        oai_base_shown = f"{shown_host}/v1"
        key = self.vm.api_access_key if self.vm.api_key_enabled else "sk-no-key-required"

        if self.vm.selected_model_id == "qwen38_27b_gguf":
            repo = "unsloth/Qwen3.8-27B-GGUF"
        elif self.vm.selected_model_id == "qwen38_27b":
            repo = "Qwen/Qwen3.8-27B"
        elif "qwen38_27b_gguf" in self.vm.loaded_model_ids and "qwen38_27b" not in self.vm.loaded_model_ids:
            repo = "unsloth/Qwen3.8-27B-GGUF"
        else:
            repo = "Qwen/Qwen3.8-27B"

        py_msg = tr("帮我设计一个高并发网关架构", "Design a high-concurrency API gateway architecture")
        oai_curl_msg = tr("用三句话解释量子纠缠", "Explain quantum entanglement in three sentences")
        ant_curl_msg = tr("分析 Rust 所有权机制的核心优势", "Explain the core advantages of Rust ownership")
        ps_comment = tr("# PowerShell (Windows 推荐)", "# PowerShell (Recommended on Windows)")

        def make_py(b: str) -> str:
            return (
                "from openai import OpenAI\n\n"
                f'client = OpenAI(base_url="{b}", api_key="{key}")\n'
                "stream = client.chat.completions.create(\n"
                f'    model="{repo}",\n'
                f'    messages=[{{"role": "user", "content": "{py_msg}"}}],\n'
                "    stream=True,\n"
                ")\n"
                "for chunk in stream:\n"
                "    delta = chunk.choices[0].delta\n"
                '    if getattr(delta, "reasoning_content", None):\n'
                '        print(delta.reasoning_content, end="", flush=True)\n'
                "    if delta.content:\n"
                '        print(delta.content, end="", flush=True)'
            )

        oai_curl = (
            f"curl {oai_base_real}/chat/completions \\\n"
            '  -H "Content-Type: application/json" \\\n'
            f'  -H "Authorization: Bearer {key}" \\\n'
            f'  -d \'{{"model": "{repo}", "stream": true, "messages": [{{"role": "user", "content": "{oai_curl_msg}"}}]}}\''
        )
        ant_curl = (
            f"curl {base_host}/v1/messages \\\n"
            '  -H "Content-Type: application/json" \\\n'
            f'  -H "x-api-key: {key}" \\\n'
            '  -H "anthropic-version: 2023-06-01" \\\n'
            f'  -d \'{{"model": "{repo}", "max_tokens": 2048, "stream": true, "messages": [{{"role": "user", "content": "{ant_curl_msg}"}}]}}\''
        )
        claude_ps = (
            f'$env:ANTHROPIC_BASE_URL="{base_host}"\n'
            f'$env:ANTHROPIC_API_KEY="{key}"\n'
            f'$env:ANTHROPIC_MODEL="{repo}"\n'
            "claude"
        )
        claude_ps_shown = (
            f'{ps_comment}\n$env:ANTHROPIC_BASE_URL="{shown_host}"\n'
            f'$env:ANTHROPIC_API_KEY="{key}"\n'
            f'$env:ANTHROPIC_MODEL="{repo}"\n\n'
            f'# Git Bash / WSL\nexport ANTHROPIC_BASE_URL="{shown_host}"\n'
            f'export ANTHROPIC_API_KEY="{key}"\n'
            f'export ANTHROPIC_MODEL="{repo}"'
        )
        claude_sh = (
            f'export ANTHROPIC_BASE_URL="{base_host}"\n'
            f'export ANTHROPIC_API_KEY="{key}"\n'
            f'export ANTHROPIC_MODEL="{repo}"'
        )
        return {
            "repo": repo,
            "oai_base": oai_base_real,
            "oai_base_shown": oai_base_shown,
            "oai_chat": f"{oai_base_real}/chat/completions",
            "oai_chat_shown": f"{oai_base_shown}/chat/completions",
            "oai_py": make_py(oai_base_real),
            "oai_py_shown": make_py(oai_base_shown),
            "oai_curl": oai_curl,
            "ant_base": base_host,
            "ant_base_shown": shown_host,
            "ant_msg": f"{base_host}/v1/messages",
            "ant_msg_shown": f"{shown_host}/v1/messages",
            "ant_curl": ant_curl,
            "claude_ps": claude_ps,
            "claude_ps_shown": claude_ps_shown,
            "claude_sh": claude_sh,
        }

    def _refresh_api_gateway_cards(self) -> None:
        sn = self._api_snippets()
        self.api_req_count_lbl.setText(
            tr(f"累计 API 请求: {self.vm.api_request_count} 次", f"Total API Requests: {self.vm.api_request_count}")
        )
        self.api_auth_chk.setChecked(self.vm.api_key_enabled)
        self.api_key_row_w.setVisible(self.vm.api_key_enabled)
        if not self.api_key_input.hasFocus():
            self.api_key_input.setText(self.vm.api_access_key)

        disp_name = "Qwen3.8-27B-GGUF" if "GGUF" in sn["repo"] else "Qwen3.8-27B"
        if not self.vm.is_qwen_loaded_in_vram:
            self.api_coresident_hint.setText(
                tr(
                    f"提示：请先在左侧点击「加载到显存」装载 {disp_name}",
                    f"Tip: Click 'Load to VRAM' on the left to load {disp_name} first",
                )
            )
            self.api_coresident_hint.setStyleSheet("color: #F59E0B; font-size: 11.5px;")
        elif len(self.vm.loaded_model_ids) > 1:
            self.api_coresident_hint.setText(
                tr(
                    f"多模型共驻已激活：外部 API 可随时调用 {disp_name}",
                    f"Multi-model co-residency active: external APIs can call {disp_name} anytime",
                )
            )
            self.api_coresident_hint.setStyleSheet("color: #10B981; font-size: 11.5px;")
        else:
            self.api_coresident_hint.setText(
                tr(f"{disp_name} 网关已就绪", f"{disp_name} API Gateway Ready")
            )
            self.api_coresident_hint.setStyleSheet("color: #10B981; font-size: 11.5px;")

        self.oai_base_lbl.setText(sn["oai_base_shown"])
        self.oai_chat_lbl.setText(sn["oai_chat_shown"])
        self.oai_model_lbl.setText(sn["repo"])
        self.oai_code_box.setPlainText(sn["oai_py_shown"])

        self.ant_base_lbl.setText(sn["ant_base_shown"])
        self.ant_msg_lbl.setText(sn["ant_msg_shown"])
        self.ant_code_box.setPlainText(sn["claude_ps_shown"])

