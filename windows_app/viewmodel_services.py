"""
Core ViewModel (EasyColabViewModel) for the EasyColab Windows Client.
Handles settings persistence, asynchronous HTTP calls to Colab (/minimax_api/*),
headless colab_bridge.py subprocess orchestration (with CREATE_NO_WINDOW on Windows),
2.5s telemetry & keepalive watchdog loop, job polling, and local media management.
"""
from __future__ import annotations

import json
import os
import secrets
import shutil
import subprocess
import sys
import threading
import time
import urllib.parse
import uuid
import webbrowser
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import requests
from PySide6.QtCore import QObject, QTimer, Signal

from windows_app.models import (
    IMAGE_RESOLUTIONS,
    MODEL_SPEC_MAP,
    OPEN_MODEL_CATALOG,
    PRESET_TEMPLATES,
    VIDEO_RESOLUTIONS,
    ChatTurnItem,
    ComfyOutputMediaItem,
    ComfyPresetPackItem,
    LoadedModelSummary,
    LocalMediaItem,
    ModelFileItem,
    ModelModality,
    OpenModelSpec,
    ResolutionOption,
    build_default_comfy_preset_packs,
    format_duration,
    get_app_config_dir,
    get_lang,
    get_legacy_media_dirs,
    get_local_save_dir,
    is_en,
    localize_server_text,
    mask_email_display,
    mask_url_display,
    open_path_in_os,
    resolve_resource_path,
    set_lang,
    snap_video_frames,
    strip_emoji,
    tr,
)

WIN_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0




