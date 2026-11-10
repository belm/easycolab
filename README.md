# EasyColab

**简体中文** | [English](./README_EN.md)

**EasyColab** 是一款专为 **macOS、Windows、iOS / iPadOS 与 Android** 原生打造的 Google Colab 云端大显存多模态 AI 创作工作台（macOS SwiftUI 原生客户端 + Windows PySide6/Qt6 桌面客户端 + iOS/iPadOS 纯 SwiftUI 原生客户端 + Android 纯 Kotlin Jetpack Compose 原生客户端 + 云端多模型加速引擎）。

默认适配 **Google Colab G4（NVIDIA RTX PRO 6000 Blackwell · `96 GB` 显存 + `176 GB` 系统内存）** 以及 `H100 / A100 / L4` 实例，支持免开网页一键唤醒部署、Google Drive 云盘权重永久复用、多模型显存共驻、实时算力折线图监控、中英文双语界面一键切换与闲置自动释放省额度。

![EasyColab 工作台界面预览](./shot.png)

### 使用经过鉴权的公网入口

可以在同一台 VM 上重新部署。如果从原版升级时 ComfyUI 正占用端口 `8188`，请先停止该 ComfyUI 进程，再启动新版。此后在同一台 VM 上热重启 EasyColab 时，它会尝试重新接管仍在运行的 ComfyUI 画布。点击「唤醒并部署」后，桌面客户端会生成管理密码，并按服务地址明文保存在本机设置中。打开 Gradio 或 ComfyUI 时，在浏览器的登录框填写用户名 `easycolab`，密码可从桌面端服务地址旁复制。手动运行 Notebook 时，在隐藏输入框设置 24 至 256 位管理密码（字母、数字、下划线或连字符），再将服务地址和密码填入桌面端。重开客户端后会自动取回该服务地址的管理密码。

OpenAI 和 Anthropic 兼容接口使用桌面端「API 网关」中的独立推理密钥。管理密码只交给可信的管理员。运行时使用 nginx 和 OpenSSL 保护两个隧道，支持媒体流和 WebSocket。直接启动 `app.py` 需要在 Linux 环境安装这两个程序，并在提示时输入管理密码。

Drive 无浏览器挂载仍可能将带有 Colab 和 Cloud Platform 授权的 Google 刷新令牌复制到 VM。与服务同用户运行的第三方节点可以读取它。仅安装可信节点，业务资料使用独立账号隔离。

---

## 核心特性

- **双平台桌面级创作体验 + 中英文双语切换 + 新手交互引导（macOS & Windows 1:1 全功能对齐）**
  - **macOS 端**采用纯原生 SwiftUI + AppKit 构建，**Windows 端**采用 PySide6 (Qt6 + FFmpeg 多媒体管线) 构建并适配 Windows 11 沉浸式深浅色标题栏与高分屏缩放；首次启动均自带 **4 步交互式新手引导**，零配置自动初始化连接组件。
  - 支持 **中英文（简体中文 / English）界面实时一键切换**（默认显示中文），状态与偏好自动记忆，无需重启应用。
  - 实时绘制云端 **GPU 显存 / 系统内存 / 磁盘空间** 平滑曲线走势图（支持分项与同屏叠加模式），同步显示官方真实剩余 **CU 计算单元** 与每小时消耗速率。
  - 内置 **30 分钟闲置自动休眠看门狗** 与一键「断开并释放实例」，杜绝忘记关机空耗算力额度。

