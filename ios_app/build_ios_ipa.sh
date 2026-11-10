#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

APP_NAME="EasyColab"
BUNDLE_ID="app.easycolab.studio.ios"
VERSION_FILE="${PROJECT_ROOT}/VERSION"
if [ -f "${VERSION_FILE}" ]; then
    APP_VERSION="$(tr -d '[:space:]' < "${VERSION_FILE}")"
fi
APP_VERSION="${APP_VERSION:-1.1.0}"

IOS_SDK_PATH="$(xcrun --sdk iphoneos --show-sdk-path)"
BUILD_ROOT="${PROJECT_ROOT}/build/ios_ipa"
PAYLOAD_DIR="${BUILD_ROOT}/Payload"
APP_BUNDLE="${PAYLOAD_DIR}/${APP_NAME}.app"
IPA_OUTPUT="${PROJECT_ROOT}/EasyColab-iOS.ipa"

rm -rf "${BUILD_ROOT}"
mkdir -p "${APP_BUNDLE}"

# 1. Bundle cloud engine & notebook resources into EasyColab.app
for res_file in "VERSION" "app.py" "EasyColab_Server.ipynb"; do
    if [ -f "${PROJECT_ROOT}/${res_file}" ]; then
        cp -f "${PROJECT_ROOT}/${res_file}" "${APP_BUNDLE}/${res_file}"
    fi
done
if [ -f "${SCRIPT_DIR}/PrivacyInfo.xcprivacy" ]; then
    cp -f "${SCRIPT_DIR}/PrivacyInfo.xcprivacy" "${APP_BUNDLE}/PrivacyInfo.xcprivacy"
fi

# 2. Generate full-bleed iOS / iPadOS AppIcon PNGs programmatically
swift - "${APP_BUNDLE}" << 'SWIFT_IOS_ICON'
import AppKit

let outDir = CommandLine.arguments[1]

func renderIOSIcon(size: Int, filename: String) {
    let s = CGFloat(size)
    let rep = NSBitmapImageRep(
        bitmapDataPlanes: nil,
        pixelsWide: size,
        pixelsHigh: size,
        bitsPerSample: 8,
        samplesPerPixel: 4,
        hasAlpha: true,
        isPlanar: false,
        colorSpaceName: .deviceRGB,
        bytesPerRow: 0,
        bitsPerPixel: 0
    )!
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: rep)!
    let c = NSGraphicsContext.current!.cgContext
    c.scaleBy(x: s / 1024.0, y: s / 1024.0)
    c.setAllowsAntialiasing(true)

    // Full-bleed sky gradient background (iOS SpringBoard applies squircle mask automatically)
    let bgColors = [
        NSColor(calibratedRed: 0.78, green: 0.89, blue: 0.96, alpha: 1.0).cgColor,
        NSColor(calibratedRed: 0.95, green: 0.98, blue: 1.00, alpha: 1.0).cgColor
    ] as CFArray
    let grad = CGGradient(colorsSpace: CGColorSpaceCreateDeviceRGB(), colors: bgColors, locations: [0.0, 1.0])!
    c.drawLinearGradient(grad, start: CGPoint(x: 120, y: 0), end: CGPoint(x: 900, y: 1024), options: [])

    c.saveGState()
    c.translateBy(x: -7, y: -48)

    let cloud = CGMutablePath()
    cloud.move(to: CGPoint(x: 290, y: 395))
    cloud.addCurve(to: CGPoint(x: 288, y: 635), control1: CGPoint(x: 200, y: 395), control2: CGPoint(x: 188, y: 608))
    cloud.addCurve(to: CGPoint(x: 632, y: 710), control1: CGPoint(x: 332, y: 798), control2: CGPoint(x: 562, y: 836))
    cloud.addCurve(to: CGPoint(x: 740, y: 612), control1: CGPoint(x: 694, y: 708), control2: CGPoint(x: 736, y: 664))
    cloud.addCurve(to: CGPoint(x: 738, y: 395), control1: CGPoint(x: 856, y: 605), control2: CGPoint(x: 874, y: 395))
    cloud.closeSubpath()

    c.saveGState()
    c.setShadow(offset: CGSize(width: 0, height: -14), blur: 28, color: NSColor(calibratedRed: 0.20, green: 0.44, blue: 0.62, alpha: 0.20).cgColor)
    c.addPath(cloud)
    c.setFillColor(NSColor.white.cgColor)
    c.fillPath()
    c.restoreGState()

    c.setStrokeColor(NSColor(calibratedRed: 0.95, green: 0.40, blue: 0.17, alpha: 1.0).cgColor)
    c.setLineWidth(38)
    c.setLineCap(.round)
    c.setLineJoin(.round)
    c.move(to: CGPoint(x: 390, y: 506))
    c.addLine(to: CGPoint(x: 512, y: 590))
    c.addLine(to: CGPoint(x: 636, y: 506))
    c.strokePath()

    for pt in [CGPoint(x: 390, y: 506), CGPoint(x: 512, y: 590), CGPoint(x: 636, y: 506)] {
        c.setFillColor(NSColor(calibratedRed: 1.0, green: 0.57, blue: 0.25, alpha: 1.0).cgColor)
        c.fillEllipse(in: CGRect(x: pt.x - 36, y: pt.y - 36, width: 72, height: 72))
    }

    c.restoreGState()
    NSGraphicsContext.restoreGraphicsState()

    let pngData = rep.representation(using: .png, properties: [:])!
    try! pngData.write(to: URL(fileURLWithPath: "\(outDir)/\(filename)"))
}

