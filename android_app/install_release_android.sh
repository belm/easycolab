#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
APK_PATH="${REPO_ROOT}/EasyColab-Android.apk"

# 1. Build latest signed Release APK
bash "${SCRIPT_DIR}/build_android_apk.sh"

# 2. Locate adb binary
ADB_BIN=""
if command -v adb >/dev/null 2>&1; then
    ADB_BIN="$(command -v adb)"
elif [[ -x "$HOME/Library/Android/sdk/platform-tools/adb" ]]; then
    ADB_BIN="$HOME/Library/Android/sdk/platform-tools/adb"
elif [[ -x "$HOME/Android/Sdk/platform-tools/adb" ]]; then
    ADB_BIN="$HOME/Android/Sdk/platform-tools/adb"
fi

if [[ -z "${ADB_BIN}" ]]; then
    echo "ERROR: 'adb' not found. Install Android Platform-Tools or transfer ${APK_PATH} directly to your phone." >&2
    exit 1
fi

# 3. Check connected USB / Wireless ADB Android device
DEVICE_SERIAL="${1:-}"
if [[ -z "${DEVICE_SERIAL}" ]]; then
    DEVICE_SERIAL="$("${ADB_BIN}" devices | awk 'NR>1 && $2=="device" {print $1; exit}')"
fi

if [[ -z "${DEVICE_SERIAL}" ]]; then
    echo ""
    echo "未检测到已开启「USB 调试 / 无线调试」的 Android 真机或模拟器。"
    echo "请通过数据线连接手机并允许 USB 调试后重试，或直接将已签名的安装包发到手机点击安装："
    echo "  -> ${APK_PATH}"
    exit 1
fi

echo "Installing EasyColab Release APK onto device [${DEVICE_SERIAL}]..."
"${ADB_BIN}" -s "${DEVICE_SERIAL}" install -r "${APK_PATH}"

echo "Launching EasyColab Studio..."
"${ADB_BIN}" -s "${DEVICE_SERIAL}" shell am start -n "app.easycolab.studio/.MainActivity"

echo "Done! EasyColab Android is now running on [${DEVICE_SERIAL}]."
