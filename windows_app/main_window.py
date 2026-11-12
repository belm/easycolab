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
    image_resolutions_for,
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


from windows_app.workspace_mixin import WorkspaceMixin


class EasyColabMainWindow(WorkspaceMixin, QMainWindow):
    def __init__(self, vm: EasyColabViewModel):
        super().__init__()
        self.vm = vm
        self._syncing_ui = False
        self._show_right_log = True
        self._last_coresident_sig: object = None
        self._last_shards_sig: object = None
        self._last_modes_sig: object = None
        self._last_packs_sig: object = None
        self._last_cfy_out_sig: object = None

        self.setWindowTitle(
            tr(
                "EasyColab — 云端大显存多模态 AI 创作工作台",
                "EasyColab — Cloud High-VRAM Multimodal AI Studio",
            )
        )
        self.setWindowIcon(build_app_icon())
        self.resize(1480, 900)
        self.setMinimumSize(1280, 820)

        central = QWidget()
        self.setCentralWidget(central)
        main_hbox = QHBoxLayout(central)
        main_hbox.setContentsMargins(0, 0, 0, 0)
        main_hbox.setSpacing(0)

        # 1. Left Sidebar (356px)
        self.left_sidebar = self._build_left_sidebar()
        main_hbox.addWidget(self.left_sidebar)

        # 2. Center Studio Workspace (expanding)
        self.center_workspace = self._build_center_workspace()
        main_hbox.addWidget(self.center_workspace, 1)

        # 3. Right Collapsible Run Log Panel (352px)
        self.right_log_panel = self._build_right_log_panel()
        main_hbox.addWidget(self.right_log_panel)

        # Shortcuts
        sc_gen1 = QShortcut(QKeySequence("Ctrl+Return"), self)
        sc_gen1.activated.connect(self._trigger_generate)
        sc_gen2 = QShortcut(QKeySequence("Ctrl+Enter"), self)
        sc_gen2.activated.connect(self._trigger_generate)
        sc_help = QShortcut(QKeySequence("Ctrl+Shift+/"), self)
        sc_help.activated.connect(lambda: self.open_onboarding_guide(0))
        sc_f1 = QShortcut(QKeySequence("F1"), self)
        sc_f1.activated.connect(lambda: self.open_onboarding_guide(0))

        # Wire ViewModel signals
        self.vm.state_changed.connect(self._refresh_all_state)
        self.vm.telemetry_changed.connect(self._refresh_telemetry)
        self.vm.console_changed.connect(self._refresh_console)
        self.vm.chat_changed.connect(self._refresh_chat_conversation)
        self.vm.media_list_changed.connect(self._refresh_media_gallery)
        self.vm.media_selected.connect(self._on_media_selected)
        self.vm.theme_changed.connect(self._apply_theme)
        self.vm.language_changed.connect(self._on_language_changed)

        self._apply_theme()
        self._refresh_all_state()
        self._refresh_telemetry()
        self._refresh_console()
        self._refresh_media_gallery()

        # First-run onboarding guide after 350ms
        if not self.vm.has_seen_onboarding:
            QTimer.singleShot(350, lambda: self.open_onboarding_guide(0))

    @property
    def palette_obj(self) -> StudioPalette:
        return DARK_PALETTE if self.vm.dark_mode else LIGHT_PALETTE

    def _on_language_changed(self) -> None:
        """Rebuild the 3-column studio central widget live while preserving transient UI state."""
        # 1. Snapshot transient widget states not stored on self.vm
        well_paths = {
            "video_first_well": getattr(self.video_first_well, "_file_path", None),
            "video_last_well": getattr(self.video_last_well, "_file_path", None),
            "vlm_img1_well": getattr(self.vlm_img1_well, "_file_path", None),
            "vlm_img2_well": getattr(self.vlm_img2_well, "_file_path", None),
            "img_ref1_well": getattr(self.img_ref1_well, "_file_path", None),
            "img_ref2_well": getattr(self.img_ref2_well, "_file_path", None),
        }
        show_log = self._show_right_log
        oauth_txt = self.oauth_input.text()
        hf_tok_txt = self.hf_token_input.text()
        cfy_src_txt = self.cfy_src_input.text()
        cfy_fn_txt = self.cfy_fname_input.text()
        cfy_sub_val = self.cfy_subfolder_combo.currentData() or self.cfy_subfolder_combo.currentText()
        llm_txt = (
            self.vm.visual_prompt
            if self.vm.active_model_spec.modality == ModelModality.LLM_VLM
            else self.llm_prompt_edit.toPlainText()
        )
        api_key_txt = self.api_key_input.text()
        shards_expanded = bool(getattr(self.shards_box, "_expanded", False))
        cur_media = self.vm.current_media_path

        # 2. Cleanly stop video playback on old preview widget before teardown
        self.media_preview.stop_video()

        # 3. Reset cached layout signatures
        self._last_coresident_sig = None
        self._last_shards_sig = None
        self._last_modes_sig = None
        self._last_packs_sig = None
        self._last_cfy_out_sig = None

        # 4. Update window title
        self.setWindowTitle(
            tr(
                "EasyColab — 云端大显存多模态 AI 创作工作台",
                "EasyColab — Cloud High-VRAM Multimodal AI Studio",
            )
        )

        # 5. Rebuild fresh central widget
        central = QWidget()
        main_hbox = QHBoxLayout(central)
        main_hbox.setContentsMargins(0, 0, 0, 0)
        main_hbox.setSpacing(0)

        self.left_sidebar = self._build_left_sidebar()
        main_hbox.addWidget(self.left_sidebar)

        self.center_workspace = self._build_center_workspace()
        main_hbox.addWidget(self.center_workspace, 1)

        self.right_log_panel = self._build_right_log_panel()
        self.right_log_panel.setVisible(show_log)
        main_hbox.addWidget(self.right_log_panel)

        old_central = self.takeCentralWidget()
        self.setCentralWidget(central)
        if old_central is not None:
            old_central.deleteLater()

        # 6. Restore snapshotted transient inputs & drop wells
        self._syncing_ui = True
        self.oauth_input.setText(oauth_txt)
        self.hf_token_input.setText(hf_tok_txt)
        self.cfy_src_input.setText(cfy_src_txt)
        self.cfy_fname_input.setText(cfy_fn_txt)
        sub_idx = self.cfy_subfolder_combo.findData(cfy_sub_val)
        if sub_idx >= 0:
            self.cfy_subfolder_combo.setCurrentIndex(sub_idx)
        self.llm_prompt_edit.setPlainText(llm_txt)
        if api_key_txt:
            self.api_key_input.setText(api_key_txt)
        self.shards_box.set_expanded(shards_expanded)
        self._syncing_ui = False

        for attr_name, fpath in well_paths.items():
            if fpath is not None and Path(fpath).exists():
                getattr(self, attr_name).load_from_file(Path(fpath))

        self._apply_theme()
        self._refresh_all_state()
        self._refresh_telemetry()
        self._refresh_console()
        self._refresh_chat_conversation()
        self._refresh_media_gallery()
        if cur_media is not None and cur_media.exists():
            el = self.vm.media_elapsed_map.get(cur_media.name)
            self.media_preview.load_media(cur_media, elapsed_seconds=el, auto_play=False)

    def _apply_theme(self) -> None:
        pal = self.palette_obj
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(build_stylesheet(pal))
        self.theme_btn.setText(tr("亮色", "Light") if pal.is_dark else tr("深色", "Dark"))
        self.theme_btn.setToolTip(tr("切换亮色 / 深色工作台主题", "Toggle Light / Dark studio theme"))
        for w in (self.chart_vram, self.chart_ram, self.chart_disk, self.chart_combined):
            w.set_palette_theme(pal)
        for well in (
            self.video_first_well,
            self.video_last_well,
            self.vlm_img1_well,
            self.vlm_img2_well,
            self.img_ref1_well,
            self.img_ref2_well,
        ):
            well.set_palette_theme(pal)
        self.media_preview.set_palette_theme(pal)
        self._refresh_all_state()
        self._refresh_chat_conversation()
        self._refresh_console()

    # ═══════════════════════════════════════════════════════════════════════════
    # 1. LEFT SIDEBAR (356px, 4 Cards)
    # ═══════════════════════════════════════════════════════════════════════════

    def _build_left_sidebar(self) -> QWidget:
        container = QWidget()
        container.setObjectName("LeftSidebarContainer")
        container.setFixedWidth(356)
        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)

        # Top 40px header
        hdr = QFrame()
        hdr.setObjectName("TopHeaderBar")
        hdr.setFixedHeight(42)
        h_lay = QHBoxLayout(hdr)
        h_lay.setContentsMargins(14, 0, 12, 0)
        h_lay.setSpacing(6)

        logo = QLabel()
        logo.setPixmap(draw_easycolab_icon_pixmap(22))
        h_lay.addWidget(logo)

        title = QLabel("EasyColab")
        title.setStyleSheet("font-size: 14px; font-weight: 800; letter-spacing: 0.2px;")
        h_lay.addWidget(title)
        h_lay.addStretch(1)

        self.lang_btn = set_btn_role(QPushButton("EN" if not is_en() else "中文"), "pill")
        self.lang_btn.setFixedHeight(26)
        self.lang_btn.setToolTip(tr("切换界面为英文 (Switch to English)", "Switch UI to Chinese (切换为中文)"))
        self.lang_btn.clicked.connect(self.vm.toggle_language)
        h_lay.addWidget(self.lang_btn)

        self.theme_btn = set_btn_role(QPushButton(tr("深色", "Dark")), "pill")
        self.theme_btn.setFixedHeight(26)
        self.theme_btn.clicked.connect(self.vm.toggle_dark_mode)
        h_lay.addWidget(self.theme_btn)

        guide_pill = set_btn_role(QPushButton(tr("新手引导", "Guide")), "pill")
        guide_pill.setFixedHeight(26)
        guide_pill.clicked.connect(lambda: self.open_onboarding_guide(0))
        h_lay.addWidget(guide_pill)
        vbox.addWidget(hdr)

        # Scrollable cards stack
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        body_w = QWidget()
        body_lay = QVBoxLayout(body_w)
        body_lay.setContentsMargins(12, 12, 12, 16)
        body_lay.setSpacing(12)

        body_lay.addWidget(self._build_sidebar_card1_instance())
        body_lay.addWidget(self._build_sidebar_card2_cu_idle())
        body_lay.addWidget(self._build_sidebar_card3_models())
        body_lay.addWidget(self._build_sidebar_card4_params())
        body_lay.addStretch(1)

        scroll.setWidget(body_w)
        vbox.addWidget(scroll, 1)
        return container

    def _build_sidebar_card1_instance(self) -> SidebarCard:
        self.conn_badge = PillBadge(tr("离线", "Offline"), fg="#64748B", bg="rgba(148,163,184,0.16)")
        card = SidebarCard(tr("Colab 算力实例", "Colab Cloud Runtime"), trailing=self.conn_badge)

        # Row 1: Google Account
        acc_row = QHBoxLayout()
        acc_row.setSpacing(6)
        acc_lbl = QLabel(tr("Google 账号", "Google Account"))
        acc_lbl.setStyleSheet("color: #64748B; font-size: 11.5px;")
        acc_row.addWidget(acc_lbl)

        self.account_val_lbl = QLabel(tr("未绑定", "Not Linked"))
        self.account_val_lbl.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.account_val_lbl.setStyleSheet("font-size: 11.5px; font-weight: 600;")
        acc_row.addWidget(self.account_val_lbl, 1)

        self.bind_btn = set_btn_role(QPushButton(tr("绑定", "Bind")), "primary")
        self.bind_btn.clicked.connect(lambda: self.vm.start_google_oauth_login(False))
        acc_row.addWidget(self.bind_btn)

        self.acc_refresh_btn = QPushButton(tr("刷新", "Refresh"))
        self.acc_refresh_btn.clicked.connect(self.vm.refresh_official_colab_account_usage)
        acc_row.addWidget(self.acc_refresh_btn)

        self.acc_menu_btn = QPushButton(tr("换号", "Account"))
        acc_menu = QMenu(self)
        act_switch = QAction(tr("切换 Google 账号...", "Switch Google Account..."), self)
        act_switch.triggered.connect(lambda: self.vm.start_google_oauth_login(True))
        act_logout = QAction(tr("退出当前账号", "Sign Out"), self)
        act_logout.triggered.connect(self.vm.logout_google_account)
        acc_menu.addAction(act_switch)
        acc_menu.addSeparator()
        acc_menu.addAction(act_logout)
        self.acc_menu_btn.setMenu(acc_menu)
        acc_row.addWidget(self.acc_menu_btn)
        card.body.addLayout(acc_row)

        # Row 1b: OAuth Code input (hidden by default)
        self.oauth_box = QWidget()
        oa_lay = QHBoxLayout(self.oauth_box)
        oa_lay.setContentsMargins(0, 0, 0, 0)
        oa_lay.setSpacing(5)
        self.oauth_input = QLineEdit()
        self.oauth_input.setPlaceholderText(tr("粘贴浏览器显示的授权码", "Paste OAuth code from browser"))
        self.oauth_input.returnPressed.connect(self._submit_oauth_code)
        oa_lay.addWidget(self.oauth_input, 1)
        oa_ok = set_btn_role(QPushButton(tr("确认", "Submit")), "primary")
        oa_ok.clicked.connect(self._submit_oauth_code)
        oa_cancel = QPushButton(tr("取消", "Cancel"))
        oa_cancel.clicked.connect(self._cancel_oauth_code)
        oa_lay.addWidget(oa_ok)
        oa_lay.addWidget(oa_cancel)
        self.oauth_box.setVisible(False)
        card.body.addWidget(self.oauth_box)

        # Row 2: GPU Picker + 1-Click Wake
        self.wake_row_widget = QWidget()
        wk_lay = QHBoxLayout(self.wake_row_widget)
        wk_lay.setContentsMargins(0, 0, 0, 0)
        wk_lay.setSpacing(6)
        self.gpu_combo = QComboBox()
        self.gpu_combo.setFixedWidth(134)
        for val, label in GPU_CHOICES:
            self.gpu_combo.addItem(label, val)
        self.gpu_combo.currentIndexChanged.connect(self._on_gpu_combo_changed)
        wk_lay.addWidget(self.gpu_combo)

        self.wake_btn = set_btn_role(QPushButton(tr("唤醒实例并部署", "Wake & Deploy")), "primary")
        self.wake_btn.clicked.connect(self.vm.wake_colab_headless)
        wk_lay.addWidget(self.wake_btn, 1)
        card.body.addWidget(self.wake_row_widget)

        # Row 3: Server URL + Privacy Eye + Connect + ?
        url_row = QHBoxLayout()
        url_row.setSpacing(5)
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://xxxx.gradio.live")
        self.url_input.setStyleSheet("font-family: Consolas, monospace; font-size: 11.5px;")
        self.url_input.editingFinished.connect(lambda: self.vm.set_colab_server_url(self.url_input.text()))
        self.url_input.returnPressed.connect(lambda: self._on_connect_clicked())
        url_row.addWidget(self.url_input, 1)

        self.mask_eye_btn = QPushButton(tr("打码", "Mask"))
        self.mask_eye_btn.setFixedWidth(58)
        self.mask_eye_btn.setToolTip(
            tr(
                "录屏/截图防泄密打码开关：隐藏公网隧道域名与账号邮箱",
                "Stream/screenshot privacy mask: hide public tunnel URLs and account email",
            )
        )
        self.mask_eye_btn.clicked.connect(lambda: self.vm.set_mask_server_url(not self.vm.mask_server_url))
        url_row.addWidget(self.mask_eye_btn)

        self.connect_btn = QPushButton(tr("连接", "Connect"))
        self.connect_btn.clicked.connect(self._on_connect_clicked)
        url_row.addWidget(self.connect_btn)

        help_mini = set_btn_role(QPushButton("?"), "ghost")
        help_mini.setFixedWidth(24)
        help_mini.clicked.connect(lambda: self.open_onboarding_guide(0))
        url_row.addWidget(help_mini)
        card.body.addLayout(url_row)

        auth_row = QHBoxLayout()
        auth_row.addWidget(QLabel(tr("用户名：easycolab", "User: easycolab")))
        self.admin_input = QLineEdit()
        self.admin_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.admin_input.setPlaceholderText(tr("管理密码", "Management password"))
        self.admin_input.textEdited.connect(self.vm.set_admin_password)
        auth_row.addWidget(self.admin_input)
        copy_admin = QPushButton(tr("复制密码", "Copy password"))
        copy_admin.clicked.connect(lambda: QGuiApplication.clipboard().setText(self.vm.admin_password))
        auth_row.addWidget(copy_admin)
        card.body.addLayout(auth_row)

        # Row 4: Hardware Status + Chart Mode Toggle
        hw_hdr = QHBoxLayout()
        hw_hdr.setSpacing(5)
        self.hw_dot = StatusDot("#64748B", size=8)
        hw_hdr.addWidget(self.hw_dot)
        self.hw_gpu_lbl = QLabel(tr("尚未连接云端 GPU", "Cloud GPU Not Connected"))
        self.hw_gpu_lbl.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.hw_gpu_lbl.setStyleSheet("font-size: 11px; font-weight: 600;")
        hw_hdr.addWidget(self.hw_gpu_lbl, 1)

        self.drive_pill = PillBadge(tr("云盘", "Drive"), fg="#10B981", bg="rgba(16,185,129,0.16)")
        self.drive_pill.setToolTip(tr("Google Drive 云盘持久化已激活", "Google Drive cloud persistence active"))
        self.drive_pill.setVisible(False)
        hw_hdr.addWidget(self.drive_pill)

        self.chart_mode_btn = set_btn_role(QPushButton(tr("同屏", "Overlay")), "pill")
        self.chart_mode_btn.setToolTip(
            tr("切换「分项折线图」与「三指标同屏对比图」", "Toggle between separate metric charts and combined overlay chart")
        )
        self.chart_mode_btn.clicked.connect(lambda: self.vm.set_combined_chart_mode(not self.vm.combined_chart_mode))
        hw_hdr.addWidget(self.chart_mode_btn)
        card.body.addLayout(hw_hdr)

        # Telemetry Charts Stack (Page 0: 3 separate charts, Page 1: combined chart)
        self.charts_stack = AutoHeightStackedWidget()
        sep_w = QWidget()
        sep_lay = QVBoxLayout(sep_w)
        sep_lay.setContentsMargins(0, 0, 0, 0)
        sep_lay.setSpacing(6)
        self.chart_vram = SingleMetricChartWidget(tr("GPU 显存", "GPU VRAM"), "#5487FA")
        self.chart_ram = SingleMetricChartWidget(tr("系统内存", "System RAM"), "#1AC287")
        self.chart_disk = SingleMetricChartWidget(tr("实例磁盘", "Runtime Disk"), "#0DBAE0")
        sep_lay.addWidget(self.chart_vram)
        sep_lay.addWidget(self.chart_ram)
        sep_lay.addWidget(self.chart_disk)
        self.charts_stack.addWidget(sep_w)

        self.chart_combined = CombinedTelemetryChartWidget()
        self.charts_stack.addWidget(self.chart_combined)
        card.body.addWidget(self.charts_stack)

        # Footer for /dev/shm and Google Drive free space
        self.storage_footer_lbl = QLabel("")
        self.storage_footer_lbl.setStyleSheet("font-size: 10.5px; color: #64748B; font-family: Consolas, monospace;")
        self.storage_footer_lbl.setVisible(False)
        card.body.addWidget(self.storage_footer_lbl)

        return card

    def _build_sidebar_card2_cu_idle(self) -> SidebarCard:
        card = SidebarCard(tr("算力额度与自动休眠", "Compute Units & Auto-Sleep"))

        # 3-Column Metric Bar
        metrics_frame = QFrame()
        metrics_frame.setObjectName("SubtlePanel")
        m_grid = QGridLayout(metrics_frame)
        m_grid.setContentsMargins(10, 8, 10, 8)
        m_grid.setHorizontalSpacing(8)
        m_grid.setVerticalSpacing(2)

        self.cu_title_lbl = QLabel(tr("账户余额", "CU Balance"))
        self.cu_title_lbl.setStyleSheet("font-size: 10.5px; color: #64748B;")
        burn_title = QLabel(tr("扣费速率", "Burn Rate"))
        burn_title.setStyleSheet("font-size: 10.5px; color: #64748B;")
        up_title = QLabel(tr("本次运行", "Session Uptime"))
        up_title.setStyleSheet("font-size: 10.5px; color: #64748B;")

        self.cu_val_lbl = QLabel("-- CU")
        self.cu_val_lbl.setStyleSheet("font-size: 12.5px; font-weight: 700; font-family: Consolas, monospace;")
        self.burn_val_lbl = QLabel("0.00 CU/h")
        self.burn_val_lbl.setStyleSheet("font-size: 12.5px; font-weight: 700; font-family: Consolas, monospace;")
        self.uptime_val_lbl = QLabel("00:00:00")
        self.uptime_val_lbl.setStyleSheet("font-size: 12.5px; font-weight: 700; font-family: Consolas, monospace;")

        m_grid.addWidget(self.cu_title_lbl, 0, 0)
        m_grid.addWidget(burn_title, 0, 1)
        m_grid.addWidget(up_title, 0, 2)
        m_grid.addWidget(self.cu_val_lbl, 1, 0)
        m_grid.addWidget(self.burn_val_lbl, 1, 1)
        m_grid.addWidget(self.uptime_val_lbl, 1, 2)
        card.body.addWidget(metrics_frame)

        # Idle Auto-Release Row
        idle_row = QHBoxLayout()
        idle_row.setSpacing(8)
        idle_lbl = QLabel(tr("闲置自动释放", "Idle Auto-Release"))
        idle_lbl.setStyleSheet("font-size: 11.5px; color: #64748B;")
        idle_row.addWidget(idle_lbl)
        idle_row.addStretch(1)
        self.idle_combo = QComboBox()
        for mins, txt in get_idle_timeout_choices():
            self.idle_combo.addItem(txt, mins)
        self.idle_combo.currentIndexChanged.connect(self._on_idle_combo_changed)
        idle_row.addWidget(self.idle_combo)
        card.body.addLayout(idle_row)

        self.idle_countdown_lbl = QLabel("")
        self.idle_countdown_lbl.setWordWrap(True)
        self.idle_countdown_lbl.setStyleSheet("font-size: 11px; color: #64748B;")
        card.body.addWidget(self.idle_countdown_lbl)

        # Destructive Release All VMs Button
        self.release_all_btn = set_btn_role(QPushButton(tr("释放全部实例", "Release All Runtimes")), "danger")
        self.release_all_btn.clicked.connect(self._confirm_release_all_vms)
        card.body.addWidget(self.release_all_btn)

        return card

    def _build_sidebar_card3_models(self) -> SidebarCard:
        self.model_center_badge = PillBadge("HF 6", fg="#60A5FA", bg="rgba(59,130,246,0.16)")
        card = SidebarCard(tr("开源模型中心", "Open Model Center"), trailing=self.model_center_badge)

        # Model Selector Buttons (Preset + Custom HF Repos)
        self._model_card_btns: Dict[str, QPushButton] = {}
        self.model_buttons_box = QWidget()
        self.model_buttons_lay = QVBoxLayout(self.model_buttons_box)
        self.model_buttons_lay.setContentsMargins(0, 0, 0, 0)
        self.model_buttons_lay.setSpacing(6)
        card.body.addWidget(self.model_buttons_box)

        self.add_custom_model_btn = QPushButton(
            tr("+ 添加自定义 HuggingFace 模型...", "+ Add Custom HuggingFace Repo...")
        )
        self.add_custom_model_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_custom_model_btn.setMinimumHeight(34)
        self.add_custom_model_btn.clicked.connect(self._open_add_custom_model_dialog)
        card.body.addWidget(self.add_custom_model_btn)

        # Co-residency strip (visible when >= 1 model loaded in VRAM)
        self.coresident_box = QFrame()
        self.coresident_box.setObjectName("SubtlePanel")
        self.coresident_lay = QVBoxLayout(self.coresident_box)
        self.coresident_lay.setContentsMargins(8, 6, 8, 6)
        self.coresident_lay.setSpacing(4)
        self.coresident_box.setVisible(False)
        card.body.addWidget(self.coresident_box)

        # Selected Model Control Stack (Page 0: Standard Model Weights/VRAM, Page 1: ComfyUI mini controls)
        self.model_ctrl_stack = AutoHeightStackedWidget()

        # Page 0: Standard Model Weight & VRAM Manager
        std_w = QFrame()
        std_w.setObjectName("SubtlePanel")
        std_lay = QVBoxLayout(std_w)
        std_lay.setContentsMargins(10, 8, 10, 9)
        std_lay.setSpacing(6)

        repo_row = QHBoxLayout()
        repo_row.addWidget(QLabel(tr("HF 仓库", "HF Repo")))
        self.repo_val_lbl = QLabel()
        self.repo_val_lbl.setStyleSheet("font-family: Consolas, monospace; font-size: 11px; color: #94A3B8;")
        repo_row.addWidget(self.repo_val_lbl, 1, Qt.AlignmentFlag.AlignRight)
        std_lay.addLayout(repo_row)

        wt_row = QHBoxLayout()
        wt_row.addWidget(QLabel(tr("磁盘权重", "Disk Weights")))
        self.weight_status_lbl = QLabel()
        self.weight_status_lbl.setStyleSheet("font-size: 11.5px; font-weight: 600;")
        wt_row.addWidget(self.weight_status_lbl, 1, Qt.AlignmentFlag.AlignRight)
        std_lay.addLayout(wt_row)

        # Collapsible shard list
        self.shards_box = CollapsibleBox(tr("查看权重分片 (0)", "View Weight Shards (0)"), expanded=False)
        self.shards_scroll = QScrollArea()
        self.shards_scroll.setFixedHeight(112)
        self.shards_scroll.setWidgetResizable(True)
        self.shards_list_w = QWidget()
        self.shards_list_lay = QVBoxLayout(self.shards_list_w)
        self.shards_list_lay.setContentsMargins(2, 2, 2, 2)
        self.shards_list_lay.setSpacing(2)
        self.shards_scroll.setWidget(self.shards_list_w)
        self.shards_box.content_layout.addWidget(self.shards_scroll)
        std_lay.addWidget(self.shards_box)

        # Optional HF Token for gated downloads
        hf_row = QHBoxLayout()
        hf_lbl = QLabel("HF Token")
        hf_lbl.setStyleSheet("font-size: 11px; color: #94A3B8;")
        hf_row.addWidget(hf_lbl)
        self.hf_token_input = QLineEdit(self.vm.hf_token)
        self.hf_token_input.setPlaceholderText(tr("可选 (下载受限仓库时填写)", "Optional (for gated HF repos)"))
        self.hf_token_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.hf_token_input.editingFinished.connect(self._on_hf_token_edited)
        hf_row.addWidget(self.hf_token_input, 1)
        std_lay.addLayout(hf_row)

        # KV context mismatch hint for Qwen GGUF
        self.kv_mismatch_lbl = QLabel("")
        self.kv_mismatch_lbl.setWordWrap(True)
        self.kv_mismatch_lbl.setStyleSheet("font-size: 11px; color: #F59E0B;")
        self.kv_mismatch_lbl.setVisible(False)
        std_lay.addWidget(self.kv_mismatch_lbl)

        # Offline hint banner
        self.offline_banner = QWidget()
        ob_lay = QHBoxLayout(self.offline_banner)
        ob_lay.setContentsMargins(0, 0, 0, 0)
        ob_lay.setSpacing(6)
        ob_txt = QLabel(tr("尚未连接云端 GPU", "Cloud GPU Not Connected"))
        ob_txt.setStyleSheet("color: #F59E0B; font-size: 11px;")
        ob_lay.addWidget(ob_txt, 1)
        self.offline_quick_btn = QPushButton(tr("一键唤醒", "1-Click Wake"))
        self.offline_quick_btn.clicked.connect(self._on_offline_quick_action)
        ob_lay.addWidget(self.offline_quick_btn)
        std_lay.addWidget(self.offline_banner)

        # Progress bar when downloading/loading weights
        self.weight_prog_bar = QProgressBar()
        self.weight_prog_bar.setRange(0, 100)
        self.weight_prog_bar.setVisible(False)
        std_lay.addWidget(self.weight_prog_bar)

        # Download + Load VRAM + Eject buttons
        act_row = QHBoxLayout()
        act_row.setSpacing(6)
        self.dl_weights_btn = QPushButton(tr("下载权重", "Download"))
        self.dl_weights_btn.clicked.connect(self.vm.download_model_weights)
        act_row.addWidget(self.dl_weights_btn)

        self.load_vram_btn = set_btn_role(QPushButton(tr("加载到显存", "Load to VRAM")), "primary")
        self.load_vram_btn.clicked.connect(self.vm.load_model_to_vram)
        act_row.addWidget(self.load_vram_btn, 1)

        self.eject_vram_btn = set_btn_role(QPushButton(tr("卸载", "Unload")), "danger")
        self.eject_vram_btn.setToolTip(tr("从 GPU 显存卸载当前模型", "Unload current model from GPU VRAM"))
        self.eject_vram_btn.clicked.connect(lambda: self.vm.unload_model_from_vram(self.vm.selected_model_id))
        act_row.addWidget(self.eject_vram_btn)
        std_lay.addLayout(act_row)
        self.model_ctrl_stack.addWidget(std_w)

        # Page 1: ComfyUI Sidebar Mini Box
        cfy_w = QFrame()
        cfy_w.setObjectName("SubtlePanel")
        cfy_lay = QVBoxLayout(cfy_w)
        cfy_lay.setContentsMargins(10, 8, 10, 9)
        cfy_lay.setSpacing(6)
        st_row = QHBoxLayout()
        st_row.addWidget(QLabel(tr("画布状态", "Canvas Status")))
        self.cfy_side_status_lbl = QLabel(tr("未启动", "Stopped"))
        self.cfy_side_status_lbl.setStyleSheet("font-weight: 700; font-size: 11.5px;")
        st_row.addWidget(self.cfy_side_status_lbl, 1, Qt.AlignmentFlag.AlignRight)
        cfy_lay.addLayout(st_row)

        self.cfy_side_prog = QProgressBar()
        self.cfy_side_prog.setRange(0, 100)
        self.cfy_side_prog.setVisible(False)
        cfy_lay.addWidget(self.cfy_side_prog)

        cfy_btns = QHBoxLayout()
        cfy_btns.setSpacing(6)
        self.cfy_side_start_btn = set_btn_role(QPushButton(tr("启动 ComfyUI 画布", "Launch ComfyUI")), "primary")
        self.cfy_side_start_btn.clicked.connect(self._on_comfy_side_primary)
        cfy_btns.addWidget(self.cfy_side_start_btn, 1)
        self.cfy_side_stop_btn = set_btn_role(QPushButton(tr("停止", "Stop")), "danger")
        self.cfy_side_stop_btn.clicked.connect(self.vm.stop_comfyui)
        cfy_btns.addWidget(self.cfy_side_stop_btn)
        cfy_lay.addLayout(cfy_btns)
        self.model_ctrl_stack.addWidget(cfy_w)

        card.body.addWidget(self.model_ctrl_stack)
        return card

    def _build_sidebar_card4_params(self) -> SidebarCard:
        self.params_card = SidebarCard(tr("规格与采样参数", "Resolution & Sampling"))
        self.params_stack = AutoHeightStackedWidget()

        # Page 0: Video / VideoAudio Params
        vid_p = QWidget()
        vp_lay = QVBoxLayout(vid_p)
        vp_lay.setContentsMargins(0, 0, 0, 0)
        vp_lay.setSpacing(8)
        vp_lay.addWidget(QLabel(tr("视频分辨率", "Video Resolution")))
        self.vid_res_combo = QComboBox()
        for r in VIDEO_RESOLUTIONS:
            self.vid_res_combo.addItem(r.label, r.id)
        vr_idx = self.vid_res_combo.findData(self.vm.selected_video_res.id)
        if vr_idx >= 0:
            self.vid_res_combo.setCurrentIndex(vr_idx)
        self.vid_res_combo.currentIndexChanged.connect(self._on_vid_res_changed)
        vp_lay.addWidget(self.vid_res_combo)

        init_fr = snap_video_frames(self.vm.num_frames)
        fr_hdr = QHBoxLayout()
        fr_hdr.addWidget(QLabel(tr("视频总帧数 (4~15 秒)", "Total Frames (4-15s)")))
        self.vid_frames_lbl = QLabel(
            tr(f"{init_fr} 帧 · 约 {init_fr / 24.0:.1f} 秒", f"{init_fr} frames · ~{init_fr / 24.0:.1f}s")
        )
        self.vid_frames_lbl.setStyleSheet("font-family: Consolas, monospace; font-size: 11px; color: #60A5FA;")
        fr_hdr.addWidget(self.vid_frames_lbl, 0, Qt.AlignmentFlag.AlignRight)
        vp_lay.addLayout(fr_hdr)

        self.vid_frames_slider = QSlider(Qt.Orientation.Horizontal)
        self.vid_frames_slider.setRange(90, 362)
        self.vid_frames_slider.setValue(init_fr)
        self.vid_frames_slider.valueChanged.connect(self._on_vid_frames_changed)
        vp_lay.addWidget(self.vid_frames_slider)

        dur_chips = QHBoxLayout()
        dur_chips.setSpacing(4)
        for fr_val, d_txt in VIDEO_DURATION_PRESETS:
            b = QPushButton(d_txt)
            b.setFixedHeight(24)
            b.clicked.connect(lambda _c=False, f=fr_val: self.vid_frames_slider.setValue(f))
            dur_chips.addWidget(b)
        vp_lay.addLayout(dur_chips)

        vs_hdr = QHBoxLayout()
        vs_hdr.addWidget(QLabel(tr("采样步数", "Sampling Steps")))
        self.vid_steps_lbl = QLabel(tr(f"{self.vm.inference_steps} 步", f"{self.vm.inference_steps} steps"))
        self.vid_steps_lbl.setStyleSheet("font-family: Consolas, monospace; font-size: 11px;")
        vs_hdr.addWidget(self.vid_steps_lbl, 0, Qt.AlignmentFlag.AlignRight)
        vp_lay.addLayout(vs_hdr)
        self.vid_steps_slider = QSlider(Qt.Orientation.Horizontal)
        self.vid_steps_slider.setRange(10, 60)
        self.vid_steps_slider.setSingleStep(5)
        self.vid_steps_slider.setValue(max(10, min(60, self.vm.inference_steps)))
        self.vid_steps_slider.valueChanged.connect(self._on_vid_steps_changed)
        vp_lay.addWidget(self.vid_steps_slider)

        vp_lay.addLayout(self._build_seed_and_batch_controls(is_video=True))
        self.params_stack.addWidget(vid_p)

        # Page 1: Image Params
        img_p = QWidget()
        ip_lay = QVBoxLayout(img_p)
        ip_lay.setContentsMargins(0, 0, 0, 0)
        ip_lay.setSpacing(8)
        ip_lay.addWidget(QLabel(tr("输出画幅", "Aspect Ratio & Size")))
        self.img_res_combo = QComboBox()
        for r in image_resolutions_for(self.vm.selected_model_id):
            self.img_res_combo.addItem(r.label, r.id)
        ir_idx = self.img_res_combo.findData(self.vm.selected_image_res.id)
        if ir_idx >= 0:
            self.img_res_combo.setCurrentIndex(ir_idx)
        self.img_res_combo.currentIndexChanged.connect(self._on_img_res_changed)
        ip_lay.addWidget(self.img_res_combo)

        is_hdr = QHBoxLayout()
        is_hdr.addWidget(QLabel(tr("采样步数", "Sampling Steps")))
        self.img_steps_lbl = QLabel(tr(f"{self.vm.inference_steps} 步", f"{self.vm.inference_steps} steps"))
        self.img_steps_lbl.setStyleSheet("font-family: Consolas, monospace; font-size: 11px;")
        is_hdr.addWidget(self.img_steps_lbl, 0, Qt.AlignmentFlag.AlignRight)
        ip_lay.addLayout(is_hdr)
        self.img_steps_slider = QSlider(Qt.Orientation.Horizontal)
        self.img_steps_slider.setRange(4, 50)
        self.img_steps_slider.setValue(max(4, min(50, self.vm.inference_steps)))
        self.img_steps_slider.valueChanged.connect(self._on_img_steps_changed)
        ip_lay.addWidget(self.img_steps_slider)

        self.denoise_box = QWidget()
        dn_lay = QVBoxLayout(self.denoise_box)
        dn_lay.setContentsMargins(0, 0, 0, 0)
        dn_lay.setSpacing(4)
        dn_hdr = QHBoxLayout()
        dn_hdr.addWidget(QLabel(tr("重绘幅度 (Denoising)", "Denoising Strength")))
        self.denoise_lbl = QLabel(f"{self.vm.denoising_strength:.2f}")
        self.denoise_lbl.setStyleSheet("font-family: Consolas, monospace; font-size: 11px;")
        dn_hdr.addWidget(self.denoise_lbl, 0, Qt.AlignmentFlag.AlignRight)
        dn_lay.addLayout(dn_hdr)
        self.denoise_slider = QSlider(Qt.Orientation.Horizontal)
        self.denoise_slider.setRange(20, 100)
        self.denoise_slider.setValue(int(round(self.vm.denoising_strength * 100)))
        self.denoise_slider.valueChanged.connect(self._on_denoise_changed)
        dn_lay.addWidget(self.denoise_slider)
        ip_lay.addWidget(self.denoise_box)

        ip_lay.addLayout(self._build_seed_and_batch_controls(is_video=False))
        self.params_stack.addWidget(img_p)

        # Page 2: LLM / VLM Params
        llm_p = QWidget()
        lp_lay = QVBoxLayout(llm_p)
        lp_lay.setContentsMargins(0, 0, 0, 0)
        lp_lay.setSpacing(8)
        self.thinking_chk = QCheckBox(tr("启用深度思考链 (Thinking Mode)", "Enable Thinking Mode (CoT)"))
        self.thinking_chk.setChecked(self.vm.enable_thinking)
        self.thinking_chk.toggled.connect(self._on_thinking_toggled)
        lp_lay.addWidget(self.thinking_chk)

        self.effort_box = QWidget()
        ef_lay = QVBoxLayout(self.effort_box)
        ef_lay.setContentsMargins(0, 0, 0, 0)
        ef_lay.setSpacing(4)
        ef_lay.addWidget(QLabel(tr("思考深度 (Reasoning Effort)", "Reasoning Effort")))
        ef_btns = QHBoxLayout()
        ef_btns.setSpacing(4)
        self._effort_btns: Dict[str, QPushButton] = {}
        for ef_id, ef_lbl in (
            ("low", tr("精简", "Low")),
            ("medium", tr("均衡", "Med")),
            ("high", tr("深入", "High")),
            ("xhigh", tr("极深", "XHigh")),
        ):
            b = QPushButton(ef_lbl)
            b.setFixedHeight(26)
            b.clicked.connect(lambda _c=False, eid=ef_id: self.vm.set_reasoning_effort(eid))
            ef_btns.addWidget(b)
            self._effort_btns[ef_id] = b
        ef_lay.addLayout(ef_btns)
        lp_lay.addWidget(self.effort_box)

        ctx_hdr = QHBoxLayout()
        ctx_hdr.addWidget(QLabel(tr("上下文窗口 (最高 256K)", "Context Window (up to 256K)")))
        self.ctx_spin = QSpinBox()
        self.ctx_spin.setRange(4, 256)
        self.ctx_spin.setSingleStep(4)
        self.ctx_spin.setSuffix(" K")
        self.ctx_spin.setValue(self.vm.context_length_k)
        self.ctx_spin.valueChanged.connect(lambda v: self._on_ctx_changed(v, sync_remote=True))
        ctx_hdr.addWidget(self.ctx_spin)
        lp_lay.addLayout(ctx_hdr)

        self.ctx_slider = QSlider(Qt.Orientation.Horizontal)
        self.ctx_slider.setRange(4, 256)
        self.ctx_slider.setSingleStep(4)
        self.ctx_slider.setValue(self.vm.context_length_k)
        self.ctx_slider.sliderReleased.connect(lambda: self.vm.set_context_length_k(self.ctx_slider.value(), True))
        self.ctx_slider.valueChanged.connect(lambda v: self._on_ctx_slider_preview(v))
        lp_lay.addWidget(self.ctx_slider)

        ctx_chips = QHBoxLayout()
        ctx_chips.setSpacing(4)
        for kv in (8, 16, 32, 64, 128, 256):
            cb = QPushButton(f"{kv}K")
            cb.setFixedHeight(23)
            cb.clicked.connect(lambda _c=False, k=kv: self.vm.set_context_length_k(k, True))
            ctx_chips.addWidget(cb)
        lp_lay.addLayout(ctx_chips)

        tok_hdr = QHBoxLayout()
        tok_hdr.addWidget(QLabel(tr("最大输出长度 (含思考链)", "Max Output Tokens (incl. CoT)")))
        self.max_tok_lbl = QLabel(str(self.vm.max_new_tokens))
        self.max_tok_lbl.setStyleSheet("font-family: Consolas, monospace; font-size: 11px;")
        tok_hdr.addWidget(self.max_tok_lbl, 0, Qt.AlignmentFlag.AlignRight)
        lp_lay.addLayout(tok_hdr)
        self.max_tok_slider = QSlider(Qt.Orientation.Horizontal)
        self.max_tok_slider.setRange(1024, 65536)
        self.max_tok_slider.setSingleStep(512)
        self.max_tok_slider.setValue(self.vm.max_new_tokens)
        self.max_tok_slider.valueChanged.connect(self._on_max_tokens_changed)
        lp_lay.addWidget(self.max_tok_slider)

        tmp_hdr = QHBoxLayout()
        tmp_hdr.addWidget(QLabel(tr("采样温度 (Temperature)", "Temperature")))
        self.temp_lbl = QLabel(f"{self.vm.temperature:.2f} · Top-P {self.vm.top_p:.2f} · Top-K 20")
        self.temp_lbl.setStyleSheet("font-family: Consolas, monospace; font-size: 10.5px; color: #94A3B8;")
        tmp_hdr.addWidget(self.temp_lbl, 0, Qt.AlignmentFlag.AlignRight)
        lp_lay.addLayout(tmp_hdr)
        self.temp_slider = QSlider(Qt.Orientation.Horizontal)
        self.temp_slider.setRange(10, 150)
        self.temp_slider.setValue(int(round(self.vm.temperature * 100)))
        self.temp_slider.valueChanged.connect(self._on_temp_changed)
        lp_lay.addWidget(self.temp_slider)
        self.params_stack.addWidget(llm_p)

        # Page 3: ComfyUI Sidebar Persistence & Queue Params
        cfy_p = QWidget()
        cp_lay = QVBoxLayout(cfy_p)
        cp_lay.setContentsMargins(0, 0, 0, 0)
        cp_lay.setSpacing(8)
        self.cfy_persist_lbl = QLabel(
            tr("架构：Google Drive 自动软链持久化", "Storage: Google Drive Auto-Symlink Persistence")
        )
        self.cfy_persist_lbl.setWordWrap(True)
        self.cfy_persist_lbl.setStyleSheet("font-size: 11.5px; color: #94A3B8;")
        cp_lay.addWidget(self.cfy_persist_lbl)

        self.cfy_counts_lbl = QLabel(tr("已存节点 / 权重：0 个节点 · 0 个权重", "Saved Nodes / Weights: 0 nodes · 0 weights"))
        self.cfy_counts_lbl.setStyleSheet("font-size: 11.5px;")
        cp_lay.addWidget(self.cfy_counts_lbl)

        self.cfy_queue_lbl = QLabel(tr("画布执行队列：运行 0 · 排队 0", "Canvas Queue: 0 running · 0 queued"))
        self.cfy_queue_lbl.setStyleSheet("font-size: 11.5px; font-family: Consolas, monospace;")
        cp_lay.addWidget(self.cfy_queue_lbl)

        self.cfy_unload_chk = QCheckBox(tr("启动前释放其它常驻模型显存", "Free co-resident models VRAM before start"))
        self.cfy_unload_chk.setChecked(self.vm.comfy_unload_others_on_start)
        self.cfy_unload_chk.toggled.connect(lambda v: setattr(self.vm, "comfy_unload_others_on_start", v))
        cp_lay.addWidget(self.cfy_unload_chk)

        cfy_act = QHBoxLayout()
        cfy_act.setSpacing(6)
        sync_b = QPushButton(tr("立即同步云盘", "Sync Drive Now"))
        sync_b.clicked.connect(self.vm.sync_comfy_drive)
        free_b = QPushButton(tr("清缓存显存", "Free VRAM Cache"))
        free_b.clicked.connect(self.vm.free_comfy_vram)
        cfy_act.addWidget(sync_b)
        cfy_act.addWidget(free_b)
        cp_lay.addLayout(cfy_act)
        self.params_stack.addWidget(cfy_p)

        self.params_card.body.addWidget(self.params_stack)
        return self.params_card

    def _build_seed_and_batch_controls(self, is_video: bool) -> QVBoxLayout:
        lay = QVBoxLayout()
        lay.setSpacing(6)

        seed_row = QHBoxLayout()
        seed_row.addWidget(QLabel(tr("随机种子", "Seed")))
        spin = QSpinBox()
        spin.setRange(0, 2147483647)
        spin.setValue(self.vm.seed)
        spin.valueChanged.connect(lambda v: setattr(self.vm, "seed", int(v)))
        seed_row.addWidget(spin, 1)
        chk = QCheckBox(tr("随机", "Random"))
        chk.setChecked(self.vm.randomize_seed)
        chk.toggled.connect(lambda v: self._sync_rand_seed(v))
        seed_row.addWidget(chk)
        lay.addLayout(seed_row)

        lay.addWidget(QLabel(tr("批量连抽", "Batch Count")))
        b_row = QHBoxLayout()
        b_row.setSpacing(4)
        btns: Dict[int, QPushButton] = {}
        for n in (1, 2, 3, 4):
            if is_en():
                btn_lbl = f"{n}x"
            else:
                unit = "条" if is_video else "张"
                btn_lbl = f"{n} {unit}"
            b = QPushButton(btn_lbl)
            b.setFixedHeight(26)
            b.clicked.connect(lambda _c=False, cnt=n: self._set_batch_count(cnt))
            b_row.addWidget(b)
            btns[n] = b
        lay.addLayout(b_row)

        if is_video:
            self.vid_seed_spin = spin
            self.vid_rand_chk = chk
            self._vid_batch_btns = btns
        else:
            self.img_seed_spin = spin
            self.img_rand_chk = chk
            self._img_batch_btns = btns
        return lay


    # ═══════════════════════════════════════════════════════════════════════════
    # 3. RIGHT COLLAPSIBLE RUN LOG PANEL (352px)
    # ═══════════════════════════════════════════════════════════════════════════

    def _build_right_log_panel(self) -> QWidget:
        container = QWidget()
        container.setObjectName("RightLogContainer")
        container.setFixedWidth(352)
        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)

        hdr = QFrame()
        hdr.setObjectName("LogTopBar")
        hdr.setFixedHeight(42)
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(12, 0, 10, 0)
        hl.setSpacing(6)
        log_title = QLabel(tr("运行日志", "Run Logs"))
        log_title.setStyleSheet("font-weight: 700; font-size: 12.5px;")
        hl.addWidget(log_title)
        hl.addStretch(1)

        self.log_pill = PillBadge(tr("就绪", "Ready"), fg="#64748B", bg="rgba(148,163,184,0.16)", mono=True)
        hl.addWidget(self.log_pill)

        cp_btn = set_btn_role(QPushButton(tr("复制", "Copy")), "ghost")
        cp_btn.clicked.connect(
            lambda: self._copy_text(
                "\n".join(self.vm.live_console_lines),
                tr("已复制全部运行日志到剪贴板。", "Copied all run logs to clipboard."),
            )
        )
        clr_btn = set_btn_role(QPushButton(tr("清空", "Clear")), "ghost")
        clr_btn.clicked.connect(self.vm.clear_console_lines)
        hl.addWidget(cp_btn)
        hl.addWidget(clr_btn)
        vbox.addWidget(hdr)

        body = QWidget()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(12, 12, 12, 12)
        bl.setSpacing(10)

        # Status Summary Box
        st_box = QFrame()
        st_box.setObjectName("SidebarCard")
        st_lay = QVBoxLayout(st_box)
        st_lay.setContentsMargins(10, 8, 10, 8)
        st_lay.setSpacing(6)
        self.log_status_lbl = QLabel(self.vm.status_message)
        self.log_status_lbl.setWordWrap(True)
        self.log_status_lbl.setStyleSheet("font-size: 11.5px; line-height: 1.35;")
        st_lay.addWidget(self.log_status_lbl)
        self.log_task_prog = QProgressBar()
        self.log_task_prog.setRange(0, 100)
        self.log_task_prog.setVisible(False)
        st_lay.addWidget(self.log_task_prog)
        bl.addWidget(st_box)

        # Theme-Aware Monospace Terminal
        self.terminal_view = QTextBrowser()
        self.terminal_view.setObjectName("LogTerminalView")
        self.terminal_view.setOpenExternalLinks(False)
        bl.addWidget(self.terminal_view, 1)

        vbox.addWidget(body, 1)
        return container

    # ═══════════════════════════════════════════════════════════════════════════
    # UI REFRESH & SIGNAL HANDLERS
    # ═══════════════════════════════════════════════════════════════════════════

    def open_onboarding_guide(self, step: int = 0) -> None:
        dlg = ColabGuideDialog(self.vm, initial_step=step, parent=self)
        dlg.exec()


    def _toggle_right_log_panel(self) -> None:
        self._show_right_log = not self._show_right_log
        self.right_log_panel.setVisible(self._show_right_log)

    def _submit_oauth_code(self) -> None:
        self.vm.submit_google_oauth_code(self.oauth_input.text())
        self.oauth_input.clear()

    def _cancel_oauth_code(self) -> None:
        self.vm.show_oauth_code_input = False
        self.oauth_input.clear()
        self._refresh_all_state()

    def _on_gpu_combo_changed(self, idx: int) -> None:
        if self._syncing_ui:
            return
        val = self.gpu_combo.itemData(idx)
        if val:
            self.vm.set_wake_gpu_choice(str(val))

    def _on_connect_clicked(self) -> None:
        self.vm.set_colab_server_url(self.url_input.text())
        self.vm.check_colab_status(silent=False)

    def _on_idle_combo_changed(self, idx: int) -> None:
        if self._syncing_ui:
            return
        mins = self.idle_combo.itemData(idx)
        if mins is not None:
            self.vm.update_idle_timeout_config(int(mins))

    def _confirm_release_all_vms(self) -> None:
        ans = QMessageBox.question(
            self,
            tr("释放所有 Colab 实例？", "Release All Colab Runtimes?"),
            tr(
                "账号下所有运行中的 Colab GPU 实例将被销毁，计费立即归零。\n确认立即释放吗？",
                "All active Colab GPU runtimes on your account will be terminated and billing will stop immediately.\nConfirm release now?",
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if ans == QMessageBox.StandardButton.Yes:
            self.vm.disconnect_remote_colab()

    def _on_hf_token_edited(self) -> None:
        self.vm.hf_token = self.hf_token_input.text().strip()
        self.vm._save_setting("hfToken", self.vm.hf_token)

    def _on_offline_quick_action(self) -> None:
        if self.vm.cli_logged_in:
            self.vm.wake_colab_headless()
        elif self.vm.normalized_base_url:
            self.vm.check_colab_status(silent=False)
        else:
            self.open_onboarding_guide(0)

    def _on_comfy_side_primary(self) -> None:
        if self.vm.comfy_running and self.vm.comfy_public_url:
            webbrowser.open(self.vm.comfy_public_url)
        else:
            self.vm.start_comfyui(force_restart=False, auto_open_browser=True)

    def _open_comfy_browser(self) -> None:
        if self.vm.comfy_public_url:
            webbrowser.open(self.vm.comfy_public_url)

    def _copy_comfy_url(self) -> None:
        if self.vm.comfy_public_url:
            self._copy_text(
                self.vm.comfy_public_url,
                tr("已复制 ComfyUI 公网画布地址到剪贴板。", "Copied ComfyUI public canvas URL to clipboard."),
            )

    def _on_comfy_custom_dl(self) -> None:
        sf = str(self.cfy_subfolder_combo.currentData() or "diffusion_models")
        self.vm.download_comfy_weight(self.cfy_src_input.text(), self.cfy_fname_input.text(), sf)

    def _on_vid_res_changed(self, idx: int) -> None:
        if 0 <= idx < len(VIDEO_RESOLUTIONS):
            self.vm.selected_video_res = VIDEO_RESOLUTIONS[idx]

    def _on_vid_frames_changed(self, val: int) -> None:
        snapped = snap_video_frames(val)
        self.vm.num_frames = snapped
        self.vid_frames_lbl.setText(
            tr(f"{snapped} 帧 · 约 {snapped / 24.0:.1f} 秒", f"{snapped} frames · ~{snapped / 24.0:.1f}s")
        )

    def _on_vid_steps_changed(self, val: int) -> None:
        snapped = max(10, min(60, int(round(val / 5.0)) * 5))
        self.vm.inference_steps = snapped
        self.vid_steps_lbl.setText(tr(f"{snapped} 步", f"{snapped} steps"))

    def _sync_img_res_options(self, model_id: str) -> None:
        """切换模型时把画幅下拉刷新为对应分辨率表（H3-Image 使用 4K 画幅）"""
        if not hasattr(self, "img_res_combo"):
            return
        wanted = image_resolutions_for(model_id)
        current = [self.img_res_combo.itemData(i) for i in range(self.img_res_combo.count())]
        if current == [r.id for r in wanted]:
            return
        self.img_res_combo.blockSignals(True)
        self.img_res_combo.clear()
        for r in wanted:
            self.img_res_combo.addItem(r.label, r.id)
        idx = self.img_res_combo.findData(self.vm.selected_image_res.id)
        if idx >= 0:
            self.img_res_combo.setCurrentIndex(idx)
        self.img_res_combo.blockSignals(False)

    def _on_img_res_changed(self, idx: int) -> None:
        if self._syncing_ui:
            return
        opts = image_resolutions_for(self.vm.selected_model_id)
        if 0 <= idx < len(opts):
            self.vm.selected_image_res = opts[idx]

    def _on_img_steps_changed(self, val: int) -> None:
        self.vm.inference_steps = int(val)
        self.img_steps_lbl.setText(tr(f"{val} 步", f"{val} steps"))

    def _on_denoise_changed(self, val: int) -> None:
        d = val / 100.0
        self.vm.denoising_strength = d
        self.denoise_lbl.setText(f"{d:.2f}")

    def _sync_rand_seed(self, checked: bool) -> None:
        self.vm.randomize_seed = checked
        if not self._syncing_ui:
            self._syncing_ui = True
            self.vid_rand_chk.setChecked(checked)
            self.img_rand_chk.setChecked(checked)
            self._syncing_ui = False

    def _set_batch_count(self, cnt: int) -> None:
        self.vm.batch_count = cnt
        self._refresh_batch_buttons()

    def _on_thinking_toggled(self, checked: bool) -> None:
        if self._syncing_ui:
            return
        self.vm.set_enable_thinking(checked)

    def _on_ctx_slider_preview(self, val: int) -> None:
        if self._syncing_ui:
            return
        snapped = max(4, min(256, int(round(val / 4.0)) * 4))
        self._syncing_ui = True
        self.ctx_spin.setValue(snapped)
        self._syncing_ui = False
        self.vm.set_context_length_k(snapped, sync_remote=False)

    def _on_ctx_changed(self, val: int, sync_remote: bool) -> None:
        if self._syncing_ui:
            return
        self._syncing_ui = True
        self.ctx_slider.setValue(val)
        self._syncing_ui = False
        self.vm.set_context_length_k(val, sync_remote=sync_remote)

    def _on_max_tokens_changed(self, val: int) -> None:
        snapped = max(1024, min(65536, int(round(val / 512.0)) * 512))
        self.vm.max_new_tokens = snapped
        self.max_tok_lbl.setText(str(snapped))

    def _on_temp_changed(self, val: int) -> None:
        t = val / 100.0
        self.vm.temperature = t
        self.temp_lbl.setText(f"{t:.2f} · Top-P {self.vm.top_p:.2f} · Top-K 20")

    def _on_vid_visual_edited(self) -> None:
        if not self._syncing_ui:
            self.vm.visual_prompt = self.vid_visual_edit.toPlainText()

    def _on_img_visual_edited(self) -> None:
        if not self._syncing_ui:
            self.vm.visual_prompt = self.img_visual_edit.toPlainText()

    def _on_llm_prompt_edited(self) -> None:
        if not self._syncing_ui:
            self.vm.visual_prompt = self.llm_prompt_edit.toPlainText()

    def _clear_chat_history(self) -> None:
        self.vm.chat_history.clear()
        self._refresh_chat_conversation()

    def _sync_api_key_clicked(self) -> None:
        self.vm.sync_api_key_to_colab(self.api_key_input.text())
        self.vm.status_message = tr(
            "API 密钥已同步更新至 Colab 云端网关。",
            "API Key synced to cloud Colab gateway.",
        )
        self._refresh_all_state()

    def _regen_api_key_clicked(self) -> None:
        self.vm.regenerate_api_key()
        self.api_key_input.setText(self.vm.api_access_key)
        self._refresh_all_state()

    def _copy_text(self, text: str, tip: str) -> None:
        cb = QGuiApplication.clipboard()
        if cb is not None:
            cb.setText(text)
        self.vm.status_message = tip
        self.log_status_lbl.setText(tip)

    def _trigger_generate(self) -> None:
        spec = self.vm.active_model_spec
        if spec.modality == ModelModality.COMFY_UI:
            return
        if spec.modality == ModelModality.LLM_VLM and self.vm.task_mode_id == "api":
            return

        first_b64: Optional[str] = None
        last_b64: Optional[str] = None
        if spec.modality in (ModelModality.VIDEO_AUDIO, ModelModality.VIDEO):
            self.vm.visual_prompt = self.vid_visual_edit.toPlainText()
            if self.vm.task_mode_id == "fl2va":
                first_b64 = self.video_first_well.to_jpeg_base64()
                last_b64 = self.video_last_well.to_jpeg_base64()
        elif spec.modality == ModelModality.LLM_VLM:
            self.vm.visual_prompt = self.llm_prompt_edit.toPlainText()
            if self.vm.task_mode_id == "vlm":
                first_b64 = self.vlm_img1_well.to_jpeg_base64()
                last_b64 = self.vlm_img2_well.to_jpeg_base64()
        elif spec.modality == ModelModality.IMAGE:
            self.vm.visual_prompt = self.img_visual_edit.toPlainText()
            if self.vm.task_mode_id == "i2i_edit":
                first_b64 = self.img_ref1_well.to_jpeg_base64()
                if spec.id == "qwen_image_21":
                    last_b64 = self.img_ref2_well.to_jpeg_base64()

        self.vm.start_generation(first_frame_b64=first_b64, last_frame_b64=last_b64)
        if spec.modality == ModelModality.LLM_VLM and not self.vm.visual_prompt:
            self._syncing_ui = True
            self.llm_prompt_edit.clear()
            self._syncing_ui = False

    # ─── Master State Refresh ────────────────────────────────────────────────

    def _refresh_all_state(self) -> None:
        self._syncing_ui = True
        pal = self.palette_obj
        spec = self.vm.active_model_spec
        self._sync_img_res_options(spec.id)

        # 1. Connection & Account
        if self.vm.is_connected:
            self.conn_badge.setText(tr("在线", "Online"))
            self.conn_badge.set_badge_style("#10B981", "rgba(16,185,129,0.16)")
            self.hw_dot.set_color("#10B981")
            self.ws_top_dot.set_color("#10B981")
            self.connect_btn.setText(tr("刷新", "Refresh"))
            top_text = tr(
                f"{self.vm.gpu_name} · 显存 {self.vm.vram_used_gb:.1f}/{self.vm.vram_total_gb:.0f}G · "
                f"内存 {self.vm.ram_used_gb:.1f}/{self.vm.ram_total_gb:.0f}G · "
                f"磁盘可用 {self.vm.disk_free_gb:.0f}/{self.vm.disk_total_gb:.0f}G",
                f"{self.vm.gpu_name} · VRAM {self.vm.vram_used_gb:.1f}/{self.vm.vram_total_gb:.0f}G · "
                f"RAM {self.vm.ram_used_gb:.1f}/{self.vm.ram_total_gb:.0f}G · "
                f"Disk Free {self.vm.disk_free_gb:.0f}/{self.vm.disk_total_gb:.0f}G",
            )
            self.ws_top_summary.setToolTip(top_text)
            top_w = max(220, self.ws_top_summary.width() or 360)
            self.ws_top_summary.setText(
                QFontMetrics(self.ws_top_summary.font()).elidedText(top_text, Qt.TextElideMode.ElideRight, top_w)
            )
        else:
            self.conn_badge.setText(tr("离线", "Offline"))
            self.conn_badge.set_badge_style("#94A3B8", "rgba(148,163,184,0.16)")
            self.hw_dot.set_color("#64748B")
            self.ws_top_dot.set_color("#64748B")
            self.connect_btn.setText(tr("连接", "Connect"))
            self.ws_top_summary.setToolTip("")
            self.ws_top_summary.setText(tr("开源多模型云端工作台", "Open Multi-Model Cloud AI Studio"))

        acct_txt = self.vm.display_account_label
        self.account_val_lbl.setToolTip(acct_txt)
        acct_w = max(90, (self.account_val_lbl.width() or 120) - 4)
        self.account_val_lbl.setText(
            QFontMetrics(self.account_val_lbl.font()).elidedText(acct_txt, Qt.TextElideMode.ElideMiddle, acct_w)
        )
        self.bind_btn.setVisible(not self.vm.cli_logged_in)
        self.acc_refresh_btn.setVisible(self.vm.cli_logged_in)
        self.acc_menu_btn.setVisible(self.vm.cli_logged_in)
        self.oauth_box.setVisible(self.vm.show_oauth_code_input)
        self.wake_row_widget.setVisible(self.vm.cli_logged_in)

        g_idx = self.gpu_combo.findData(self.vm.wake_gpu_choice)
        if g_idx >= 0:
            self.gpu_combo.setCurrentIndex(g_idx)
        self.wake_btn.setEnabled(not self.vm.is_waking_colab)
        self.wake_btn.setText(
            tr("唤醒部署中...", "Deploying...") if self.vm.is_waking_colab else tr("唤醒实例并部署", "Wake & Deploy")
        )

        if not self.url_input.hasFocus():
            self.url_input.setText(self.vm.colab_server_url)
        if self.admin_input.text() != self.vm.admin_password:
            self.admin_input.setText(self.vm.admin_password)
        self.url_input.setEchoMode(
            QLineEdit.EchoMode.Password if self.vm.mask_server_url else QLineEdit.EchoMode.Normal
        )
        self.url_input.setPlaceholderText(
            tr("已开启打码保护", "Privacy mask enabled") if self.vm.mask_server_url else "https://xxxx.gradio.live"
        )
        self.mask_eye_btn.setText(tr("已打码", "Masked") if self.vm.mask_server_url else tr("打码", "Mask"))

        self.hw_gpu_lbl.setText(self.vm.gpu_name)
        self.drive_pill.setVisible(self.vm.drive_persisted)

        # 2. CU Ledger & Idle Timeout
        self.cu_title_lbl.setText(
            tr("账户余额", "CU Balance") if self.vm.official_cu_balance is not None else tr("预计余额", "Est. Balance")
        )
        self.cu_val_lbl.setText(f"{self.vm.display_remaining_cu:.2f} CU")
        burn = self.vm.display_burn_rate
        self.burn_val_lbl.setText(f"{burn:.2f} CU/h")
        self.burn_val_lbl.setStyleSheet(
            f"font-size: 12.5px; font-weight: 700; font-family: Consolas, monospace; "
            f"color: {'#F59E0B' if burn > 0 else pal.text_primary};"
        )
        self.uptime_val_lbl.setText(format_uptime_hms(self.vm.uptime_seconds))

        idle_idx = self.idle_combo.findData(self.vm.idle_timeout_minutes)
        if idle_idx >= 0:
            self.idle_combo.setCurrentIndex(idle_idx)
        if self.vm.idle_timeout_minutes <= 0:
            self.idle_countdown_lbl.setText(
                tr(
                    "已关闭闲置自动休眠（请记得用完手动释放实例）",
                    "Idle auto-release is Off (remember to release runtime manually)",
                )
            )
        elif self.vm.is_connected:
            rem = max(0, self.vm.idle_remaining_seconds)
            self.idle_countdown_lbl.setText(
                tr(
                    f"{rem // 60}分{rem % 60:02d}秒无操作后自动释放实例",
                    f"Auto-release in {rem // 60}m {rem % 60:02d}s if idle",
                )
            )
        else:
            self.idle_countdown_lbl.setText(
                tr(
                    f"连接后超过 {self.vm.idle_timeout_minutes} 分钟闲置将自动释放实例",
                    f"Auto-release after {self.vm.idle_timeout_minutes} min of inactivity once connected",
                )
            )

        if self.vm.active_vm_count > 0:
            self.release_all_btn.setText(
                tr(
                    f"释放全部实例 ({self.vm.active_vm_count} 台运行中)",
                    f"Release All Runtimes ({self.vm.active_vm_count} Active)",
                )
            )
        else:
            self.release_all_btn.setText(tr("释放全部实例", "Release All Runtimes"))
        self.release_all_btn.setEnabled(not self.vm.is_releasing_colab)

        # 3. Model Center Cards & Co-Residency
        all_models = self.vm.all_available_models
        blue_badge_fg = "#60A5FA" if pal.is_dark else "#2563EB"
        if len(self.vm.loaded_model_ids) > 1:
            self.model_center_badge.setText(
                tr(f"共驻 {len(self.vm.loaded_model_ids)} 模型", f"{len(self.vm.loaded_model_ids)} Co-Resident")
            )
            self.model_center_badge.set_badge_style("#059669", "rgba(16,185,129,0.14)")
        else:
            self.model_center_badge.setText(f"HF {len(all_models)}")
            self.model_center_badge.set_badge_style(blue_badge_fg, "rgba(59,130,246,0.14)")

        expected_ids = [m.id for m in all_models]
        if list(self._model_card_btns.keys()) != expected_ids:
            while self.model_buttons_lay.count():
                item = self.model_buttons_lay.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            self._model_card_btns.clear()
            for spec_item in all_models:
                btn = QPushButton()
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setMinimumHeight(46)
                btn.clicked.connect(lambda _c=False, mid=spec_item.id: self.vm.select_model(mid))
                if spec_item.is_custom:
                    btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
                    btn.customContextMenuRequested.connect(
                        lambda pos, b=btn, mid=spec_item.id: self._show_custom_model_menu(b, pos, mid)
                    )
                self.model_buttons_lay.addWidget(btn)
                self._model_card_btns[spec_item.id] = btn

        for m_spec in all_models:
            btn = self._model_card_btns[m_spec.id]
            is_sel = m_spec.id == self.vm.selected_model_id
            is_loaded = m_spec.id in self.vm.loaded_model_ids or (
                m_spec.id == "comfyui_studio" and self.vm.comfy_running
            )
            status_tag = tr("  [显存就绪]", "  [VRAM Ready]") if is_loaded else ""
            btn.setText(f"{m_spec.name}{status_tag}\n{m_spec.badge}")
            if is_sel:
                btn.setStyleSheet(
                    f"QPushButton {{ text-align: left; padding: 7px 10px; font-size: 11.5px; font-weight: 700; "
                    f"background-color: {pal.selected_card_bg}; border: 1.5px solid {pal.selected_card_border}; border-radius: 8px; }}"
                )
            else:
                btn.setStyleSheet(
                    f"QPushButton {{ text-align: left; padding: 7px 10px; font-size: 11.5px; "
                    f"background-color: {pal.input_fill}; border: 1px solid {pal.card_border}; border-radius: 8px; }}"
                    f"QPushButton:hover {{ border-color: {pal.accent_blue}; }}"
                )
        self.add_custom_model_btn.setStyleSheet(
            f"QPushButton {{ text-align: center; padding: 6px 10px; font-size: 11px; font-weight: 700; "
            f"color: {blue_badge_fg}; background-color: rgba(59,130,246,0.08); "
            f"border: 1px dashed {pal.accent_blue}; border-radius: 8px; }}"
        )

        self._rebuild_coresident_strip()

        if spec.modality == ModelModality.COMFY_UI:
            self.model_ctrl_stack.setCurrentIndex(1)
            if self.vm.comfy_running:
                self.cfy_side_status_lbl.setText(tr("在线 (端口 8188)", "Online (Port 8188)"))
                self.cfy_side_status_lbl.setStyleSheet("color: #10B981; font-weight: 700; font-size: 11.5px;")
                self.cfy_side_start_btn.setText(tr("打开画布", "Open Canvas"))
            elif self.vm.comfy_starting:
                self.cfy_side_status_lbl.setText(tr("部署启动中...", "Deploying..."))
                self.cfy_side_status_lbl.setStyleSheet("color: #F59E0B; font-weight: 700; font-size: 11.5px;")
                self.cfy_side_start_btn.setText(tr("正在启动...", "Starting..."))
            else:
                self.cfy_side_status_lbl.setText(tr("未启动", "Stopped"))
                self.cfy_side_status_lbl.setStyleSheet("color: #94A3B8; font-weight: 700; font-size: 11.5px;")
                self.cfy_side_start_btn.setText(tr("启动 ComfyUI 画布", "Launch ComfyUI"))
            self.cfy_side_stop_btn.setEnabled(self.vm.comfy_running)
            cfy_busy = (
                self.vm.comfy_starting or self.vm.comfy_downloading_weight or bool(self.vm.comfy_installing_pack_id)
            )
            self.cfy_side_prog.setVisible(cfy_busy)
            self.cfy_side_prog.setValue(int(self.vm.comfy_progress * 100))
        else:
            self.model_ctrl_stack.setCurrentIndex(0)
            self.repo_val_lbl.setText(spec.repo_id)
            if self.vm.all_downloaded:
                sz = self.vm.total_size_gb if self.vm.total_size_gb > 0 else spec.approx_size_gb
                self.weight_status_lbl.setText(
                    tr(
                        f"已就绪 {self.vm.downloaded_count}/{self.vm.total_count} ({sz:.1f} GB)",
                        f"Ready {self.vm.downloaded_count}/{self.vm.total_count} ({sz:.1f} GB)",
                    )
                )
                self.weight_status_lbl.setStyleSheet("color: #10B981; font-size: 11.5px; font-weight: 700;")
            else:
                self.weight_status_lbl.setText(
                    tr(
                        f"{self.vm.downloaded_count}/{self.vm.total_count} 个分片",
                        f"{self.vm.downloaded_count}/{self.vm.total_count} shards",
                    )
                )
                self.weight_status_lbl.setStyleSheet("color: #F59E0B; font-size: 11.5px; font-weight: 600;")

            self._rebuild_shards_list()

            # KV mismatch check for Qwen GGUF
            loaded_k = self.vm.loaded_context_length // 1024
            if (
                spec.id == "qwen38_27b_gguf"
                and self.vm.is_selected_model_loaded_in_vram
                and loaded_k > 0
                and loaded_k != self.vm.context_length_k
            ):
                self.kv_mismatch_lbl.setText(
                    tr(
                        f"当前显存 KV 为 {loaded_k}K，点「重新装载」切换至 {self.vm.context_length_k}K",
                        f"Loaded KV is {loaded_k}K — click 'Reload VRAM' to apply {self.vm.context_length_k}K",
                    )
                )
                self.kv_mismatch_lbl.setVisible(True)
            else:
                self.kv_mismatch_lbl.setVisible(False)

            self.offline_banner.setVisible(not self.vm.is_connected)
            self.offline_quick_btn.setText(
                tr("一键唤醒", "1-Click Wake") if self.vm.cli_logged_in else tr("重连", "Reconnect")
            )

            busy_w = self.vm.is_downloading_weights or self.vm.is_loading_model
            self.weight_prog_bar.setVisible(busy_w)
            self.weight_prog_bar.setValue(int(self.vm.model_task_progress * 100))

            self.dl_weights_btn.setText(
                tr("校验权重", "Verify") if self.vm.all_downloaded else tr("下载权重", "Download")
            )
            self.dl_weights_btn.setEnabled(self.vm.is_connected and not busy_w)

            self.load_vram_btn.setText(
                tr("重新装载", "Reload VRAM")
                if self.vm.is_selected_model_loaded_in_vram
                else tr("加载到显存", "Load to VRAM")
            )
            self.load_vram_btn.setEnabled(self.vm.is_connected and self.vm.all_downloaded and not busy_w)
            self.eject_vram_btn.setVisible(self.vm.is_selected_model_loaded_in_vram)

        # 4. Adaptive Params Card
        if spec.modality in (ModelModality.VIDEO_AUDIO, ModelModality.VIDEO):
            self.params_card.title_label.setText(tr("规格与采样参数", "Resolution & Sampling"))
            self.params_stack.setCurrentIndex(0)
            self.vid_steps_slider.setValue(self.vm.inference_steps)
            self.vid_steps_lbl.setText(tr(f"{self.vm.inference_steps} 步", f"{self.vm.inference_steps} steps"))
        elif spec.modality == ModelModality.IMAGE:
            self.params_card.title_label.setText(tr("规格与采样参数", "Resolution & Sampling"))
            self.params_stack.setCurrentIndex(1)
            self.img_steps_slider.setValue(self.vm.inference_steps)
            self.img_steps_lbl.setText(tr(f"{self.vm.inference_steps} 步", f"{self.vm.inference_steps} steps"))
            self.denoise_box.setVisible(spec.id == "z_image_turbo" and self.vm.task_mode_id == "i2i_edit")
        elif spec.modality == ModelModality.LLM_VLM:
            self.params_card.title_label.setText(tr("推理与对话参数", "Reasoning & Sampling"))
            self.params_stack.setCurrentIndex(2)
            self.thinking_chk.setChecked(self.vm.enable_thinking)
            self.effort_box.setVisible(self.vm.enable_thinking)
            for ef_id, b in self._effort_btns.items():
                if ef_id == self.vm.reasoning_effort:
                    b.setStyleSheet(
                        f"background-color: {pal.accent_blue}; color: #FFFFFF; font-weight: 700; border-radius: 5px;"
                    )
                else:
                    b.setStyleSheet("")
            self.ctx_spin.setValue(self.vm.context_length_k)
            self.ctx_slider.setValue(self.vm.context_length_k)
            self.temp_slider.setValue(int(round(self.vm.temperature * 100)))
            self.temp_lbl.setText(f"{self.vm.temperature:.2f} · Top-P {self.vm.top_p:.2f} · Top-K 20")
        elif spec.modality == ModelModality.COMFY_UI:
            self.params_card.title_label.setText(tr("ComfyUI 云盘持久化与控制", "ComfyUI Persistence & Control"))
            self.params_stack.setCurrentIndex(3)
            self.cfy_persist_lbl.setText(
                tr(f"架构：{self.vm.comfy_persistence_label}", f"Storage: {self.vm.comfy_persistence_label}")
            )
            self.cfy_counts_lbl.setText(
                tr(
                    f"已存节点 / 权重：{self.vm.comfy_custom_nodes_count} 个节点 · {self.vm.comfy_models_count} 个权重",
                    f"Saved Nodes / Weights: {self.vm.comfy_custom_nodes_count} nodes · {self.vm.comfy_models_count} weights",
                )
            )
            self.cfy_queue_lbl.setText(
                tr(
                    f"画布执行队列：运行 {self.vm.comfy_queue_running} · 排队 {self.vm.comfy_queue_pending}",
                    f"Canvas Queue: {self.vm.comfy_queue_running} running · {self.vm.comfy_queue_pending} queued",
                )
            )

        self._refresh_batch_buttons()

        # 5. Center Mode Switcher & Preset Menu
        self._rebuild_preset_menu()
        self.ms_title_lbl.setText(spec.name)
        self.ms_repo_pill.setText(spec.repo_id)
        self.ms_summary_lbl.setText(spec.summary)

        if len(self.vm.loaded_model_ids) > 1:
            self.ms_coresident_pill.setText(
                tr(
                    f"{len(self.vm.loaded_model_ids)} 模型显存共驻",
                    f"{len(self.vm.loaded_model_ids)} Models Co-Resident",
                )
            )
            self.ms_coresident_pill.setVisible(True)
        else:
            self.ms_coresident_pill.setVisible(False)

        ready_vram = self.vm.is_selected_model_loaded_in_vram or (
            spec.modality == ModelModality.COMFY_UI and self.vm.comfy_running
        )
        if ready_vram:
            self.ms_vram_pill.setText(tr("显存已就绪", "VRAM Ready"))
            self.ms_vram_pill.set_badge_style("#10B981", "rgba(16,185,129,0.16)")
        else:
            self.ms_vram_pill.setText(tr("待加载至显存", "Not Loaded in VRAM"))
            self.ms_vram_pill.set_badge_style("#F59E0B", "rgba(245,158,11,0.16)")

        self._rebuild_mode_radio_cards()

        # 6. Active Modality Studio Routing
        if spec.modality in (ModelModality.VIDEO_AUDIO, ModelModality.VIDEO):
            self.studio_stack.setCurrentIndex(0)
            self.video_frames_card.setVisible(self.vm.task_mode_id == "fl2va")
            self.shared_media_split.setVisible(True)
            self.right_gallery_stack.setCurrentIndex(0)
            self._update_gen_bar(
                "vid",
                tr(
                    f"连续生成 {self.vm.batch_count} 条全模态音视频 (Ctrl+Enter)",
                    f"Generate {self.vm.batch_count}x Audio-Video Clips (Ctrl+Enter)",
                )
                if self.vm.batch_count > 1
                else tr("开始生成音视频 (Ctrl+Enter)", "Generate Audio-Video (Ctrl+Enter)"),
            )
        elif spec.modality == ModelModality.COMFY_UI:
            self.studio_stack.setCurrentIndex(1)
            self.shared_media_split.setVisible(True)
            self.right_gallery_stack.setCurrentIndex(1)
            self._refresh_comfyui_studio_cards()
        elif spec.modality == ModelModality.LLM_VLM:
            self.studio_stack.setCurrentIndex(2)
            self.shared_media_split.setVisible(False)
            if self.vm.task_mode_id == "api":
                self.qwen_mode_stack.setCurrentIndex(1)
                self._refresh_api_gateway_cards()
            else:
                self.qwen_mode_stack.setCurrentIndex(0)
                self.vlm_images_card.setVisible(self.vm.task_mode_id == "vlm")
                self._update_gen_bar("llm", tr("发送并开始深度推理 (Ctrl+Enter)", "Send & Start Deep Reasoning (Ctrl+Enter)"))
        elif spec.modality == ModelModality.IMAGE:
            self.studio_stack.setCurrentIndex(3)
            self.img_refs_card.setVisible(self.vm.task_mode_id == "i2i_edit")
            self.img_ref2_well.setVisible(spec.id == "qwen_image_21")
            self.shared_media_split.setVisible(True)
            self.right_gallery_stack.setCurrentIndex(0)
            self._update_gen_bar(
                "img",
                tr(
                    f"连续生成 {self.vm.batch_count} 张高清图像 (Ctrl+Enter)",
                    f"Generate {self.vm.batch_count}x HD Images (Ctrl+Enter)",
                )
                if self.vm.batch_count > 1
                else tr("开始生成图像 (Ctrl+Enter)", "Generate Image (Ctrl+Enter)"),
            )

        # 7. Right Log Panel Header & Status
        self.log_status_lbl.setText(self.vm.status_message)
        any_busy = (
            self.vm.is_generating
            or self.vm.is_downloading_weights
            or self.vm.is_loading_model
            or self.vm.is_waking_colab
            or self.vm.comfy_starting
            or self.vm.comfy_downloading_weight
            or bool(self.vm.comfy_installing_pack_id)
        )
        if any_busy:
            self.log_pill.setText(tr("实时传输", "Streaming"))
            self.log_pill.set_badge_style("#059669", "rgba(16,185,129,0.14)")
        else:
            self.log_pill.setText(tr(f"{len(self.vm.live_console_lines)} 行", f"{len(self.vm.live_console_lines)} lines"))
            self.log_pill.set_badge_style("#64748B", "rgba(148,163,184,0.16)")

        if self.vm.is_generating:
            self.log_task_prog.setVisible(True)
            self.log_task_prog.setValue(int(self.vm.progress_value * 100))
        elif self.vm.is_downloading_weights or self.vm.is_loading_model:
            self.log_task_prog.setVisible(True)
            self.log_task_prog.setValue(int(self.vm.model_task_progress * 100))
        else:
            self.log_task_prog.setVisible(False)

        self._syncing_ui = False

    def _update_gen_bar(self, prefix: str, idle_label: str) -> None:
        gen_btn: QPushButton = getattr(self, f"{prefix}_gen_btn")
        stop_btn: QPushButton = getattr(self, f"{prefix}_stop_btn")
        prog: QProgressBar = getattr(self, f"{prefix}_prog_bar")
        if self.vm.is_generating:
            pct = int(self.vm.progress_value * 100)
            gen_btn.setText(
                tr(
                    f"正在云端推理中... {pct}% · 已用时 {format_duration(self.vm.current_job_elapsed)}",
                    f"Inferring on Cloud... {pct}% · Elapsed {format_duration(self.vm.current_job_elapsed)}",
                )
            )
            gen_btn.setEnabled(False)
            stop_btn.setEnabled(True)
            prog.setVisible(True)
            prog.setValue(pct)
        else:
            gen_btn.setText(idle_label)
            gen_btn.setEnabled(True)
            stop_btn.setEnabled(False)
            prog.setVisible(False)

    def _refresh_batch_buttons(self) -> None:
        pal = self.palette_obj
        for btns in (self._vid_batch_btns, self._img_batch_btns):
            for n, b in btns.items():
                if n == self.vm.batch_count:
                    b.setStyleSheet(
                        f"background-color: {pal.accent_blue}; color: #FFFFFF; font-weight: 700; border-radius: 5px;"
                    )
                else:
                    b.setStyleSheet("")

    def _rebuild_preset_menu(self) -> None:
        self.preset_menu.clear()
        mod = self.vm.active_model_spec.modality
        matching = [t for t in PRESET_TEMPLATES if t.modality == mod]
        if not matching:
            matching = PRESET_TEMPLATES
        for tpl in matching:
            act = QAction(tpl.title, self)
            act.triggered.connect(lambda _c=False, tp=tpl: self._apply_preset_template(tp))
            self.preset_menu.addAction(act)

    def _apply_preset_template(self, tpl) -> None:
        self._syncing_ui = True
        self.vm.visual_prompt = tpl.visual
        self.vm.soundscape_prompt = tpl.soundscape
        self.vm.music_prompt = tpl.music
        self.vid_visual_edit.setPlainText(tpl.visual)
        self.vid_sound_edit.setPlainText(tpl.soundscape)
        self.vid_music_edit.setPlainText(tpl.music)
        self.img_visual_edit.setPlainText(tpl.visual)
        self.llm_prompt_edit.setPlainText(tpl.visual)
        self._syncing_ui = False
        self.vm.status_message = tr(f"已填入示例提示词：{tpl.title}", f"Applied preset template: {tpl.title}")
        self.log_status_lbl.setText(self.vm.status_message)

    def _rebuild_coresident_strip(self) -> None:
        sig = (
            get_lang(),
            tuple(self.vm.loaded_model_ids),
            tuple((d.id, d.name, d.vram_gb) for d in self.vm.loaded_models_detail),
        )
        if sig == self._last_coresident_sig:
            return
        self._last_coresident_sig = sig
        self._clear_layout(self.coresident_lay)

        details = self.vm.loaded_models_detail
        if not details and not self.vm.loaded_model_ids:
            self.coresident_box.setVisible(False)
            return

        self.coresident_box.setVisible(True)
        hdr = QHBoxLayout()
        lbl = QLabel(
            tr(
                f"显存常驻模型 ({len(self.vm.loaded_model_ids)})",
                f"Co-Resident in VRAM ({len(self.vm.loaded_model_ids)})",
            )
        )
        lbl.setStyleSheet("font-size: 11px; font-weight: 700; color: #10B981;")
        hdr.addWidget(lbl, 1)
        if len(self.vm.loaded_model_ids) >= 2:
            ua = set_btn_role(QPushButton(tr("全部卸载", "Unload All")), "ghost")
            ua.setStyleSheet("font-size: 10.5px; color: #F87171;")
            ua.clicked.connect(lambda: self.vm.unload_model_from_vram("all"))
            hdr.addWidget(ua)
        self.coresident_lay.addLayout(hdr)

        items_to_show = (
            [(d.id, d.name, f"{d.vram_gb:.1f}G" if d.vram_gb else "") for d in details]
            if details
            else [(mid, MODEL_SPEC_MAP[mid].name if mid in MODEL_SPEC_MAP else mid, "") for mid in self.vm.loaded_model_ids]
        )
        for mid, mname, vtxt in items_to_show:
            r = QHBoxLayout()
            r.setSpacing(4)
            info = f"{mname}" + (f" ({vtxt})" if vtxt else "")
            il = QLabel(info)
            il.setStyleSheet("font-size: 11px;")
            r.addWidget(il, 1)
            xb = set_btn_role(QPushButton(tr("卸载", "Unload")), "ghost")
            xb.setFixedHeight(22)
            xb.clicked.connect(lambda _c=False, m=mid: self.vm.unload_model_from_vram(m))
            r.addWidget(xb)
            self.coresident_lay.addLayout(r)

    def _rebuild_shards_list(self) -> None:
        self.shards_box.set_title(
            tr(f"查看权重分片 ({len(self.vm.model_files)})", f"View Weight Shards ({len(self.vm.model_files)})")
        )
        sig = (
            get_lang(),
            self.vm.selected_model_id,
            tuple((f.name, f.exists, round(f.size_gb, 2), f.desc) for f in self.vm.model_files),
        )
        if sig == self._last_shards_sig:
            return
        self._last_shards_sig = sig
        self._clear_layout(self.shards_list_lay)
        for f in self.vm.model_files:
            mark = tr("[已就绪]", "[Ready]") if f.exists else tr("[未下载]", "[Missing]")
            color = "#059669" if f.exists else "#64748B"
            sz = (
                f"{f.size_gb:.1f}G"
                if f.exists and f.size_gb > 0
                else (tr("已就绪", "Ready") if f.exists else tr("未下", "Missing"))
            )
            short_name = Path(f.name).name
            lbl = QLabel(f"{mark} {short_name}  ({sz})")
            if f.desc:
                lbl.setToolTip(f.desc)
            lbl.setStyleSheet(f"font-family: Consolas, monospace; font-size: 10.5px; color: {color};")
            self.shards_list_lay.addWidget(lbl)
        self.shards_list_lay.addStretch(1)

    def _rebuild_mode_radio_cards(self) -> None:
        sig = (get_lang(), self.vm.selected_model_id, self.vm.task_mode_id, self.vm.dark_mode)
        if sig == self._last_modes_sig:
            return
        self._last_modes_sig = sig
        self._clear_layout(self.mode_buttons_row)
        pal = self.palette_obj
        for m in self.vm.active_model_spec.modes:
            is_cur = m.id == self.vm.task_mode_id
            card = ModeRadioCard(
                glyph=icon_glyph(m.icon),
                title=m.title,
                subtitle=m.subtitle,
                selected=is_cur,
                pal=pal,
            )
            card.clicked.connect(lambda mid=m.id: self.vm.set_task_mode(mid))
            self.mode_buttons_row.addWidget(card, 1)


    # ─── Telemetry, Console, Chat & Local Gallery Refreshers ─────────────────

    def _refresh_telemetry(self) -> None:
        pal = self.palette_obj
        v_col = metric_threshold_color("vram", self.vm.vram_free_gb, pal.metric_vram)
        r_col = metric_threshold_color("ram", self.vm.ram_free_gb, pal.metric_ram)
        d_col = metric_threshold_color("disk", self.vm.disk_free_gb, pal.metric_disk)

        if self.vm.combined_chart_mode:
            self.chart_mode_btn.setText(tr("分项", "Split"))
            self.charts_stack.setCurrentIndex(1)
            self.chart_combined.update_all(
                [
                    (tr("显存", "VRAM"), self.vm.vram_history_pct, self.vm.vram_used_gb, self.vm.vram_total_gb, v_col),
                    (tr("内存", "RAM"), self.vm.ram_history_pct, self.vm.ram_used_gb, self.vm.ram_total_gb, r_col),
                    (tr("磁盘", "Disk"), self.vm.disk_history_pct, self.vm.disk_used_gb, self.vm.disk_total_gb, d_col),
                ]
            )
        else:
            self.chart_mode_btn.setText(tr("同屏", "Overlay"))
            self.charts_stack.setCurrentIndex(0)
            self.chart_vram.update_metric(self.vm.vram_history_pct, self.vm.vram_used_gb, self.vm.vram_total_gb, v_col)
            self.chart_ram.update_metric(self.vm.ram_history_pct, self.vm.ram_used_gb, self.vm.ram_total_gb, r_col)
            self.chart_disk.update_metric(self.vm.disk_history_pct, self.vm.disk_used_gb, self.vm.disk_total_gb, d_col)

        parts = []
        if self.vm.shm_total_gb >= 1.0:
            parts.append(
                tr(
                    f"内存盘可用 {self.vm.shm_free_gb:.1f}/{self.vm.shm_total_gb:.0f}G",
                    f"RAM Disk Free {self.vm.shm_free_gb:.1f}/{self.vm.shm_total_gb:.0f}G",
                )
            )
        if self.vm.drive_total_gb > 0:
            parts.append(
                tr(
                    f"云盘可用 {self.vm.drive_free_gb:.1f}G",
                    f"Drive Free {self.vm.drive_free_gb:.1f}G",
                )
            )
        if parts:
            self.storage_footer_lbl.setText(" · ".join(parts))
            self.storage_footer_lbl.setVisible(True)
        else:
            self.storage_footer_lbl.setVisible(False)

    def _refresh_console(self) -> None:
        is_dark = self.vm.dark_mode
        html_lines = []
        for ln in self.vm.live_console_lines:
            esc = html.escape(ln)
            if any(k in ln for k in ("失败", "错误", "异常", "ERROR", "Error", "error:", "Failed", "failed")):
                col = "#FA7575" if is_dark else "#DC2626"
            elif "───" in ln:
                col = "#75CCFA" if is_dark else "#0284C7"
            elif any(k in ln for k in ("%", "已装载", "成功", "完成", "Loaded", "Success", "Complete", "complete", "ready.")):
                col = "#59EB8C" if is_dark else "#059669"
            else:
                col = "#DEDEDE" if is_dark else "#1E293B"
            html_lines.append(f'<div style="color:{col}; margin-bottom:2px; white-space:pre-wrap;">{esc}</div>')
        self.terminal_view.setHtml("".join(html_lines))
        sb = self.terminal_view.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _refresh_chat_conversation(self) -> None:
        self._clear_layout(self.chat_turns_container)
        if not self.vm.chat_history:
            empty = QLabel(
                tr(
                    "尚无对话记录。输入问题或拖入图片后按 Ctrl+Enter 即可开始推理。",
                    "No conversation yet. Enter a prompt or drop an image and press Ctrl+Enter to start reasoning.",
                )
            )
            empty.setStyleSheet("color: #64748B; font-size: 12px; padding: 14px;")
            self.chat_turns_container.addWidget(empty)
            return

        is_dark = self.vm.dark_mode
        user_col = "#60A5FA" if is_dark else "#2563EB"
        asst_col = "#34D399" if is_dark else "#059669"
        for turn in self.vm.chat_history:
            box = QFrame()
            box.setObjectName("SubtlePanel")
            bl = QVBoxLayout(box)
            bl.setContentsMargins(12, 10, 12, 10)
            bl.setSpacing(6)

            hdr = QHBoxLayout()
            if turn.role == "user":
                rl = QLabel(tr("提问", "You"))
                rl.setStyleSheet(f"font-weight: 700; color: {user_col}; font-size: 12px;")
                hdr.addWidget(rl)
                if turn.has_image:
                    hdr.addWidget(
                        PillBadge(tr("附带视觉图像", "With Image"), fg="#059669", bg="rgba(16,185,129,0.14)")
                    )
                hdr.addStretch(1)
            else:
                rl = QLabel(f"{self.vm.active_model_spec.name}")
                rl.setStyleSheet(f"font-weight: 700; color: {asst_col}; font-size: 12px;")
                hdr.addWidget(rl)
                hdr.addStretch(1)
                cp = set_btn_role(QPushButton(tr("复制回复", "Copy Reply")), "ghost")
                cp.setStyleSheet("font-size: 11px;")
                cp.clicked.connect(
                    lambda _c=False, txt=turn.content: self._copy_text(
                        txt,
                        tr("已复制模型回复到剪贴板。", "Copied model reply to clipboard."),
                    )
                )
                hdr.addWidget(cp)
            bl.addLayout(hdr)

            if turn.role == "assistant" and turn.thinking:
                think_box = CollapsibleBox(
                    tr(f"深度思考过程 ({len(turn.thinking)} 字)", f"Thinking Process ({len(turn.thinking)} chars)"),
                    expanded=(not bool(turn.content)),
                )
                th_lbl = QLabel(turn.thinking)
                th_lbl.setWordWrap(True)
                th_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                th_lbl.setStyleSheet("font-size: 11.5px; color: #64748B; padding: 4px;")
                think_box.content_layout.addWidget(th_lbl)
                bl.addWidget(think_box)

            content_txt = (
                turn.content
                if turn.content
                else (tr("正在思考与生成回复...", "Thinking & generating reply...") if turn.role == "assistant" else "")
            )
            c_lbl = QLabel(content_txt)
            c_lbl.setWordWrap(True)
            c_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            c_lbl.setStyleSheet("font-size: 12.5px; line-height: 1.45;")
            bl.addWidget(c_lbl)
            self.chat_turns_container.addWidget(box)

    def _refresh_media_gallery(self) -> None:
        self._clear_layout(self.local_gallery_lay)
        if not self.vm.local_media_items:
            empty = QLabel(tr("本地目录暂无历史作品", "No local outputs yet"))
            empty.setStyleSheet("color: #64748B; font-size: 11.5px; padding: 12px;")
            self.local_gallery_lay.addWidget(empty)
        else:
            for item in self.vm.local_media_items[:60]:
                ic = tr("[图片]", "[Img]") if item.is_image else tr("[视频]", "[Vid]")
                ts_str = datetime.fromtimestamp(item.created_ts).strftime("%m-%d %H:%M") if item.created_ts > 0 else ""
                el_str = f" · {format_duration(item.elapsed_seconds, compact=True)}" if item.elapsed_seconds else ""
                btn = QPushButton(f"{ic} {item.filename[:22]}\n{ts_str}{el_str}")
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setStyleSheet("QPushButton { text-align: left; padding: 6px 8px; font-size: 11px; }")
                btn.clicked.connect(lambda _c=False, p=item.path: self.vm.select_local_media(p, auto_play=True))
                self.local_gallery_lay.addWidget(btn)
        self.local_gallery_lay.addStretch(1)

    def _on_media_selected(self, path_obj: object, elapsed_obj: object, auto_play: bool) -> None:
        p = path_obj if isinstance(path_obj, Path) else None
        el = float(elapsed_obj) if isinstance(elapsed_obj, (int, float)) else None
        self.media_preview.load_media(p, elapsed_seconds=el, auto_play=auto_play)

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
                EasyColabMainWindow._clear_layout(item.layout())