renderIOSIcon(size: 120, filename: "AppIcon60x60@2x.png")
renderIOSIcon(size: 180, filename: "AppIcon60x60@3x.png")
renderIOSIcon(size: 152, filename: "AppIcon76x76@2x~ipad.png")
renderIOSIcon(size: 167, filename: "AppIcon83.5x83.5@2x~ipad.png")
renderIOSIcon(size: 1024, filename: "AppIcon1024.png")
SWIFT_IOS_ICON

# 3. Generate iOS / iPadOS Info.plist
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
    <key>UIRequiredDeviceCapabilities</key>
    <array>
        <string>arm64</string>
    </array>
    <key>UISupportedInterfaceOrientations</key>
    <array>
        <string>UIInterfaceOrientationPortrait</string>
        <string>UIInterfaceOrientationLandscapeLeft</string>
        <string>UIInterfaceOrientationLandscapeRight</string>
    </array>
    <key>UISupportedInterfaceOrientations~ipad</key>
    <array>
        <string>UIInterfaceOrientationPortrait</string>
        <string>UIInterfaceOrientationPortraitUpsideDown</string>
        <string>UIInterfaceOrientationLandscapeLeft</string>
        <string>UIInterfaceOrientationLandscapeRight</string>
    </array>
    <key>UIFileSharingEnabled</key>
    <true/>
    <key>LSSupportsOpeningDocumentsInPlace</key>
    <true/>
    <key>ITSAppUsesNonExemptEncryption</key>
    <false/>
    <key>NSPhotoLibraryUsageDescription</key>
    <string>EasyColab 需要访问相册以选择首尾帧/修图参考图片并将生成的视频和海报保存至相册。</string>
    <key>NSPhotoLibraryAddUsageDescription</key>
    <string>EasyColab 需要将云端生成的高清 MP4 视频与 PNG 图像保存到您的系统相册。</string>
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
    <key>CFBundleIcons</key>
    <dict>
        <key>CFBundlePrimaryIcon</key>
        <dict>
            <key>CFBundleIconFiles</key>
            <array>
                <string>AppIcon60x60</string>
            </array>
            <key>UIPrerenderedIcon</key>
            <false/>
        </dict>
    </dict>
    <key>CFBundleIcons~ipad</key>
    <dict>
        <key>CFBundlePrimaryIcon</key>
        <dict>
            <key>CFBundleIconFiles</key>
            <array>
                <string>AppIcon60x60</string>
                <string>AppIcon76x76</string>
                <string>AppIcon83.5x83.5</string>
            </array>
            <key>UIPrerenderedIcon</key>
            <false/>
        </dict>
    </dict>
</dict>
</plist>
EOF

echo -n "APPL????" > "${APP_BUNDLE}/PkgInfo"

# 4. Compile Pure-Swift Native iOS arm64 Binary (target iOS 16.0+, strip local build paths)
echo "Compiling native SwiftUI iOS/iPadOS arm64 binary (${APP_NAME} v${APP_VERSION})..."
xcrun --sdk iphoneos swiftc -O \
    -sdk "${IOS_SDK_PATH}" \
    -target arm64-apple-ios16.0 \
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

# 5. Ad-hoc sign (no personal Apple Team ID leaked; ready for AltStore / SideStore / Sideloadly / TrollStore)
xattr -cr "${APP_BUNDLE}" 2>/dev/null || true
codesign --force --sign - "${APP_BUNDLE}"

# 6. Package clean standard Payload/EasyColab.app into EasyColab-iOS.ipa (no __MACOSX metadata for strict sideloaders)
rm -f "${IPA_OUTPUT}"
(
    cd "${BUILD_ROOT}"
    COPYFILE_DISABLE=1 zip -r -y -q "${IPA_OUTPUT}" "Payload" -x "*.DS_Store" -x "__MACOSX/*"
)

echo "✅ Successfully built iOS/iPadOS bundle: ${APP_BUNDLE}"
echo "✅ Successfully packaged sideload IPA:   ${IPA_OUTPUT}"
ls -lh "${IPA_OUTPUT}"
