# EasyColab

[简体中文](./README.md) | **English**

**EasyColab** is a native Multimodal AI Studio built for **macOS, Windows, iOS / iPadOS, and Android**, powered by Google Colab high-VRAM cloud GPUs (macOS native SwiftUI client + Windows PySide6/Qt6 desktop client + iOS/iPadOS pure SwiftUI client + Android pure Kotlin Jetpack Compose client + cloud multi-model acceleration engine).

Optimized out of the box for **Google Colab G4 (`NVIDIA RTX PRO 6000 Blackwell` · `96 GB` VRAM + `176 GB` System RAM)** as well as `H100 / A100 / L4` runtimes, EasyColab supports headless one-click runtime wake & deployment, persistent model caching on Google Drive, multi-model VRAM co-residency, real-time spline telemetry charts, instant Chinese/English UI switching, and automatic idle runtime release to save Compute Units.

![EasyColab Studio Screenshot](./shot.png)

---

## Key Features

- **Cross-Platform Native Studio + Bilingual UI Toggle + Interactive Onboarding (1:1 Parity Across macOS & Windows)**
  - **macOS Client** is crafted natively with SwiftUI + AppKit; **Windows Client** is built with PySide6 (Qt6 + FFmpeg multimedia pipeline) featuring Windows 11 immersive light/dark title bars and high-DPI scaling. Both include a **4-step interactive onboarding wizard** on first launch with zero-config bridge initialization.
  - Built-in **one-click Chinese / English (`中文 / EN`) live UI toggle** (defaults to Chinese), persisting language preferences automatically without restarting the app.
  - Real-time smooth Catmull-Rom spline telemetry charts for cloud **GPU VRAM / System RAM / Disk Space** (supporting both split and combined overlay modes), paired with official **Compute Unit (CU) balance** and hourly burn-rate tracking.
  - Built-in **30-minute idle auto-sleep watchdog** and one-click **"Release All Instances"** to prevent forgotten runtimes from draining your CU quota.

- **Four Flagship Open-Source Multimodal Engines Out of the Box**
  1. **`MiniMax-H3 (Native BF16)` · 4–15s Cinematic Video with Native Stereo Audio**
     - Supports Text-to-Video+Audio, First-Frame-to-Video, and First/Last-Frame camera transitions, natively generating `24 FPS` video paired with `32 kHz` stereo soundscapes, dialogue, and music.
     - **G4 176 GB Dual-Backbone DDR5 Hot-Standby Acceleration**: Keeps both the `32B Text Encoder` and `33B DiT Backbone` resident in high-speed DDR5 RAM — delivering `0 ms` prompt reuse on consecutive generations and ~`8–12s` PCIe swap-in when editing prompts.
  2. **`ComfyUI Node Studio` · Google Drive Persistence + 4 Curated Ready-to-Run Workflow Packs**
     - One-click deployment of ComfyUI + ComfyUI-Manager over a free encrypted Cloudflare HTTPS tunnel, with `custom_nodes`, `models`, and `workflows` automatically symlinked and persisted to Google Drive.
     - Ships with four curated Image-to-Video & First/Last-Frame workflow packs (**Wan2.2 14B**, **MiniMax-H3 Turbo**, **LTX-2.3 (22B)**, and **HunyuanVideo 1.5**) featuring one-click model provisioning.
  3. **`Qwen3.8-27B (UD-Q4_K_M + MTP Speculative Decoding / BF16)` · 100 tok/s Vision Chat & Dual-Protocol API Gateway**
     - Supports up to `256K` context length, deep chain-of-thought reasoning, and multimodal image analysis / prompt reverse-engineering.
     - Built-in public API gateway compatible with both **OpenAI (`/v1/chat/completions`)** and **Anthropic (`/v1/messages`)** (with Bearer / `x-api-key` authentication), ready to plug directly into **Claude Code**, **Cursor**, and custom agent workflows.
  4. **`Qwen-Image-2.1` & `Z-Image-Turbo` · 2K Poster Generation & Multi-Image Instruction Editing**
     - High-fidelity bilingual typography rendering, natural-language multi-image editing, and 8-step ultra-fast photorealistic generation. All generated MP4 videos and PNG images are automatically pulled back to your local machine (macOS: `~/Movies/EasyColab`, Windows: `%USERPROFILE%\Videos\EasyColab`).

---

## Quick Start

### System Requirements
- **Operating System**:
  - **macOS**: macOS 13.0 (Ventura) or later (Apple Silicon / macOS Sonoma & Sequoia recommended)
  - **Windows**: Windows 10 (1903+) or Windows 11 64-bit (x64)
  - **iOS / iPadOS**: iOS 16.0 or later (build & sign locally from open-source `ios_app/` via Xcode, or sideload `.ipa` via AltStore / SideStore / Sideloadly / TrollStore)
  - **Android**: Android 8.0 (API 26) or later (direct signed `.apk` via GitHub Releases, or build from open-source `android_app/`)
