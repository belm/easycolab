#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

APP_NAME="EasyColab"
BUNDLE_ID="app.easycolab.studio.ios"
VERSION_FILE="${PROJECT_ROOT}/VERSION"
APP_VERSION="$( [ -f "${VERSION_FILE}" ] && tr -d '[:space:]' < "${VERSION_FILE}" || echo "1.1.0" )"

HOST_ARCH="$(uname -m)"
SIM_SDK_PATH="$(xcrun --sdk iphonesimulator --show-sdk-path)"
SIM_BUILD_DIR="${PROJECT_ROOT}/build/ios_simulator"
APP_BUNDLE="${SIM_BUILD_DIR}/${APP_NAME}.app"

rm -rf "${SIM_BUILD_DIR}"
mkdir -p "${APP_BUNDLE}"

for res_file in "VERSION" "app.py" "EasyColab_Server.ipynb"; do
    if [ -f "${PROJECT_ROOT}/${res_file}" ]; then
        cp -f "${PROJECT_ROOT}/${res_file}" "${APP_BUNDLE}/${res_file}"
    fi
done

GOOGLE_OAUTH_SCHEME="$(/usr/bin/python3 -c '
import re, pathlib, sys
src = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
m = re.search(r"encodedClientIdBytes:\s*\[UInt8\]\s*=\s*\[([^\]]+)\]", src)
nums = [int(x.strip()) for x in m.group(1).split(",") if x.strip()]
cid = bytes(b ^ 0x5A for b in nums).decode("utf-8")
print("com.googleusercontent.apps." + cid.split(".apps.googleusercontent.com")[0])
' "${SCRIPT_DIR}/Sources/ColabNativeBridge.swift")"

cat > "${APP_BUNDLE}/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleDevelopmentRegion</key>
    <string>zh_CN</string>
    <key>CFBundleDisplayName</key>
    <string>${APP_NAME}</string>
    <key>CFBundleExecutable</key>
    <string>${APP_NAME}</string>
    <key>CFBundleIdentifier</key>
    <string>${BUNDLE_ID}</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleName</key>
    <string>${APP_NAME}</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>${APP_VERSION}</string>
    <key>CFBundleVersion</key>
    <string>${APP_VERSION}</string>
    <key>LSRequiresIPhoneOS</key>
    <true/>
    <key>MinimumOSVersion</key>
    <string>16.0</string>
    <key>UIDeviceFamily</key>
    <array>
        <integer>1</integer>
        <integer>2</integer>
    </array>
    <key>UILaunchScreen</key>
    <dict/>
    <key>NSPhotoLibraryUsageDescription</key>
    <string>EasyColab 需要访问相册以选择参考图片并保存生成的视频与海报。</string>
    <key>NSPhotoLibraryAddUsageDescription</key>
    <string>EasyColab 需要将云端生成的视频与图像保存到系统相册。</string>
    <key>NSAppTransportSecurity</key>
    <dict>
        <key>NSAllowsArbitraryLoads</key>
        <true/>
    </dict>
    <key>CFBundleURLTypes</key>
    <array>
        <dict>
            <key>CFBundleTypeRole</key>
            <string>Editor</string>
            <key>CFBundleURLName</key>
            <string>google-oauth</string>
            <key>CFBundleURLSchemes</key>
            <array>
                <string>${GOOGLE_OAUTH_SCHEME}</string>
            </array>
        </dict>
    </array>
</dict>
</plist>
EOF

echo "Compiling EasyColab for iOS Simulator (${HOST_ARCH}-apple-ios16.0-simulator)..."
xcrun --sdk iphonesimulator swiftc \
    -sdk "${SIM_SDK_PATH}" \
    -target "${HOST_ARCH}-apple-ios16.0-simulator" \
    -file-prefix-map "${PROJECT_ROOT}=." \
    -file-prefix-map "${HOME}=~" \
    -parse-as-library \
    -framework SwiftUI \
    -framework UIKit \
    -framework AVKit \
    -framework AVFoundation \
    -framework Photos \
    -framework PhotosUI \
    -framework SafariServices \
    -framework AuthenticationServices \
    -framework Security \
    -framework CryptoKit \
    "${SCRIPT_DIR}"/Sources/*.swift \
    -o "${APP_BUNDLE}/${APP_NAME}"

codesign --force --sign - "${APP_BUNDLE}"
echo "✅ Built Simulator app bundle: ${APP_BUNDLE}"

if [ "${1:-}" = "--build-only" ]; then
    exit 0
fi

BOOTED_UDID="$(xcrun simctl list devices booted | grep -Eo '[0-9A-F-]{36}' | head -n 1 || true)"
if [ -z "${BOOTED_UDID}" ]; then
    BOOTED_UDID="$(xcrun simctl list devices available | grep "iPhone" | grep -Eo '[0-9A-F-]{36}' | head -n 1 || true)"
    if [ -n "${BOOTED_UDID}" ]; then
        echo "Booting iOS Simulator (${BOOTED_UDID})..."
        xcrun simctl boot "${BOOTED_UDID}" || true
    fi
fi

open -a Simulator || true
xcrun simctl install booted "${APP_BUNDLE}"
xcrun simctl launch booted "${BUNDLE_ID}"
echo "🚀 Launched ${BUNDLE_ID} in iOS Simulator!"