- **四大旗舰开源多模态引擎开箱即用**
  1. **`MiniMax-H3 (BF16 原生满血)` · 4～15 秒电影级有声视频**
     - 支持文生有声视频、首帧图生视频、首尾帧过渡控镜，原生输出 `24 FPS` 画面 + `32 kHz` 立体声音轨。
     - **G4 176GB 双主干内存热备加速**：自动将 `32B 文本编码器` 与 `33B DiT 主干` 常驻高速 DDR5 内存，同提示词连抽 `0 ms` 瞬回，修改新提示词整块 PCIe 换入解析仅需约 `8～12 秒`。
  2. **`ComfyUI 节点工作台` · 云盘持久化 + 4 套零基础预置工作流包**
     - 一键部署 ComfyUI + Manager 并开通免费 Cloudflare HTTPS 加密隧道，所有 `custom_nodes`、`models` 与 `workflows` 自动软链/同步至 Google Drive。
     - 内置 **万相 Wan2.2 14B**、**MiniMax-H3 Turbo**、**LTX-2.3 (22B)**、**混元 HunyuanVideo 1.5** 四套「一键配齐模型 + 节点指引」的图生视频与首尾帧运镜工作流。
  3. **`Qwen3.8-27B (UD-Q4_K_M + MTP 投机解码 / BF16)` · 100 tok/s 视觉对话与双协议网关**
     - 支持最高 `256K` 上下文、长思维链推理、多模态看图反推提示词。
     - 内置兼容 **OpenAI (`/v1/chat/completions`)** 与 **Anthropic (`/v1/messages`)** 的公网 API 网关（支持 Bearer / `x-api-key` 鉴权），可直接接入 **Claude Code**、**Cursor** 等开发工具。
  4. **`Qwen-Image-2.1` & `Z-Image-Turbo` · 2K 海报生图与多图指令修图**
     - 支持高质感中英文排版直出、双图自然语言指令修图与 8 步极速出图；所有生成的 MP4 / PNG 自动回传至本地目录（macOS: `~/Movies/EasyColab`，Windows: `%USERPROFILE%\Videos\EasyColab`）。

---

## 快速开始

### 系统要求
- **操作系统**：
  - **macOS**：macOS 13.0 (Ventura) 或更高版本（推荐 Apple Silicon / macOS Sonoma & Sequoia）
  - **Windows**：Windows 10 (1903+) 或 Windows 11 64 位 (x64)
  - **iOS / iPadOS**：iOS 16.0 或更高版本（支持 Mac 本地源码真机签名安装或通过 AltStore / SideStore / Sideloadly / TrollStore 侧载 `.ipa`）
  - **Android**：Android 8.0 (API 26) 或更高版本（支持从 GitHub Releases 下载签名 `.apk` 直接安装，或从 `android_app/` 源码一键编译）
- **云端账号**：开通了 **Google Colab Pro / Pro+ / Google AI Ultra**（拥有可用 CU 计算单元）的 Google 账号；免费版用户请使用下方「Google Colab 官方网页端运行 `.ipynb`」。

---

### macOS 客户端

#### 方式一：本地一行命令编译运行（推荐，无 Gatekeeper 拦截）
只需系统装有 Xcode Command Line Tools（若未安装可执行 `xcode-select --install`）：

```bash
git clone https://github.com/<your-username>/EasyColab.git
cd EasyColab
bash macos_app/build_macos_app.sh
open EasyColab.app
```

> 编译脚本会自动将 `app.py`、`colab_bridge.py`、`EasyColab_Server.ipynb` 打包进 `EasyColab.app/Contents/Resources/`。你可以将生成的 `EasyColab.app` 直接拖入 `/Applications` 独立使用；首次点击「绑定」时，应用会在 `~/Library/Application Support/EasyColab/venv` 自动创建隔离 Python 环境并安装连接组件。

#### 方式二：从 GitHub Releases 下载预编译 `.app`
若下载的是未经过 Apple Developer ID 公证的预编译 `.app`，首次打开若遇到 macOS 提示 *“无法验证开发者 / 已损坏”*，请在终端执行一次解除隔离命令：

```bash
xattr -cr /Applications/EasyColab.app
```

---

### Windows 客户端

#### 方式一：下载免安装绿色版 `.zip`（零 Python 依赖，推荐）
1. 从 GitHub Releases（或仓库 **Actions -> Build EasyColab Windows App** 构建产物）下载 `EasyColab-Windows-x64.zip`。
2. 解压到任意目录后，直接双击运行 `EasyColab\EasyColab.exe` 即可使用（已内置 Python 运行时、Qt6 界面库、FFmpeg 音视频解码器与 `colab_bridge` 云端唤醒组件，无需在电脑上安装 Python）。
3. 如遇 Windows SmartScreen 提示 *“Windows 已保护你的电脑”*，点击 **「更多信息」 -> 「仍要运行」** 即可。

#### 方式二：Windows 本地一键打包独立 `.exe`
若本机已安装 Python 3.10～3.13（64 位），在仓库根目录可直接一键创建隔离虚拟环境并编译生成 `dist\EasyColab\EasyColab.exe` 与 `EasyColab-Windows-x64.zip`：