- **Cloud Account**: A Google account subscribed to **Google Colab Pro / Pro+ / Google AI Ultra** with available Compute Units (CU). Free-tier users should follow the *"Run via Official Google Colab Web UI"* section below.

---

### macOS Client

#### Option 1: Build & Run Locally with One Command (Recommended, No Gatekeeper Prompt)
Requires Xcode Command Line Tools (`xcode-select --install` if not already installed):

```bash
git clone https://github.com/<your-username>/EasyColab.git
cd EasyColab
bash macos_app/build_macos_app.sh
open EasyColab.app
```

> The build script automatically bundles `app.py`, `colab_bridge.py`, and `EasyColab_Server.ipynb` into `EasyColab.app/Contents/Resources/`. You can drag `EasyColab.app` directly into `/Applications` for standalone use; the first time you click **Bind**, EasyColab automatically creates an isolated Python environment at `~/Library/Application Support/EasyColab/venv` and installs the bridge dependencies.

#### Option 2: Download Prebuilt `.app` from GitHub Releases
If you download an unsigned/unnotarized `.app` archive and macOS displays *"Cannot verify developer / App is damaged"* on first launch, clear the quarantine attribute once in Terminal:

```bash
xattr -cr /Applications/EasyColab.app
```

---

### Windows Client

#### Option 1: Download Portable `.zip` (Zero Python Dependency, Recommended)
1. Download `EasyColab-Windows-x64.zip` from GitHub Releases (or from repository **Actions -> Build EasyColab Windows App** artifacts).
2. Extract to any folder and double-click `EasyColab\EasyColab.exe` (bundles an embedded Python runtime, Qt6 UI libraries, FFmpeg audio/video codecs, and the `colab_bridge` cloud launcher — no system Python required).
3. If Windows SmartScreen displays *"Windows protected your PC"*, click **More info -> Run anyway**.

#### Option 2: Build Standalone `.exe` Locally on Windows
With 64-bit Python 3.10–3.13 installed, run the one-click build script from the repository root to generate `dist\EasyColab\EasyColab.exe` and `EasyColab-Windows-x64.zip`:

```bat
REM Double-click or run in CMD:
windows_app\build_windows_app.bat
```

Or in PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\windows_app\build_windows_app.ps1
```

#### Option 3: Run Directly from Source (Windows / macOS Cross-Platform Preview)

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS:   source .venv/bin/activate
pip install -r windows_app/requirements-windows.txt
python windows_app/easycolab_win.py
```

---

### iOS / iPadOS Client (Open-Source Build & Sideload `.ipa`)

Crafted natively in pure SwiftUI for iPhone and iPad (source code in [`ios_app/`](./ios_app)) with a zero-Python pure-Swift Colab provisioning bridge, supporting 1-tap Google OAuth & headless G4 (96GB) wake, background/lock-screen job recovery, automatic MP4/PNG export to Photos, custom HuggingFace repo import, and cloud idle auto-sleep protection.

<p align="center">
  <img src="./app_1.PNG" alt="EasyColab Mobile Studio & 1-Tap ComfyUI Workflow Packs" width="45%" />
  &nbsp;&nbsp;&nbsp;
  <img src="./app_2.PNG" alt="EasyColab Mobile Cloud GPU Center & 1-Tap G4 Wake" width="45%" />
</p>

#### Option 1: One-Command Local Build & Install to iPhone / iPad (Recommended)
Works with both a **free personal Apple ID** (7-day Xcode signing) and a paid Apple Developer account (365-day signing). Connect your iPhone or iPad to a Mac with Xcode installed:

```bash
# Generates an isolated Xcode project inside git-ignored build/ (never writes your Team ID to tracked files) & installs Release build
bash ios_app/install_release_iphone.sh

# Or open the generated project in Xcode GUI to select your Personal Team manually:
bash ios_app/install_release_iphone.sh --open-xcode
```

#### Option 2: Sideload Prebuilt `EasyColab-iOS.ipa`
1. Download `EasyColab-iOS.ipa` from **[GitHub Releases](../../releases)** (or build it locally on macOS via `bash ios_app/build_ios_ipa.sh`, which outputs an ad-hoc unsigned `.ipa` with zero personal Team ID).
2. Sideload `EasyColab-iOS.ipa` onto your iPhone or iPad using **AltStore**, **SideStore**, **Sideloadly**, or **TrollStore**.

#### Option 3: Launch Directly in iOS Simulator on macOS

```bash
bash ios_app/run_ios_simulator.sh
```

---

### Android Client (Standalone Signed `.apk` & Open-Source Build)

Built natively in pure Kotlin + Jetpack Compose Material 3 (source code in [`android_app/`](./android_app)) with a zero-Python pure-Kotlin Colab provisioning & Jupyter WebSocket bridge, supporting 1-tap Google OAuth2 sign-in, headless G4 (96GB) wake, automatic MP4/PNG export to Android System Gallery (`Movies/EasyColab` & `Pictures/EasyColab`), and background/screen-lock job recovery.