class ViewModelServicesMixin:
    # ─── Headless colab_bridge.py Execution ──────────────────────────────────

    def _resolve_python_for_bridge(self, install_if_missing: bool = False) -> List[str]:
        """
        Return base command prefix to execute colab_bridge CLI:
        - Portable Windows bundle: `[_internal/runtime/python.exe, "-X", "utf8", colab_bridge.py]`
        - PyInstaller Windows .exe: `[EasyColab.exe, "--bridge-cli"]`
        - Dev Python source: `[python, colab_bridge.py]` (with automatic managed venv fallback if needed).
        """
        bridge_py = resolve_resource_path("colab_bridge.py")

        # 1. Direct filesystem check for bundled embeddable runtime (works regardless of sys.frozen)
        exe_dir = Path(sys.executable).resolve().parent
        pkg_parent = Path(__file__).resolve().parent.parent
        env_internal = os.environ.get("EASYCOLAB_INTERNAL_DIR", "").strip()
        embedded_candidates = [
            pkg_parent / "runtime" / "python.exe",
            exe_dir / "_internal" / "runtime" / "python.exe",
            exe_dir / "runtime" / "python.exe",
        ]
        if env_internal:
            embedded_candidates.insert(0, Path(env_internal) / "runtime" / "python.exe")

        for emb_py in embedded_candidates:
            if emb_py.exists() and bridge_py.exists():
                return [str(emb_py), "-X", "utf8", str(bridge_py)]

        # 2. PyInstaller frozen executable fallback
        if getattr(sys, "frozen", False):
            return [sys.executable, "--bridge-cli"]

        # 3. Dev Python source mode (never treat a non-Python GUI .exe as a Python interpreter)
        candidates: List[Path] = []
        cur_exe = Path(sys.executable)
        if cur_exe.stem.lower().startswith("python"):
            candidates.append(cur_exe)
        repo_root = Path(__file__).resolve().parent.parent
        if sys.platform == "win32":
            candidates.append(repo_root / ".venv" / "Scripts" / "python.exe")
            managed_dir = get_app_config_dir() / "venv"
            managed_py = managed_dir / "Scripts" / "python.exe"
        else:
            candidates.append(repo_root / ".venv" / "bin" / "python")
            managed_dir = get_app_config_dir() / "venv"
            managed_py = managed_dir / "bin" / "python"
        candidates.append(managed_py)

        for py in candidates:
            if py.exists():
                try:
                    chk = subprocess.run(
                        [str(py), "-c", "import colab_cli, google.auth, websocket"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=8,
                        creationflags=WIN_NO_WINDOW,
                    )
                    if chk.returncode == 0:
                        return [str(py), str(bridge_py)]
                except Exception:
                    pass

        if install_if_missing:
            self._dispatch_ui(
                lambda: self._set_status_and_log(
                    tr(
                        "首次使用正在初始化本地 Colab 连接组件 (约需 15~30 秒)...",
                        "First-run setup: initializing local Colab bridge components (~15-30s)...",
                    )
                )
            )
            if not managed_py.exists():
                subprocess.run(
                    [sys.executable, "-m", "venv", str(managed_dir)],
                    check=True,
                    creationflags=WIN_NO_WINDOW,
                )
            subprocess.run(
                [
                    str(managed_py),
                    "-m",
                    "pip",
                    "install",
                    "-q",
                    "google-colab-cli>=0.7.5",
                    "google-auth>=2.28.0",
                    "google-auth-oauthlib>=1.2.0",
                    "requests>=2.31.0",
                    "requests-oauthlib>=1.3.1",
                    "websocket-client>=1.7.0",
                ],
                check=True,
                creationflags=WIN_NO_WINDOW,
            )
            return [str(managed_py), str(bridge_py)]

        if not cur_exe.stem.lower().startswith("python"):
            return [sys.executable, "--bridge-cli"]
        return [sys.executable, str(bridge_py)]

    def _set_status_and_log(self, msg: str) -> None:
        self.status_message = strip_emoji(self.masked_url(msg))
        self.append_console_line(msg)
        self.state_changed.emit()

    def _bridge_env(self) -> Dict[str, str]:
        env = os.environ.copy()
        env["PYTHONUTF8"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        return env

    def _run_bridge_json(self, subargs: List[str], install_if_missing: bool = False, timeout: int = 45) -> dict:
        cmd = self._resolve_python_for_bridge(install_if_missing=install_if_missing) + subargs
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=self._bridge_env(),
            timeout=timeout,
            creationflags=WIN_NO_WINDOW,
        )
        out = (proc.stdout or "").strip()
        for line in reversed(out.splitlines()):
            line = line.strip()
            if line.startswith("{") and line.endswith("}"):
                return json.loads(line)
        if proc.stderr:
            return {"ok": False, "error": proc.stderr.strip()[-300:]}
        return {"ok": False, "error": out or tr("空响应", "Empty response")}

    # ─── Google OAuth & Headless Wake / Keepalive / Stop ─────────────────────

    def refresh_official_colab_account_usage(self) -> None:
        if self._auth_busy:
            return
        self._auth_busy = True

        def worker() -> None:
            try:
                data = self._run_bridge_json(["auth_status"], install_if_missing=False, timeout=25)
            except Exception as exc:
                data = {"ok": False, "error": str(exc)}

            def apply_ui() -> None:
                self._auth_busy = False
                logged = bool(data.get("logged_in", False))
                self.cli_logged_in = logged
                if logged:
                    if data.get("email"):
                        self.account_email = str(data["email"])
                    if data.get("paid_balance") is not None:
                        bal = float(data["paid_balance"])
                        self.official_cu_balance = bal
                        self.total_budget_cu = bal
                        self._save_setting("totalBudgetCU", bal)
                    if data.get("burn_rate_hourly") is not None:
                        self.official_burn_rate = float(data["burn_rate_hourly"])
                    if data.get("active_assignments") is not None:
                        self.active_vm_count = int(data["active_assignments"])
                        if self.active_vm_count == 0 and not self.is_connected and self.loaded_model_ids:
                            self.reset_stale_remote_runtime_state(
                                tr("云端实例已释放，本地状态已同步归零。", "Cloud runtime released; local state reset.")
                            )
                self.state_changed.emit()

            self._dispatch_ui(apply_ui)

        threading.Thread(target=worker, daemon=True).start()

    def start_google_oauth_login(self, switching_account: bool = False) -> None:
        self.status_message = tr("正在生成 Google OAuth 安全授权链接...", "Generating Google OAuth authorization URL...")
        self.state_changed.emit()

        def worker() -> None:
            try:
                data = self._run_bridge_json(["auth_url"], install_if_missing=True, timeout=120)
            except Exception as exc:
                data = {"ok": False, "error": str(exc)}

            def apply_ui() -> None:
                auth_url = str(data.get("auth_url") or "").strip()
                if auth_url:
                    self.show_oauth_code_input = True
                    tip = (
                        tr(
                            "请在弹出的浏览器中选择要切换的 Google 账号，并将授权码粘贴回下方输入框。",
                            "Select the Google account in your browser and paste the authorization code below.",
                        )
                        if switching_account
                        else tr(
                            "已在浏览器打开 Google 授权页，请登录并复制授权码粘贴至下方输入框。",
                            "Opened Google sign-in in browser. Authorize and paste the code below.",
                        )
                    )
                    self.status_message = tip
                    self.append_console_line(tip)
                    webbrowser.open(auth_url)
                else:
                    err = str(data.get("error") or tr("无法生成授权链接", "Failed to generate OAuth URL"))
                    self.status_message = tr(f"获取授权链接失败：{err}", f"Failed to get OAuth URL: {err}")
                    self.append_console_line(self.status_message)
                self.state_changed.emit()

            self._dispatch_ui(apply_ui)

        threading.Thread(target=worker, daemon=True).start()

    def submit_google_oauth_code(self, code: str) -> None:
        trimmed = (code or "").strip()
        if not trimmed:
            self.status_message = tr(
                "请先粘贴浏览器中显示的 Google 授权码。",
                "Please paste the Google authorization code from your browser first.",
            )
            self.state_changed.emit()
            return

        was_logged_in = self.cli_logged_in
        prev_email = self.account_email
        self.status_message = tr(
            "正在验证授权码并同步 Google Colab 算力账户...",
            "Verifying authorization code & syncing Google Colab account...",
        )
        self.state_changed.emit()

        def worker() -> None:
            try:
                data = self._run_bridge_json(["auth_code", trimmed], install_if_missing=True, timeout=45)
            except Exception as exc:
                data = {"ok": False, "error": str(exc)}

            def apply_ui() -> None:
                if data.get("logged_in"):
                    new_email = str(data.get("email") or "")
                    if was_logged_in and (new_email != prev_email or self.colab_server_url):
                        self.set_colab_server_url("")
                        self.reset_stale_remote_runtime_state(
                            tr(
                                "已切换 Google 账号，请点击「唤醒实例并部署」启动新实例。",
                                "Switched Google account. Click 'Wake & Deploy' to launch a new runtime.",
                            )
                        )
                    self.cli_logged_in = True
                    self.account_email = new_email
                    self.show_oauth_code_input = False
                    if data.get("paid_balance") is not None:
                        bal = float(data["paid_balance"])
                        self.official_cu_balance = bal
                        self.total_budget_cu = bal
                        self._save_setting("totalBudgetCU", bal)
                    if data.get("burn_rate_hourly") is not None:
                        self.official_burn_rate = float(data["burn_rate_hourly"])
                    if data.get("active_assignments") is not None:
                        self.active_vm_count = int(data["active_assignments"])
                    self.status_message = tr(
                        f"Google 账号绑定成功 ({self.display_account_label})！现在可一键唤醒 {self.wake_gpu_choice} 实例。",
                        f"Google account bound ({self.display_account_label})! Ready to wake {self.wake_gpu_choice} runtime in 1 click.",
                    )
                    self.append_console_line(self.status_message)
                else:
                    err = str(data.get("error") or tr("授权码无效或已过期", "Invalid or expired authorization code"))
                    self.status_message = tr(f"绑定失败：{err}", f"Account binding failed: {err}")
                    self.append_console_line(self.status_message)
                self.state_changed.emit()

            self._dispatch_ui(apply_ui)

        threading.Thread(target=worker, daemon=True).start()

    def logout_google_account(self) -> None:
        def worker() -> None:
            try:
                self._run_bridge_json(["auth_logout"], install_if_missing=False, timeout=20)
            except Exception:
                pass

            def apply_ui() -> None:
                self.cli_logged_in = False
                self.account_email = ""
                self.official_cu_balance = None
                self.official_burn_rate = None
                self.active_vm_count = 0
                self.show_oauth_code_input = False
                self.set_colab_server_url("")
                self.reset_stale_remote_runtime_state(tr("已退出当前 Google 账号。", "Signed out of Google account."))
                self.state_changed.emit()

            self._dispatch_ui(apply_ui)

        threading.Thread(target=worker, daemon=True).start()

    def wake_colab_headless(self) -> None:
        if self.is_waking_colab:
            return
        if not self.cli_logged_in:
            self.status_message = tr(
                "请先点击「绑定」授权登录 Google 账号。",
                "Please click 'Bind' to sign in with your Google account first.",
            )
            self.state_changed.emit()
            return

        app_py = resolve_resource_path("app.py")
        if not app_py.exists():
            self.status_message = tr(f"未找到服务端脚本 app.py ({app_py})", f"Server script app.py not found ({app_py})")
            self.state_changed.emit()
            return

        gpu = self.wake_gpu_choice
        self.is_waking_colab = True
        self.status_message = tr(
            f"正在唤醒 Google Colab {gpu} 实例并自动部署多模型服务端...",
            f"Waking Google Colab {gpu} runtime & deploying multi-model server...",
        )
        self.append_console_line(
            tr(
                f"─── 开始无网页唤醒 Colab {gpu} 实例 ───",
                f"─── Starting Headless Wake for Colab {gpu} Runtime ───",
            )
        )
        self.state_changed.emit()

        def worker() -> None:
            try:
                cmd = self._resolve_python_for_bridge(install_if_missing=True) + [
                    "wake",
                    "--gpu",
                    gpu,
                    "--app-py",
                    str(app_py),
                ]
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    bufsize=1,
                    env=self._bridge_env(),
                    creationflags=WIN_NO_WINDOW,
                )
                assert proc.stdout is not None
                for raw_line in proc.stdout:
                    line = raw_line.strip()
                    if not line:
                        continue
                    if line.startswith("WAKE_URL:"):
                        url = line[len("WAKE_URL:") :].strip()

                        def on_url(u: str = url) -> None:
                            self.set_colab_server_url(u)
                            self.append_console_line(
                                tr(
                                    f"成功获取云端隧道地址: {self.masked_url(u)}",
                                    f"Tunnel URL acquired: {self.masked_url(u)}",
                                )
                            )
                            self.status_message = tr(
                                f"云端 {gpu} 实例已唤醒就绪，正在同步模型状态...",
                                f"Cloud {gpu} runtime is online! Syncing model status...",
                            )
                            self.state_changed.emit()

                        self._dispatch_ui(on_url)
                    elif line.startswith("WAKE_ERROR:"):
                        err_txt = strip_emoji(line[len("WAKE_ERROR:") :].strip())

                        def on_err(e: str = err_txt) -> None:
                            loc_e = localize_server_text(e)
                            msg_e = tr(f"唤醒失败: {loc_e}", f"Wake failed: {loc_e}")
                            self.append_console_line(msg_e)
                            self.status_message = msg_e
                            self.state_changed.emit()

                        self._dispatch_ui(on_err)
                    else:
                        clean = strip_emoji(line.replace("WAKE_LOG:", "").strip())
                        if clean:

                            def on_log(c: str = clean) -> None:
                                loc_c = localize_server_text(c)
                                self.append_console_line(loc_c)
                                self.status_message = loc_c
                                self.state_changed.emit()

                            self._dispatch_ui(on_log)
                proc.wait(timeout=30)
            except Exception as exc:
                err_msg = str(exc)
                self._dispatch_ui(
                    lambda: self._set_status_and_log(tr(f"唤醒进程异常: {err_msg}", f"Wake process error: {err_msg}"))
                )

            def finish_ui() -> None:
                self.is_waking_colab = False
                self.state_changed.emit()
                self.refresh_official_colab_account_usage()
                if self.normalized_base_url:
                    self.check_colab_status(silent=False)

            self._dispatch_ui(finish_ui)

        threading.Thread(target=worker, daemon=True).start()

    def keepalive_colab_runtime(self) -> None:
        def worker() -> None:
            try:
                data = self._run_bridge_json(["keepalive"], install_if_missing=False, timeout=35)
            except Exception:
                return

            def apply_ui() -> None:
                if data.get("paid_balance") is not None:
                    bal = float(data["paid_balance"])
                    self.official_cu_balance = bal
                    self.total_budget_cu = bal
                if data.get("burn_rate_hourly") is not None:
                    self.official_burn_rate = float(data["burn_rate_hourly"])
                if data.get("active_assignments") is not None:
                    self.active_vm_count = int(data["active_assignments"])
                self.state_changed.emit()

            self._dispatch_ui(apply_ui)

        threading.Thread(target=worker, daemon=True).start()

    def disconnect_remote_colab(self) -> None:
        if self.is_releasing_colab:
            return
        self.is_releasing_colab = True
        self._active_generation_token = str(uuid.uuid4())
        self.is_generating = False
        self.status_message = tr(
            "正在同步云盘数据并彻底销毁所有运行中的 Colab GPU 实例...",
            "Syncing Google Drive & terminating all active Colab GPU runtimes...",
        )
        self.append_console_line(
            tr(
                "─── 正在断开并释放全部云端 GPU 实例 ───",
                "─── Disconnecting & Releasing All Cloud GPU Runtimes ───",
            )
        )
        self.state_changed.emit()

        base = self.normalized_base_url

        def worker() -> None:
            if base:
                try:
                    requests.post(f"{base}/minimax_api/disconnect", json={}, timeout=8)
                except Exception:
                    pass
            try:
                data = self._run_bridge_json(["stop_all"], install_if_missing=False, timeout=60)
            except Exception as exc:
                data = {"ok": False, "error": str(exc)}

            def apply_ui() -> None:
                self.is_releasing_colab = False
                self.set_colab_server_url("")
                raw_msg = str(data.get("message") or data.get("error") or tr("已释放全部云端实例。", "All cloud runtimes released."))
                msg = localize_server_text(strip_emoji(raw_msg))
                self.reset_stale_remote_runtime_state(msg)
                if data.get("paid_balance") is not None:
                    self.official_cu_balance = float(data["paid_balance"])
                self.official_burn_rate = float(data.get("burn_rate_hourly") or 0.0)
                self.active_vm_count = int(data.get("active_assignments") or 0)
                self.append_console_line(msg)
                self.state_changed.emit()

            self._dispatch_ui(apply_ui)

        threading.Thread(target=worker, daemon=True).start()


    # ─── Model Selection, Weight Download, Load & Unload ─────────────────────

    def _load_persisted_custom_models(self) -> None:
        raw_list = self._settings.get("customModels")
        if not isinstance(raw_list, list):
            return
        loaded: List[OpenModelSpec] = []
        for item in raw_list:
            if isinstance(item, dict) and item.get("id") and item.get("repo_id"):
                spec = OpenModelSpec.from_custom_dict(item)
                loaded.append(spec)
                MODEL_SPEC_MAP[spec.id] = spec
        self.custom_models = loaded

    def _save_persisted_custom_models(self) -> None:
        serialized = [
            {
                "id": s.id,
                "name": s.name_zh,
                "repo_id": s.repo_id,
                "include_pattern": s.include_pattern,
                "modality": s.modality.value,
                "category": s.summary_zh,
                "approx_size_gb": s.approx_size_gb,
                "is_custom": True,
            }
            for s in self.custom_models
        ]
        self._save_setting("customModels", serialized)

    def _merge_remote_custom_models(self, remote_list: list) -> None:
        by_id: Dict[str, OpenModelSpec] = {s.id: s for s in self.custom_models}
        remote_ids: List[str] = []
        for item in remote_list:
            if isinstance(item, dict) and item.get("id") and item.get("repo_id"):
                spec = OpenModelSpec.from_custom_dict(item)
                by_id[spec.id] = spec
                MODEL_SPEC_MAP[spec.id] = spec
                remote_ids.append(spec.id)
        ordered = remote_ids + [s.id for s in self.custom_models if s.id not in remote_ids]
        self.custom_models = [by_id[mid] for mid in ordered if mid in by_id]
        self._save_persisted_custom_models()

    _UNSUPPORTED_HF_PIPELINE_TAGS = {
        "image-to-3d", "text-to-3d", "image-segmentation", "object-detection",
        "depth-estimation", "mask-generation", "keypoint-detection", "robotics",
        "reinforcement-learning", "tabular-classification", "tabular-regression",
        "time-series-forecasting", "audio-classification", "automatic-speech-recognition",
        "text-to-speech", "audio-to-audio", "feature-extraction", "sentence-similarity",
        "token-classification", "text-classification", "zero-shot-image-classification",
        "zero-shot-classification", "fill-mask", "question-answering",
        "table-question-answering", "video-classification",
    }

    _SUPPORTED_TRENDING_PIPELINE_TAGS = {
        "text-generation", "image-text-to-text", "visual-question-answering",
        "any-to-any", "text-to-image", "image-to-image", "text-to-video", "image-to-video",
    }

    @staticmethod
    def _analyze_hf_model_sizing(item: dict, is_gguf: bool) -> dict:
        import re as _re

        rid = str(item.get("id") or item.get("modelId") or "")
        ptag = str(item.get("pipeline_tag") or "").strip().lower()
        st = item.get("safetensors") if isinstance(item.get("safetensors"), dict) else {}
        gg = item.get("gguf") if isinstance(item.get("gguf"), dict) else {}
        total_params = int(st.get("total") or gg.get("total") or 0)
        if total_params <= 0:
            m = _re.search(r"(?:^|[-_/])(\d+(?:\.\d+)?)\s*([bBmMtT])(?:[-_/\b]|$)", rid)
            if m:
                val = float(m.group(1))
                unit = m.group(2).upper()
                if unit == "T":
                    total_params = int(val * 1e12)
                elif unit == "B":
                    total_params = int(val * 1e9)
                elif unit == "M":
                    total_params = int(val * 1e6)

        if total_params >= 1e12:
            param_label = f"{total_params / 1e12:.1f}T"
        elif total_params >= 1e9:
            b = total_params / 1e9
            param_label = f"{b:.0f}B" if b >= 20 else f"{b:.1f}B".replace(".0B", "B")
        elif total_params >= 1e6:
            param_label = f"{total_params / 1e6:.0f}M"
        else:
            param_label = ""

        params_b = total_params / 1e9 if total_params > 0 else 0.0
        if is_gguf:
            est_vram_gb = round(params_b * 0.62 + 1.2, 1) if params_b > 0 else 0.0
        else:
            pmap = st.get("parameters") if isinstance(st.get("parameters"), dict) else {}
            if pmap:
                bytes_total = 0.0
                for dtype, cnt in pmap.items():
                    dt = str(dtype).upper()
                    c = float(cnt or 0)
                    if "32" in dt:
                        bytes_total += c * 4.0
                    elif "16" in dt:
                        bytes_total += c * 2.0
                    elif "8" in dt:
                        bytes_total += c * 1.0
                    elif "4" in dt:
                        bytes_total += c * 0.55
                    else:
                        bytes_total += c * 2.0
                est_vram_gb = round((bytes_total / 1e9) * 1.12 + 1.2, 1)
            elif params_b > 0:
                est_vram_gb = round(params_b * 2.1 + 1.2, 1)
            else:
                est_vram_gb = 0.0

        vram_disp = max(1, int(round(est_vram_gb)))
        if not is_gguf and ptag in ViewModelServicesMixin._UNSUPPORTED_HF_PIPELINE_TAGS:
            status = "too_large"
            zh = f"非内置管线 ({ptag} · 需专用SDK)"
            en = f"Custom Pipeline ({ptag})"
        elif est_vram_gb <= 0:
            status = "unknown"
            zh = "显存待探测"
            en = "VRAM TBD"
        elif est_vram_gb <= 14.2:
            status = "great"
            zh = f"适合 · T4(15G)可跑 (~{vram_disp}G)"
            en = f"Fit: T4 15G (~{vram_disp}G)"
        elif est_vram_gb <= 22.5:
            status = "good"
            zh = f"适合 · 需L4(24G) (~{vram_disp}G)"
            en = f"Fit: L4 24G (~{vram_disp}G)"
        elif est_vram_gb <= 39.0:
            status = "a100"
            zh = f"可部署 · 需A100(40G) (~{vram_disp}G)"
            en = f"Fit: A100 40G (~{vram_disp}G)"
        elif est_vram_gb <= 78.0:
            status = "heavy"
            zh = f"需A100(80G) (~{vram_disp}G)"
            en = f"Needs A100 80G (~{vram_disp}G)"
        elif is_gguf and params_b <= 240:
            status = "heavy"
            zh = f"需A100(80G)+CPU卸载 (~{vram_disp}G)"
            en = f"A100 80G + Offload (~{vram_disp}G)"
        else:
            status = "too_large"
            zh = f"超单卡上限 (~{vram_disp}G · 建议搜GGUF)"
            en = f"Too Large (~{vram_disp}G · Try GGUF)"

        return {
            "param_count": total_params,
            "param_label": param_label,
            "est_vram_gb": est_vram_gb,
            "deploy_status": status,
            "deploy_label_zh": zh,
            "deploy_label_en": en,
        }

    def fetch_trending_hf_models(
        self,
        category: str = "all",
        force_refresh: bool = False,
        on_loaded=None,
        search_query: str = "",
    ) -> None:
        cat = (category or "all").strip().lower()
        sq = (search_query or "").strip()
        base = self.normalized_base_url
        tok = self.hf_token.strip()

        def worker() -> None:
            import urllib.parse as _up

            results: list = []
            if self.is_connected and base:
                try:
                    r = requests.get(
                        f"{base}/minimax_api/hf_trending",
                        params={
                            "category": cat,
                            "limit": 14,
                            "hf_token": tok,
                            "force_refresh": "true" if force_refresh else "false",
                            "search_query": sq,
                        },
                        timeout=12,
                    )
                    if r.status_code == 200:
                        data = r.json()
                        if isinstance(data.get("models"), list) and data["models"]:
                            results = data["models"]
                except Exception:
                    pass

            if not results:
                expand_qs = (
                    "&expand[]=safetensors&expand[]=gguf&expand[]=likes"
                    "&expand[]=downloads&expand[]=pipeline_tag&expand[]=tags&expand[]=gated"
                )
                search_qs = f"&search={_up.quote(sq)}" if sq else ""
                if cat == "gguf":
                    qpaths = [f"/api/models?sort=trendingScore&direction=-1&filter=gguf&limit=20{search_qs}{expand_qs}"]
                elif cat == "llm":
                    qpaths = [
                        f"/api/models?sort=trendingScore&direction=-1&pipeline_tag=text-generation&limit=18{search_qs}{expand_qs}",
                    ]
                    if not sq:
                        qpaths.append(
                            f"/api/models?sort=trendingScore&direction=-1&pipeline_tag=image-text-to-text&limit=10{expand_qs}"
                        )
                elif cat == "image_video":
                    qpaths = [
                        f"/api/models?sort=trendingScore&direction=-1&pipeline_tag=text-to-image&limit=12{search_qs}{expand_qs}",
                        f"/api/models?sort=trendingScore&direction=-1&pipeline_tag=image-to-video&limit=10{search_qs}{expand_qs}",
                    ]
                else:
                    qpaths = [f"/api/models?sort=trendingScore&direction=-1&limit=22{search_qs}{expand_qs}"]

                headers = {"User-Agent": "EasyColab-Windows/2.0", "Accept": "application/json"}
                if tok:
                    headers["Authorization"] = f"Bearer {tok}"

                seen = set()
                for qpath in qpaths:
                    raw_arr = None
                    for host in ("https://huggingface.co", "https://hf-mirror.com"):
                        try:
                            resp = requests.get(f"{host}{qpath}", headers=headers, timeout=10)
                            if resp.status_code == 200 and isinstance(resp.json(), list):
                                raw_arr = resp.json()
                                break
                        except Exception:
                            continue
                    if not raw_arr:
                        continue
                    for item in raw_arr:
                        if not isinstance(item, dict):
                            continue
                        rid = str(item.get("id") or item.get("modelId") or "").strip()
                        if "/" not in rid or rid in seen:
                            continue
                        seen.add(rid)
                        rid_low = rid.lower()
                        ptag = str(item.get("pipeline_tag") or "").strip().lower()
                        tags = [str(t).lower() for t in (item.get("tags") or []) if isinstance(t, str)]
                        is_gguf = ("gguf" in rid_low) or ("gguf" in tags)
                        gated_raw = item.get("gated")
                        is_gated = bool(gated_raw) and str(gated_raw).lower() not in ("false", "0", "none")
                        if not sq and cat == "all" and not is_gguf:
                            if ptag in self._UNSUPPORTED_HF_PIPELINE_TAGS:
                                continue
                            if ptag and ptag not in self._SUPPORTED_TRENDING_PIPELINE_TAGS:
                                continue
                            if not ptag and not any(t in tags for t in ("transformers", "diffusers", "text-generation")):
                                continue
                        if "video" in ptag or "text-to-video" in tags or "image-to-video" in tags:
                            mod_str = "video_audio"
                        elif "text-to-image" in ptag or "image-to-image" in ptag or ("diffusers" in tags and not is_gguf):
                            mod_str = "image"
                        else:
                            mod_str = "llm_vlm"
                        sizing = self._analyze_hf_model_sizing(item, is_gguf)
                        results.append(
                            {
                                "repo_id": rid,
                                "name": rid.split("/")[-1],
                                "pipeline_tag": ptag or ("gguf" if is_gguf else "text-generation"),
                                "modality": mod_str,
                                "is_gguf": is_gguf,
                                "is_gated": is_gated,
                                "suggested_pattern": "*Q4_K_M*.gguf" if is_gguf else "",
                                "likes": int(item.get("likes") or 0),
                                "downloads": int(item.get("downloads") or 0),
                                **sizing,
                            }
                        )
                        if len(results) >= 14:
                            break
                    if len(results) >= 14:
                        break

            if callable(on_loaded):
                self._dispatch_ui(lambda r=results: on_loaded(r))

        threading.Thread(target=worker, daemon=True).start()

    def fetch_hf_model_detail(self, repo_id: str, on_loaded=None) -> None:
        raw_repo = (repo_id or "").strip()
        for prefix in (
            "https://huggingface.co/",
            "http://huggingface.co/",
            "https://hf.co/",
            "http://hf.co/",
            "huggingface.co/",
            "hf.co/",
        ):
            if raw_repo.lower().startswith(prefix):
                raw_repo = raw_repo[len(prefix) :]
                break
        parts = [p for p in raw_repo.strip("/").split("/") if p]
        if len(parts) < 2:
            if callable(on_loaded):
                on_loaded({"ok": False, "error": "Invalid Repo ID"})
            return
        clean_id = f"{parts[0]}/{parts[1]}"
        base = self.normalized_base_url
        tok = self.hf_token.strip()

        def worker() -> None:
            if self.is_connected and base:
                try:
                    r = requests.get(
                        f"{base}/minimax_api/hf_model_detail",
                        params={"repo_id": clean_id, "hf_token": tok},
                        timeout=14,
                    )
                    if r.status_code == 200:
                        data = r.json()
                        if isinstance(data, dict) and data.get("ok"):
                            if callable(on_loaded):
                                self._dispatch_ui(lambda d=data: on_loaded(d))
                            return
                except Exception:
                    pass

            headers = {"User-Agent": "EasyColab-Windows/2.0", "Accept": "application/json"}
            if tok:
                headers["Authorization"] = f"Bearer {tok}"

            meta = None
            for host in ("https://huggingface.co", "https://hf-mirror.com"):
                try:
                    resp = requests.get(f"{host}/api/models/{clean_id}?blobs=true", headers=headers, timeout=12)
                    if resp.status_code == 200 and isinstance(resp.json(), dict):
                        meta = resp.json()
                        break
                except Exception:
                    continue

            if not meta:
                if callable(on_loaded):
                    self._dispatch_ui(lambda: on_loaded({"ok": False, "repo_id": clean_id}))
                return

            rid = str(meta.get("id") or meta.get("modelId") or clean_id).strip()
            rid_low = rid.lower()
            ptag = str(meta.get("pipeline_tag") or "").strip().lower()
            tags = [str(t) for t in (meta.get("tags") or []) if isinstance(t, str)]
            tags_low = [t.lower() for t in tags]
            is_gguf = ("gguf" in rid_low) or ("gguf" in tags_low) or bool(meta.get("gguf"))
            gated_raw = meta.get("gated")
            is_gated = bool(gated_raw) and str(gated_raw).lower() not in ("false", "0", "none")

            if "video" in ptag or "text-to-video" in tags_low or "image-to-video" in tags_low:
                mod_str = "video_audio"
            elif "text-to-image" in ptag or "image-to-image" in ptag or ("diffusers" in tags_low and not is_gguf):
                mod_str = "image"
            else:
                mod_str = "llm_vlm"

            sizing = self._analyze_hf_model_sizing(meta, is_gguf)
            card_data = meta.get("cardData") if isinstance(meta.get("cardData"), dict) else {}
            config_data = meta.get("config") if isinstance(meta.get("config"), dict) else {}
            gguf_data = meta.get("gguf") if isinstance(meta.get("gguf"), dict) else {}

            lic = card_data.get("license") or ""
            if isinstance(lic, list):
                lic = ", ".join(str(x) for x in lic)
            lic = str(lic).strip() or "Unspecified"

            base_model = card_data.get("base_model") or ""
            if isinstance(base_model, list):
                base_model = ", ".join(str(x) for x in base_model[:2])
            base_model = str(base_model).strip()

            archs = config_data.get("architectures")
            arch_str = ""
            if isinstance(archs, list) and archs:
                arch_str = str(archs[0])
            elif gguf_data.get("architecture"):
                arch_str = str(gguf_data.get("architecture"))
            elif config_data.get("model_type"):
                arch_str = str(config_data.get("model_type"))

            ctx_len = int(gguf_data.get("context_length") or 0)
            used_storage_gb = round(float(meta.get("usedStorage") or 0.0) / (1024.0**3), 2)

            weight_files = []
            for sib in meta.get("siblings") or []:
                if not isinstance(sib, dict):
                    continue
                fname = str(sib.get("rfilename") or "").strip()
                if not fname.lower().endswith((".gguf", ".safetensors", ".bin", ".pth")):
                    continue
                lfs = sib.get("lfs") if isinstance(sib.get("lfs"), dict) else {}
                f_bytes = float(sib.get("size") or lfs.get("size") or 0.0)
                size_gb = round(f_bytes / (1024.0**3), 2) if f_bytes > 0 else 0.0
                vram_need = round(size_gb * 1.12 + 1.0, 1) if size_gb > 0 else 0.0
                if vram_need <= 0:
                    f_status, f_zh, f_en = "unknown", "体积未知", "Size TBD"
                elif vram_need <= 14.5:
                    f_status, f_zh, f_en = "great", "T4(15G)可跑", "T4 15G Ready"
                elif vram_need <= 22.5:
                    f_status, f_zh, f_en = "good", "L4(24G)可跑", "L4 24G Ready"
                elif vram_need <= 39.0:
                    f_status, f_zh, f_en = "a100", "需A100(40G)", "A100 40G"
                elif vram_need <= 78.0:
                    f_status, f_zh, f_en = "heavy", "需A100(80G)", "A100 80G"
                else:
                    f_status, f_zh, f_en = "too_large", "超单卡显存", ">80G VRAM"
                weight_files.append(
                    {
                        "filename": fname,
                        "size_gb": size_gb,
                        "fit_status": f_status,
                        "fit_zh": f_zh,
                        "fit_en": f_en,
                    }
                )
                if len(weight_files) >= 36:
                    break

            import re as _re

            readme_excerpt = ""
            for host in ("https://huggingface.co", "https://hf-mirror.com"):
                try:
                    r_resp = requests.get(f"{host}/{rid}/raw/main/README.md", headers=headers, timeout=6)
                    if r_resp.status_code == 200:
                        raw_md = r_resp.text[:32768]
                        if raw_md.startswith("---"):
                            end_idx = raw_md.find("\n---", 3)
                            if end_idx != -1:
                                raw_md = raw_md[end_idx + 4 :]
                        raw_md = _re.sub(r"<!--[\s\S]*?-->", "", raw_md)
                        raw_md = _re.sub(r"<a[^>]*>\s*<img[^>]*>\s*</a>", "", raw_md, flags=_re.IGNORECASE)
                        raw_md = _re.sub(r"<img[^>]*>", "", raw_md, flags=_re.IGNORECASE)
                        raw_md = _re.sub(
                            r"<h[1-4][^>]*>(.*?)</h[1-4]>",
                            r"\n### \1\n",
                            raw_md,
                            flags=_re.IGNORECASE | _re.DOTALL,
                        )
                        raw_md = _re.sub(r"<[^>]+>", "", raw_md)
                        raw_md = _re.sub(r"\[!\[[^\]]*\]\([^\)]*\)\]\([^\)]*\)", "", raw_md)
                        raw_md = _re.sub(r"!\[[^\]]*\]\([^\)]*\)", "", raw_md)
                        clean_lines = [
                            ln.strip()
                            for ln in raw_md.splitlines()
                            if ln.strip()
                            and not ln.strip().startswith(("```", "|---", "| ---"))
                        ]
                        joined_md = "\n".join(clean_lines)[:1400].strip()
                        readme_excerpt = _re.sub(r"\[([^\]]+)\]\([^\)\n]*$", r"\1", joined_md)
                        if readme_excerpt:
                            break
                except Exception:
                    continue

            detail = {
                "ok": True,
                "repo_id": rid,
                "name": rid.split("/")[-1],
                "author": str(meta.get("author") or rid.split("/")[0]),
                "pipeline_tag": ptag or ("gguf" if is_gguf else "text-generation"),
                "modality": mod_str,
                "is_gguf": is_gguf,
                "is_gated": is_gated,
                "license": lic,
                "base_model": base_model,
                "architecture": arch_str,
                "context_length": ctx_len,
                "likes": int(meta.get("likes") or 0),
                "downloads": int(meta.get("downloads") or 0),
                "last_modified": str(meta.get("lastModified") or "")[:10],
                "used_storage_gb": used_storage_gb,
                **sizing,
                "weight_files": weight_files,
                "readme_excerpt": readme_excerpt,
            }
            if callable(on_loaded):
                self._dispatch_ui(lambda d=detail: on_loaded(d))

        threading.Thread(target=worker, daemon=True).start()

    def register_custom_hf_model(
        self,
        repo_id: str,
        include_pattern: str = "",
        display_name: str = "",
        modality: str = "auto",
        auto_download: bool = False,
    ) -> None:
        raw_repo = (repo_id or "").strip()
        for prefix in (
            "https://huggingface.co/",
            "http://huggingface.co/",
            "https://hf.co/",
            "http://hf.co/",
            "huggingface.co/",
            "hf.co/",
        ):
            if raw_repo.lower().startswith(prefix):
                raw_repo = raw_repo[len(prefix) :]
                break
        parts = [p for p in raw_repo.strip("/").split("/") if p]
        if len(parts) < 2:
            self.status_message = tr(
                "请输入合法的 HuggingFace 仓库地址（格式：作者/仓库名，如 unsloth/Qwen3.8-27B-GGUF）",
                "Please enter a valid HuggingFace Repo ID (format: owner/repo, e.g. unsloth/Qwen3.8-27B-GGUF)",
            )
            self.state_changed.emit()
            return
        clean_repo = f"{parts[0]}/{parts[1]}"
        inc = (include_pattern or "").strip()
        disp = (display_name or "").strip()
        mod_pref = (modality or "auto").strip()
        base = self.normalized_base_url

        if self.is_connected and base:
            self.status_message = tr(
                f"正在解析 HuggingFace 仓库 {clean_repo} 并同步至云端模型中心...",
                f"Resolving HuggingFace repo {clean_repo} & syncing to cloud Model Center...",
            )
            self.state_changed.emit()

            def worker() -> None:
                try:
                    r = requests.post(
                        f"{base}/minimax_api/custom_model/register",
                        json={
                            "repo_id": clean_repo,
                            "include_pattern": inc,
                            "custom_name": disp,
                            "display_name": disp,
                            "modality": mod_pref,
                            "modality_hint": mod_pref,
                            "hf_token": self.hf_token.strip(),
                        },
                        timeout=35,
                    )
                    if r.status_code == 200:
                        data = r.json()

                        def on_ok() -> None:
                            self._apply_status_response(data, update_status_msg=True)
                            reg = data.get("registered_model")
                            if isinstance(reg, dict) and reg.get("id"):
                                spec = OpenModelSpec.from_custom_dict(reg)
                                MODEL_SPEC_MAP[spec.id] = spec
                                idx = next((i for i, s in enumerate(self.custom_models) if s.id == spec.id), -1)
                                if idx >= 0:
                                    self.custom_models[idx] = spec
                                else:
                                    self.custom_models.append(spec)
                                self._save_persisted_custom_models()
                                self.select_model(spec.id)
                                if auto_download:
                                    self.download_model_weights()

                        self._dispatch_ui(on_ok)
                        return
                except Exception:
                    pass
                self._dispatch_ui(
                    lambda: self._register_custom_hf_model_offline(clean_repo, inc, disp, mod_pref)
                )

            threading.Thread(target=worker, daemon=True).start()
        else:
            self._register_custom_hf_model_offline(clean_repo, inc, disp, mod_pref)

    def _register_custom_hf_model_offline(
        self, clean_repo: str, inc: str, disp: str, mod_pref: str
    ) -> None:
        import re as _re

        slug = _re.sub(r"[^a-z0-9]+", "_", (clean_repo + (f"_{inc}" if inc else "")).lower()).strip("_")
        model_id = f"custom_{slug[:40]}"
        if mod_pref == "auto":
            lower = f"{clean_repo} {inc}".lower()
            if any(k in lower for k in ("video", "wan", "ltx", "minimax", "hunyuan")):
                resolved_mod = "video_audio"
            elif any(k in lower for k in ("flux", "image", "sdxl", "z-image")):
                resolved_mod = "image"
            else:
                resolved_mod = "llm_vlm"
        else:
            resolved_mod = mod_pref
        short_name = clean_repo.split("/")[-1]
        final_name = disp or (f"{short_name} ({inc})" if inc else short_name)
        arch_guess = (
            "gguf"
            if ("gguf" in clean_repo.lower() or ".gguf" in inc.lower())
            else ("diffusers_image" if resolved_mod == "image" else "transformers")
        )
        spec = OpenModelSpec.from_custom_dict(
            {
                "id": model_id,
                "name": final_name,
                "repo_id": clean_repo,
                "include_pattern": inc,
                "modality": resolved_mod,
                "pipeline_arch": arch_guess,
                "category": f"自定义 HuggingFace 仓库 ({clean_repo})",
                "approx_size_gb": 0.0,
                "is_custom": True,
            }
        )
        MODEL_SPEC_MAP[spec.id] = spec
        idx = next((i for i, s in enumerate(self.custom_models) if s.id == spec.id), -1)
        if idx >= 0:
            self.custom_models[idx] = spec
        else:
            self.custom_models.append(spec)
        self._save_persisted_custom_models()
        self.select_model(spec.id)
        self.status_message = tr(
            f"已添加自定义模型「{final_name}」({clean_repo})，连接 Colab 后即可并发拉取至 Google Drive。",
            f"Added custom model '{final_name}' ({clean_repo}). Connect to Colab to download weights to Google Drive.",
        )
        self.state_changed.emit()

    def remove_custom_hf_model(self, model_id: str) -> None:
        spec = MODEL_SPEC_MAP.get(model_id)
        if not spec or not spec.is_custom:
            return
        self.custom_models = [s for s in self.custom_models if s.id != model_id]
        MODEL_SPEC_MAP.pop(model_id, None)
        self._save_persisted_custom_models()
        if self.selected_model_id == model_id:
            self.select_model(OPEN_MODEL_CATALOG[0].id)
        else:
            self.state_changed.emit()

        base = self.normalized_base_url
        if self.is_connected and base:

            def worker() -> None:
                try:
                    r = requests.post(
                        f"{base}/minimax_api/custom_model/remove",
                        json={"model_id": model_id, "delete_weights": False},
                        timeout=20,
                    )
                    if r.status_code == 200:
                        data = r.json()
                        self._dispatch_ui(lambda: self._apply_status_response(data, update_status_msg=True))
                except Exception:
                    pass

            threading.Thread(target=worker, daemon=True).start()


    # ─── Remote Config Endpoints (Idle, API Key, Context) ────────────────────

    def update_idle_timeout_config(self, minutes: int) -> None:
        self.idle_timeout_minutes = minutes
        self._save_setting("idleTimeoutMinutes", minutes)
        self.state_changed.emit()

        base = self.normalized_base_url
        if not self.is_connected or not base:
            return

        def worker() -> None:
            try:
                r = requests.post(
                    f"{base}/minimax_api/config_idle",
                    json={"idle_timeout_minutes": minutes},
                    timeout=20,
                )
                if r.status_code == 200:
                    data = r.json()
                    self._dispatch_ui(lambda: self._apply_status_response(data, update_status_msg=False))
            except Exception:
                pass

        threading.Thread(target=worker, daemon=True).start()

    def set_api_key_enabled(self, enabled: bool) -> None:
        self.api_key_enabled = bool(enabled)
        self._save_setting("apiKeyEnabled", self.api_key_enabled)
        self.state_changed.emit()
        self.sync_api_key_to_colab()

    def regenerate_api_key(self) -> None:
        self.api_access_key = "sk-colab-" + secrets.token_hex(10)
        self._save_setting("apiAccessKey", self.api_access_key)
        self.status_message = tr("已生成新的随机 API Key。", "Generated a new random API Key.")
        self.state_changed.emit()
        if self.is_connected:
            self.sync_api_key_to_colab()

    def sync_api_key_to_colab(self, custom_key: Optional[str] = None) -> None:
        if custom_key is not None:
            self.api_access_key = custom_key.strip()
            self._save_setting("apiAccessKey", self.api_access_key)
        base = self.normalized_base_url
        if not self.is_connected or not base:
            return
        payload_key = self.api_access_key.strip() if self.api_key_enabled else ""

        def worker() -> None:
            try:
                r = requests.post(
                    f"{base}/minimax_api/config_api_key",
                    json={"api_key": payload_key},
                    timeout=20,
                )
                if r.status_code == 200:
                    data = r.json()
                    self._dispatch_ui(lambda: self._apply_status_response(data, update_status_msg=False))
            except Exception:
                pass

        threading.Thread(target=worker, daemon=True).start()

    def sync_context_length_to_colab(self) -> None:
        base = self.normalized_base_url
        if not self.is_connected or not base:
            return
        ctx_tokens = self.context_length_tokens

        def worker() -> None:
            try:
                r = requests.post(
                    f"{base}/minimax_api/config_context",
                    json={"context_length": ctx_tokens},
                    timeout=20,
                )
                if r.status_code == 200:
                    data = r.json()
                    self._dispatch_ui(lambda: self._apply_status_response(data, update_status_msg=False))
            except Exception:
                pass

        threading.Thread(target=worker, daemon=True).start()


    # ─── ComfyUI Studio Actions ──────────────────────────────────────────────

    def start_comfyui(self, force_restart: bool = False, auto_open_browser: bool = True) -> None:
        base = self.normalized_base_url
        if not self.is_connected or not base:
            self.status_message = tr(
                "请先连接或唤醒 Colab 云端实例。",
                "Please connect or wake a Colab cloud runtime first.",
            )
            self.state_changed.emit()
            return

        self.comfy_starting = True
        self.status_message = tr(
            "正在云端部署启动 ComfyUI 节点画布与 Cloudflare 加密隧道...",
            "Deploying ComfyUI node canvas & Cloudflare HTTPS tunnel on cloud...",
        )
        self.state_changed.emit()

        payload = {
            "unload_existing": bool(self.comfy_unload_others_on_start),
            "force_restart": bool(force_restart),
        }

        def worker() -> None:
            try:
                r = requests.post(f"{base}/minimax_api/comfyui/start", json=payload, timeout=30)
                if r.status_code == 200:
                    data = r.json()
                    self._dispatch_ui(lambda: self._apply_status_response(data, update_status_msg=True))
                for _ in range(180):
                    time.sleep(1.5)
                    sr = requests.get(
                        f"{base}/minimax_api/status",
                        params={"model_id": self.selected_model_id},
                        timeout=22,
                    )
                    if sr.status_code != 200:
                        break
                    sdata = sr.json()
                    self._dispatch_ui(lambda sd=sdata: self._apply_status_response(sd, update_status_msg=False))
                    comfy = sdata.get("comfyui") or {}
                    pub_url = str(comfy.get("public_url") or "")
                    if comfy.get("is_running") and pub_url and not comfy.get("is_starting"):
                        if auto_open_browser:
                            webbrowser.open(pub_url)
                        break
            except Exception as exc:
                msg = tr(f"启动 ComfyUI 异常：{exc}", f"Error starting ComfyUI: {exc}")
                self._dispatch_ui(lambda: self._set_status_and_log(msg))
            finally:

                def done() -> None:
                    self.comfy_starting = False
                    self.state_changed.emit()

                self._dispatch_ui(done)

        threading.Thread(target=worker, daemon=True).start()

    def stop_comfyui(self) -> None:
        base = self.normalized_base_url
        if not base:
            return
        self.status_message = tr(
            "正在同步工作流至云盘并停止 ComfyUI 服务...",
            "Syncing workflows to Google Drive and stopping ComfyUI...",
        )
        self.state_changed.emit()

        def worker() -> None:
            try:
                r = requests.post(f"{base}/minimax_api/comfyui/stop", json={}, timeout=35)
                if r.status_code == 200:
                    data = r.json()
                    self._dispatch_ui(lambda: self._apply_status_response(data, update_status_msg=True))
            except Exception as exc:
                self._dispatch_ui(
                    lambda: self._set_status_and_log(
                        tr(f"停止 ComfyUI 异常：{exc}", f"Error stopping ComfyUI: {exc}")
                    )
                )

        threading.Thread(target=worker, daemon=True).start()

    def free_comfy_vram(self) -> None:
        base = self.normalized_base_url
        if not base:
            return

        def worker() -> None:
            try:
                r = requests.post(f"{base}/minimax_api/comfyui/free_vram", json={}, timeout=20)
                if r.status_code == 200:
                    data = r.json()
                    self._dispatch_ui(lambda: self._apply_status_response(data, update_status_msg=True))
            except Exception as exc:
                self._dispatch_ui(
                    lambda: self._set_status_and_log(
                        tr(f"清理显存异常：{exc}", f"Error freeing VRAM: {exc}")
                    )
                )

        threading.Thread(target=worker, daemon=True).start()

    def sync_comfy_drive(self) -> None:
        base = self.normalized_base_url
        if not base:
            return
        self.comfy_syncing_drive = True
        self.status_message = tr(
            "正在将 ComfyUI 自定义节点、模型与工作流双向同步至 Google Drive...",
            "Syncing ComfyUI custom nodes, models & workflows to Google Drive...",
        )
        self.state_changed.emit()

        def worker() -> None:
            try:
                r = requests.post(f"{base}/minimax_api/comfyui/sync_drive", json={}, timeout=90)
                if r.status_code == 200:
                    data = r.json()
                    self._dispatch_ui(lambda: self._apply_status_response(data, update_status_msg=True))
            except Exception as exc:
                self._dispatch_ui(
                    lambda: self._set_status_and_log(
                        tr(f"同步云盘异常：{exc}", f"Error syncing to Google Drive: {exc}")
                    )
                )
            finally:

                def done() -> None:
                    self.comfy_syncing_drive = False
                    self.state_changed.emit()

                self._dispatch_ui(done)

        threading.Thread(target=worker, daemon=True).start()

    def download_comfy_weight(self, url_or_repo: str, filename: str, subfolder: str) -> None:
        src = (url_or_repo or "").strip()
        if not src:
            self.status_message = tr(
                "请先填写模型直链 URL 或 HuggingFace Repo ID。",
                "Please enter a direct model URL or Hugging Face Repo ID first.",
            )
            self.state_changed.emit()
            return
        base = self.normalized_base_url
        if not self.is_connected or not base:
            self.status_message = tr(
                "请先连接或唤醒 Colab 云端实例。",
                "Please connect or wake a Colab cloud runtime first.",
            )
            self.state_changed.emit()
            return

        self.comfy_downloading_weight = True
        self.status_message = tr(
            f"正在 8 线程极速下载权重至 ComfyUI/models/{subfolder}...",
            f"8-thread downloading weights to ComfyUI/models/{subfolder}...",
        )
        self.state_changed.emit()

        payload = {
            "url_or_repo": src,
            "filename": (filename or "").strip(),
            "subfolder": subfolder,
            "hf_token": self.hf_token.strip(),
        }

        def worker() -> None:
            try:
                r = requests.post(f"{base}/minimax_api/comfyui/download_weight", json=payload, timeout=25)
                if r.status_code == 200:
                    data = r.json()
                    self._dispatch_ui(lambda: self._apply_status_response(data, update_status_msg=True))
                while True:
                    time.sleep(1.5)
                    sr = requests.get(
                        f"{base}/minimax_api/status",
                        params={"model_id": self.selected_model_id},
                        timeout=22,
                    )
                    if sr.status_code != 200:
                        break
                    sdata = sr.json()
                    self._dispatch_ui(lambda sd=sdata: self._apply_status_response(sd, update_status_msg=False))
                    comfy = sdata.get("comfyui") or {}
                    if not comfy.get("is_downloading_weight", False):
                        break
            except Exception as exc:
                self._dispatch_ui(
                    lambda: self._set_status_and_log(
                        tr(f"下载 ComfyUI 权重异常：{exc}", f"Error downloading ComfyUI weight: {exc}")
                    )
                )
            finally:

                def done() -> None:
                    self.comfy_downloading_weight = False
                    self.state_changed.emit()

                self._dispatch_ui(done)

        threading.Thread(target=worker, daemon=True).start()

    def install_comfy_pack(self, pack_id: str, open_when_ready: bool = True) -> None:
        base = self.normalized_base_url
        if not self.is_connected or not base:
            self.status_message = tr(
                "请先连接或唤醒 Colab 云端实例。",
                "Please connect or wake a Colab cloud runtime first.",
            )
            self.state_changed.emit()
            return

        self.comfy_installing_pack_id = pack_id
        self.status_message = tr(
            "正在云端一键配齐预置工作流模型包并写入全中文节点模板...",
            "Installing preset workflow pack & generating guided node templates on cloud...",
        )
        self.state_changed.emit()

        payload = {
            "pack_id": pack_id,
            "auto_start": True,
            "hf_token": self.hf_token.strip(),
        }

        def worker() -> None:
            try:
                r = requests.post(f"{base}/minimax_api/comfyui/install_pack", json=payload, timeout=30)
                if r.status_code == 404:
                    self._dispatch_ui(
                        lambda: self._set_status_and_log(
                            tr(
                                "当前云端服务端版本较旧，请点击左侧「唤醒实例并部署」热更新服务端代码。",
                                "Cloud server version is outdated. Click 'Wake & Deploy' on the left to hot-update the server.",
                            )
                        )
                    )
                    return
                if r.status_code == 200:
                    data = r.json()
                    self._dispatch_ui(lambda: self._apply_status_response(data, update_status_msg=True))
                for _ in range(600):
                    time.sleep(1.5)
                    sr = requests.get(
                        f"{base}/minimax_api/status",
                        params={"model_id": self.selected_model_id},
                        timeout=22,
                    )
                    if sr.status_code != 200:
                        break
                    sdata = sr.json()
                    self._dispatch_ui(lambda sd=sdata: self._apply_status_response(sd, update_status_msg=False))
                    comfy = sdata.get("comfyui") or {}
                    busy = (
                        bool(comfy.get("is_downloading_weight"))
                        or bool(comfy.get("installing_pack_id"))
                        or bool(comfy.get("is_starting"))
                    )
                    if not busy:
                        pub_url = str(comfy.get("public_url") or "")
                        if open_when_ready and comfy.get("is_running") and pub_url:
                            webbrowser.open(pub_url)
                        break
            except Exception as exc:
                self._dispatch_ui(
                    lambda: self._set_status_and_log(
                        tr(f"安装预置工作流包异常：{exc}", f"Error installing preset workflow pack: {exc}")
                    )
                )
            finally:

                def done() -> None:
                    self.comfy_installing_pack_id = ""
                    self.state_changed.emit()

                self._dispatch_ui(done)

        threading.Thread(target=worker, daemon=True).start()

    def pull_comfy_output_media(self, item: ComfyOutputMediaItem) -> None:
        base = self.normalized_base_url
        if not base:
            return
        encoded_rel = "/".join(urllib.parse.quote(seg, safe="") for seg in item.rel_path.split("/"))
        url = f"{base}/minimax_api/comfyui/output_media/{encoded_rel}"
        save_name = "comfy_" + Path(item.filename).name
        dst = get_local_save_dir() / save_name
        self.status_message = tr(
            f"正在从云端 ComfyUI 回传成片 {item.filename}...",
            f"Pulling output media {item.filename} from cloud ComfyUI...",
        )
        self.state_changed.emit()

        def worker() -> None:
            try:
                r = requests.get(url, timeout=180)
                if r.status_code == 200 and r.content:
                    dst.write_bytes(r.content)

                    def on_saved() -> None:
                        self.status_message = tr(
                            f"已回传保存至本地：{dst.name}",
                            f"Saved locally: {dst.name}",
                        )
                        self.refresh_local_media_gallery(auto_select_first=False)
                        self.select_local_media(dst, auto_play=True)
                        self.state_changed.emit()

                    self._dispatch_ui(on_saved)
                else:
                    code = r.status_code
                    self._dispatch_ui(
                        lambda: self._set_status_and_log(
                            tr(f"回传成片失败 (HTTP {code})", f"Failed to pull output media (HTTP {code})")
                        )
                    )
            except Exception as exc:
                self._dispatch_ui(
                    lambda: self._set_status_and_log(
                        tr(f"回传成片异常：{exc}", f"Error pulling output media: {exc}")
                    )
                )

        threading.Thread(target=worker, daemon=True).start()