```bat
REM 双击或在 CMD 中运行：
windows_app\build_windows_app.bat
```

或使用 PowerShell：

```powershell
powershell -ExecutionPolicy Bypass -File .\windows_app\build_windows_app.ps1
```

#### 方式三：在 macOS 上直接交叉打包 Windows 独立 `.exe`
若当前在 macOS 开发机上（已安装 `brew install mingw-w64`），无需 Windows 虚拟机即可直接交叉编译原生 Win32 GUI 启动器并组装完整的 `EasyColab-Windows-x64.zip`：

```bash
python3 windows_app/build_windows_from_mac.py
```

#### 方式四：源码开发模式直接运行（Windows / macOS 通用预览）

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS:   source .venv/bin/activate
pip install -r windows_app/requirements-windows.txt
python windows_app/easycolab_win.py
```

---

### iOS / iPadOS 客户端（开源源码自编译 & 侧载 `.ipa`）

iOS / iPadOS 端采用纯原生 SwiftUI 构建（源码位于 [`ios_app/`](./ios_app)），内置零 Python 依赖的纯 Swift 云端唤醒桥接引擎，支持一键 Google OAuth 授权唤醒 G4 (96GB) 实例、锁屏/切后台推理进度自动同步、高清有声 MP4 与 PNG 自动存入系统相册、自定义 HuggingFace 仓库导入以及云端闲置自动休眠保护。

<p align="center">
  <img src="./app_1.PNG" alt="EasyColab 移动端创作工作台与 ComfyUI 预设工作流包" width="45%" />
  &nbsp;&nbsp;&nbsp;
  <img src="./app_2.PNG" alt="EasyColab 移动端云算力中心与 G4 一键唤醒" width="45%" />
</p>

#### 方式一：Mac 本地一行命令编译并安装至 iPhone / iPad 真机（推荐）
支持**免费个人 Apple ID**（7 天自签）或付费 Apple Developer 账号（365 天签名）。将 iPhone / iPad 连接至安装了 Xcode 的 Mac（首次连接请在设备上开启「开发者模式」并信任电脑）：

```bash
# 自动生成临时隔离工程（位于被 Git 忽略的 build/ 目录，绝不写入或泄露你的 Team ID）并直装真机
bash ios_app/install_release_iphone.sh

# 或者在 Xcode 图形界面打开工程手动选择个人签名团队运行：
bash ios_app/install_release_iphone.sh --open-xcode
```

#### 方式二：通过侧载工具安装预编译 `EasyColab-iOS.ipa`
1. 从 **[GitHub Releases](../../releases)** 下载 `EasyColab-iOS.ipa`（或在 Mac 本地执行 `bash ios_app/build_ios_ipa.sh` 生成无开发者签名信息的纯净 `EasyColab-iOS.ipa`）。
2. 使用 **AltStore**、**SideStore**、**Sideloadly** 或 **TrollStore** 导入 `EasyColab-iOS.ipa` 自签安装即可。

#### 方式三：macOS 本地一键启动 iOS 模拟器预览

```bash
bash ios_app/run_ios_simulator.sh
```

---

### Android 客户端（独立安装包 `.apk` & 开源自编译）

Android 端采用纯原生 Kotlin + Jetpack Compose Material 3 构建（源码位于 [`android_app/`](./android_app)），内置零 Python 依赖的纯 Kotlin 云端唤醒与 Jupyter WebSocket 桥接引擎，支持一键 Google OAuth 授权跳回、免网页唤醒云端 G4 (96GB) 实例、高清有声 MP4 与 PNG 自动写入系统相册（`Movies/EasyColab` 与 `Pictures/EasyColab`）以及锁屏/切后台断点恢复。

#### 方式一：直接下载预编译 `.apk` 安装（推荐）
1. 前往本仓库 **[GitHub Releases](../../releases)** 页面下载最新签名安装包 **`EasyColab-Android.apk`**。
2. 在 Android 手机或平板（Android 8.0+）上直接点击安装即可使用。

#### 方式二：从源码本地一键编译签名 `.apk` 或直装手机
确保本机装有 JDK 17+ 与 Android SDK（如已安装 Android Studio 则自动识别，首次构建若无签名密钥会自动在被 Git 忽略的 `android_app/.signing/` 下生成本地证书）：

```bash
# 仅编译生成根目录 EasyColab-Android.apk
bash android_app/build_android_apk.sh