#### Option 1: Download Prebuilt Signed `.apk` (Recommended)
1. Visit **[GitHub Releases](../../releases)** and download the latest signed **`EasyColab-Android.apk`**.
2. Open `EasyColab-Android.apk` on your Android phone or tablet (Android 8.0+) to install directly.

#### Option 2: Build & Install Locally from Source
With JDK 17+ and Android SDK installed (auto-detected if Android Studio is installed; automatically generates a local signing key inside git-ignored `android_app/.signing/` if none exists):

```bash
# Build standalone signed EasyColab-Android.apk in repo root
bash android_app/build_android_apk.sh

# Or build, install & launch directly on a connected ADB Android device
bash android_app/install_release_android.sh
```

---

### Run via Official Google Colab Web UI (For Colab Free Tier / Browser Users)
1. Open [Google Colab](https://colab.research.google.com/) and upload `EasyColab_Server.ipynb` from the repository root (or click **Export / Locate `.ipynb` Notebook** inside the app's Onboarding Guide).
2. In the Colab menu bar, select `Runtime -> Change runtime type`, choose `G4` / `A100` / `L4` GPU, and run the cells in order.
3. Copy the printed `https://xxxx.gradio.live` URL into the **Server URL** field on the left sidebar of the desktop client and click **Connect**.

---

## Privacy & Security Best Practices

1. **Screen-Recording / Screenshot Redaction Mode**: Next to the **Server URL** input in the left sidebar, toggle **Redact / Mask Mode** (eye icon on macOS, **Mask** button on Windows) before recording tutorials, streaming, or sharing screenshots. This masks your temporary `*.gradio.live` and `*.trycloudflare.com` tunnel URLs as well as your Google account email so others cannot access your cloud GPU.
2. **Keep API Key Authentication Enabled**: When exposing the Qwen API Gateway to external tools, keep **Enable API Key Auth** turned on.
3. **Local Credentials & Data Locations**:
   - Google OAuth tokens are stored strictly on your local machine at `~/.config/colab-cli/token.json` (`%USERPROFILE%\.config\colab-cli\token.json` on Windows) and are never uploaded to any third-party server.
   - Windows client settings are stored at `%LOCALAPPDATA%\EasyColab\settings.json`, and generated media is saved by default to `%USERPROFILE%\Videos\EasyColab` (`~/Movies/EasyColab` on macOS).

---

## Disclaimer & Compliance

- **Unofficial Independent Project**: EasyColab is an independent, community-developed open-source client and companion toolkit. **It is not affiliated with, endorsed by, or sponsored by Google LLC, Google Colab, MiniMax, Alibaba Qwen, or any of their affiliates.**
- **Platform Terms of Service (ToS) Notice**:
  - The headless *"One-Click Wake & Deploy"* feature interacts with your own Paid Compute Units via the open-source community library [`google-colab-cli`](https://pypi.org/project/google-colab-cli/). **It is strongly recommended solely for reasonable personal use on accounts with an active Colab Pro / Pro+ / Google AI Ultra subscription.**
  - Do not abuse headless background connections on the Google Colab Free Tier, and never use it for cryptocurrency mining, multi-account farming, or unauthorized compute reselling. Connecting third-party clients to cloud runtimes may be subject to platform policy changes; users assume full responsibility for evaluating and bearing any account-related risks. For a 100% official browser-based workflow, use the bundled `EasyColab_Server.ipynb`.
- **Model & Upstream Component Licenses**:
  - This repository **does not include or distribute any model weights or GPL source code**. All model weights are downloaded directly by the user at runtime from official Hugging Face repositories and remain subject to their respective upstream licenses (e.g., *MiniMax-H3 Community License Agreement*, *Apache-2.0*, *Tongyi Qianwen License*, etc.).
  - The cloud ComfyUI Studio clones the official repository on demand inside the user's personal cloud VM and communicates over an out-of-process HTTP API; ComfyUI itself is licensed under **GPL-3.0**.

---

## Acknowledgements

Special thanks to the following open-source projects and model teams:
- [DiffSynth-Studio](https://github.com/modelscope/DiffSynth-Studio)
- [ComfyUI](https://github.com/comfyanonymous/ComfyUI) & [ComfyUI-Manager](https://github.com/ltdrdata/ComfyUI-Manager)
- [MiniMax-H3](https://github.com/MiniMax-AI/MiniMax-H3)
- [Qwen](https://github.com/QwenLM) & [Unsloth](https://github.com/unslothai/unsloth)
- [llama.cpp](https://github.com/ggml-org/llama.cpp)
- [google-colab-cli](https://pypi.org/project/google-colab-cli/)

---

## License

The source code of this project is released under the [Apache License 2.0](./LICENSE).