# 编译并通过 ADB 一键安装启动至已连接 USB / 无线调试的 Android 手机
bash android_app/install_release_android.sh
```

---

### Google Colab 官方网页端运行（适合 Colab 免费版 / 浏览器用户）
1. 打开 [Google Colab](https://colab.research.google.com/)，上传本仓库根目录下的 `EasyColab_Server.ipynb`（或在客户端引导页点击「导出 / 定位 `.ipynb` 笔记本」）。
2. 在 Colab 菜单栏选择 `代码执行程序 -> 更改运行时类型`，选择 `G4` / `A100` / `L4` GPU 并按顺序运行单元格。
3. 将输出的 `https://xxxx.gradio.live` 链接粘贴至桌面客户端左侧服务地址栏点击「连接」即可。

---

## 隐私与安全建议

1. **录屏 / 截图防泄密开关**：在左侧「服务地址」输入框旁提供了 **打码保护开关**（macOS 为眼睛图标，Windows 为「打码」按钮）。在录制教程、直播或截图分享前，请开启打码隐藏你的 `*.gradio.live` 与 `*.trycloudflare.com` 临时公网隧道域名及账号邮箱，防止他人通过链接蹭用你的云端 GPU。
2. **推理密钥**：外部工具通过 Bearer 或 `x-api-key` 提交 API 网关面板中的推理密钥。
3. **本地凭证与数据目录**：
   - 桥接程序读取本机 `~/.config/colab-cli/token.json`。无浏览器挂载 Drive 时，刷新令牌也会写入云端实例的 rclone 配置。
   - Windows 客户端本地配置文件位于 `%LOCALAPPDATA%\EasyColab\settings.json`，成片默认保存于 `%USERPROFILE%\Videos\EasyColab`。

---

## 免责声明与合规说明 (Disclaimer)

- **非官方独立项目**：EasyColab 是社区开发的独立开源客户端与辅助工具，**与 Google LLC、Google Colab、MiniMax、阿里巴巴通义千问（Qwen）等官方机构无任何隶属、赞助或背书关系**。
- **平台服务条款（ToS）提示**：
  - 客户端内的「免网页一键唤醒」功能底层基于开源社区库 [`google-colab-cli`](https://pypi.org/project/google-colab-cli/) 与自购付费计算单元（Paid Compute Units）交互，**强烈建议仅在已订阅 Colab Pro / Pro+ / Google AI Ultra 的自有付费账号上合理自用**。
  - 请勿在 Google Colab 免费层（Free Tier）上滥用无网页后台连接，严禁用于加密货币挖矿、批量多号滥用或违规算力转售。使用第三方客户端连接云端运行时可能受平台策略变更影响，相关账号风险由使用者自行评估并承担；若追求 100% 官方网页交互体验，请使用仓库内置的 `EasyColab_Server.ipynb`。
- **模型与上游组件许可证**：
  - 本仓库**不包含也不分发任何模型权重或 GPL 源码**。所有模型权重均由用户在运行时从 Hugging Face 官方仓库自行下载，须遵守各模型原始许可证（如 *MiniMax-H3 Community License Agreement*、*Apache-2.0*、*Tongyi Qianwen License* 等）。
  - 云端 ComfyUI 工作台在用户个人虚拟机内按需拉取官方仓库并通过独立进程 HTTP API 通信，ComfyUI 本体遵循其 **GPL-3.0** 协议。

---

## 致谢 (Acknowledgements)

感谢以下优秀的开源项目与模型团队：
- [DiffSynth-Studio](https://github.com/modelscope/DiffSynth-Studio)
- [ComfyUI](https://github.com/comfyanonymous/ComfyUI) & [ComfyUI-Manager](https://github.com/ltdrdata/ComfyUI-Manager)
- [MiniMax-H3](https://github.com/MiniMax-AI/MiniMax-H3)
- [Qwen](https://github.com/QwenLM) & [Unsloth](https://github.com/unslothai/unsloth)
- [llama.cpp](https://github.com/ggml-org/llama.cpp)
- [google-colab-cli](https://pypi.org/project/google-colab-cli/)

---

## License

本项目源代码基于 [Apache License 2.0](./LICENSE) 开源发布。
