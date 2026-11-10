#!/bin/bash
set -euo pipefail

# ==============================================================================
# EasyColab iOS / iPadOS One-Click Release Installer (Free or Paid Apple ID)
# ------------------------------------------------------------------------------
# Builds a full -O Release .app (NO LLDB debugger attached — runs standalone
# unplugged; 7-day signing on a free Apple ID Personal Team or 365-day signing
# on a paid Apple Developer account), automatically provisions & signs via
# Xcode, and installs directly onto your connected iPhone / iPad.
#
# Privacy Guarantee:
#   All Xcode project files & DerivedData are generated inside gitignored
#   `build/ios_device_proj/`. Your personal Apple TEAM_ID is NEVER written to
#   any git-tracked file (cached locally in gitignored `LocalSigning.xcconfig`).
#
# Usage:
#   bash ios_app/install_release_iphone.sh               # Auto-sign & install Release to connected iPhone/iPad
#   TEAM_ID=ABCDE12345 bash ios_app/install_release_iphone.sh
#   bash ios_app/install_release_iphone.sh --open-xcode  # Open Release-locked project in Xcode GUI
#   bash ios_app/install_release_iphone.sh --build-only  # Verify Release xcodebuild without signing/device
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

MODE="install"
for arg in "$@"; do
    case "$arg" in
        --open-xcode) MODE="open_xcode" ;;
        --build-only) MODE="build_only" ;;
        -h|--help)
            sed -n '2,20p' "${BASH_SOURCE[0]}"
            exit 0
            ;;
    esac
done

APP_NAME="EasyColab"
VERSION_FILE="${PROJECT_ROOT}/VERSION"
APP_VERSION="$( [ -f "${VERSION_FILE}" ] && tr -d '[:space:]' < "${VERSION_FILE}" || echo "1.1.0" )"

LOCAL_XCCONFIG="${PROJECT_ROOT}/LocalSigning.xcconfig"
PROJ_ROOT="${PROJECT_ROOT}/build/ios_device_proj"
XCODEPROJ_DIR="${PROJ_ROOT}/${APP_NAME}.xcodeproj"
DERIVED_DATA="${PROJ_ROOT}/DerivedData"

# 1. Read cached TEAM_ID / BUNDLE_ID from gitignored LocalSigning.xcconfig if present
if [ "${MODE}" != "build_only" ] && [ -f "${LOCAL_XCCONFIG}" ]; then
    CACHED_TEAM="$(grep -E '^[[:space:]]*DEVELOPMENT_TEAM[[:space:]]*=' "${LOCAL_XCCONFIG}" | tail -n1 | cut -d'=' -f2 | tr -d '[:space:]' || true)"
    CACHED_BUNDLE="$(grep -E '^[[:space:]]*PRODUCT_BUNDLE_IDENTIFIER[[:space:]]*=' "${LOCAL_XCCONFIG}" | tail -n1 | cut -d'=' -f2 | tr -d '[:space:]' || true)"
    TEAM_ID="${TEAM_ID:-${CACHED_TEAM}}"
    BUNDLE_ID="${BUNDLE_ID:-${CACHED_BUNDLE}}"
fi

mkdir -p "${PROJ_ROOT}"

# 2. Auto-detect Apple Developer Team ID from local Keychain or Xcode Accounts (never echoed to git)
if [ -z "${TEAM_ID:-}" ] && [ "${MODE}" != "build_only" ]; then
    /usr/bin/python3 - > "${PROJ_ROOT}/.detected_team" << 'PY_DETECT_TEAM'
import re, subprocess

for cert_name in ("Apple Development", "iPhone Developer", "Apple Distribution"):
    try:
        pem = subprocess.check_output(
            ["security", "find-certificate", "-a", "-c", cert_name, "-p"],
            stderr=subprocess.DEVNULL, text=True
        )
        if "BEGIN CERTIFICATE" in pem:
            first_pem = "-----BEGIN CERTIFICATE-----" + pem.split("-----BEGIN CERTIFICATE-----")[1]
            subj = subprocess.check_output(
                ["openssl", "x509", "-noout", "-subject", "-nameopt", "RFC2253"],
                input=first_pem, stderr=subprocess.DEVNULL, text=True
            )
            m = re.search(r"(?:^|[,/])OU=([A-Z0-9]{10})(?:[,/\s]|$)", subj)
            if m:
                print(m.group(1))
                raise SystemExit(0)
    except Exception:
        pass

try:
    out = subprocess.check_output(
        ["defaults", "read", "com.apple.dt.Xcode", "IDEProvisioningTeams"],
        stderr=subprocess.DEVNULL, text=True
    )
    m = re.search(r"teamID\s*=\s*\"?([A-Z0-9]{10})\"?\s*;", out)
    if m:
        print(m.group(1))
        raise SystemExit(0)
except Exception:
    pass
PY_DETECT_TEAM
    TEAM_ID="$(tr -d '[:space:]' < "${PROJ_ROOT}/.detected_team" || true)"
    rm -f "${PROJ_ROOT}/.detected_team"
fi

if [ -z "${BUNDLE_ID:-}" ]; then
    if [ -n "${TEAM_ID:-}" ]; then
        TEAM_LOWER="$(echo "${TEAM_ID}" | tr '[:upper:]' '[:lower:]')"
        BUNDLE_ID="app.easycolab.studio.${TEAM_LOWER}"
    else
        BUNDLE_ID="app.easycolab.studio.ios"
    fi
fi

# Persist locally in gitignored LocalSigning.xcconfig so future updates overwrite the same app cleanly
if [ -n "${TEAM_ID:-}" ]; then
    cat > "${LOCAL_XCCONFIG}" <<EOF
// Local Apple Developer Signing Config (Git-ignored — NEVER committed)
DEVELOPMENT_TEAM = ${TEAM_ID}
PRODUCT_BUNDLE_IDENTIFIER = ${BUNDLE_ID}
EOF
fi

rm -rf "${XCODEPROJ_DIR}"
mkdir -p "${PROJ_ROOT}/Assets.xcassets/AppIcon.appiconset"

# 3. Generate strictly opaque 24-bit RGB 1024x1024 AppIcon in Assets.xcassets
swift - "${PROJ_ROOT}/Assets.xcassets/AppIcon.appiconset/AppIcon1024.png" << 'SWIFT_ASSET_ICON'
import AppKit
import CoreGraphics
import ImageIO
import UniformTypeIdentifiers

let outURL = URL(fileURLWithPath: CommandLine.arguments[1])
let size = 1024
let colorSpace = CGColorSpaceCreateDeviceRGB()
let ctx = CGContext(
    data: nil,
    width: size,
    height: size,
    bitsPerComponent: 8,
    bytesPerRow: size * 4,
    space: colorSpace,
    bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue
)!
ctx.setAllowsAntialiasing(true)

ctx.setFillColor(CGColor(red: 0.88, green: 0.94, blue: 0.99, alpha: 1.0))
ctx.fill(CGRect(x: 0, y: 0, width: size, height: size))

let bgColors = [
    CGColor(red: 0.78, green: 0.89, blue: 0.96, alpha: 1.0),
    CGColor(red: 0.95, green: 0.98, blue: 1.00, alpha: 1.0)
] as CFArray
let grad = CGGradient(colorsSpace: colorSpace, colors: bgColors, locations: [0.0, 1.0])!
ctx.drawLinearGradient(grad, start: CGPoint(x: 120, y: 0), end: CGPoint(x: 900, y: 1024), options: [])

ctx.saveGState()
ctx.translateBy(x: -7, y: -48)
let cloud = CGMutablePath()
cloud.move(to: CGPoint(x: 290, y: 395))
cloud.addCurve(to: CGPoint(x: 288, y: 635), control1: CGPoint(x: 200, y: 395), control2: CGPoint(x: 188, y: 608))
cloud.addCurve(to: CGPoint(x: 632, y: 710), control1: CGPoint(x: 332, y: 798), control2: CGPoint(x: 562, y: 836))
cloud.addCurve(to: CGPoint(x: 740, y: 612), control1: CGPoint(x: 694, y: 708), control2: CGPoint(x: 736, y: 664))
cloud.addCurve(to: CGPoint(x: 738, y: 395), control1: CGPoint(x: 856, y: 605), control2: CGPoint(x: 874, y: 395))
cloud.closeSubpath()

ctx.saveGState()
ctx.setShadow(offset: CGSize(width: 0, height: -14), blur: 28, color: CGColor(red: 0.20, green: 0.44, blue: 0.62, alpha: 0.20))
ctx.addPath(cloud)
ctx.setFillColor(CGColor(red: 1.0, green: 1.0, blue: 1.0, alpha: 1.0))
ctx.fillPath()
ctx.restoreGState()

ctx.setStrokeColor(CGColor(red: 0.95, green: 0.40, blue: 0.17, alpha: 1.0))
ctx.setLineWidth(38)
ctx.setLineCap(.round)
ctx.setLineJoin(.round)
ctx.move(to: CGPoint(x: 390, y: 506))
ctx.addLine(to: CGPoint(x: 512, y: 590))
ctx.addLine(to: CGPoint(x: 636, y: 506))
ctx.strokePath()

for pt in [CGPoint(x: 390, y: 506), CGPoint(x: 512, y: 590), CGPoint(x: 636, y: 506)] {
    ctx.setFillColor(CGColor(red: 1.0, green: 0.57, blue: 0.25, alpha: 1.0))
    ctx.fillEllipse(in: CGRect(x: pt.x - 36, y: pt.y - 36, width: 72, height: 72))
}
ctx.restoreGState()

let rawImg = ctx.makeImage()!
let rep = NSBitmapImageRep(cgImage: rawImg)
let opaqueRep = NSBitmapImageRep(
    bitmapDataPlanes: nil,
    pixelsWide: size,
    pixelsHigh: size,
    bitsPerSample: 8,
    samplesPerPixel: 3,
    hasAlpha: false,
    isPlanar: false,
    colorSpaceName: .deviceRGB,
    bytesPerRow: size * 3,
    bitsPerPixel: 24
)!
if let src = rep.bitmapData, let dst = opaqueRep.bitmapData {
    let srcBPR = rep.bytesPerRow
    for y in 0..<size {
        for x in 0..<size {
            let sIdx = y * srcBPR + x * 4
            let dIdx = y * (size * 3) + x * 3
            dst[dIdx]     = src[sIdx]
            dst[dIdx + 1] = src[sIdx + 1]
            dst[dIdx + 2] = src[sIdx + 2]
        }
    }
}
try! opaqueRep.representation(using: .png, properties: [:])!.write(to: outURL)
SWIFT_ASSET_ICON

cat > "${PROJ_ROOT}/Assets.xcassets/Contents.json" << 'EOF'
{ "info" : { "author" : "xcode", "version" : 1 } }
EOF

cat > "${PROJ_ROOT}/Assets.xcassets/AppIcon.appiconset/Contents.json" << 'EOF'
{
  "images" : [
    {
      "filename" : "AppIcon1024.png",
      "idiom" : "universal",
      "platform" : "ios",
      "size" : "1024x1024"
    }
  ],
  "info" : { "author" : "xcode", "version" : 1 }
}
EOF

# 4. Generate Info.plist & Release-locked EasyColab.xcodeproj inside build/ios_device_proj/
GOOGLE_OAUTH_SCHEME="$(/usr/bin/python3 -c '
import re, pathlib, sys
src = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
m = re.search(r"encodedClientIdBytes:\s*\[UInt8\]\s*=\s*\[([^\]]+)\]", src)
nums = [int(x.strip()) for x in m.group(1).split(",") if x.strip()]
cid = bytes(b ^ 0x5A for b in nums).decode("utf-8")
print("com.googleusercontent.apps." + cid.split(".apps.googleusercontent.com")[0])
' "${SCRIPT_DIR}/Sources/ColabNativeBridge.swift")"

cat > "${PROJ_ROOT}/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleDevelopmentRegion</key>
    <string>zh_CN</string>
    <key>CFBundleDisplayName</key>
    <string>${APP_NAME}</string>
    <key>CFBundleExecutable</key>
    <string>\$(EXECUTABLE_NAME)</string>
    <key>CFBundleIdentifier</key>
    <string>\$(PRODUCT_BUNDLE_IDENTIFIER)</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleName</key>
    <string>\$(PRODUCT_NAME)</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>${APP_VERSION}</string>
    <key>CFBundleVersion</key>
    <string>${APP_VERSION}</string>
    <key>LSRequiresIPhoneOS</key>
    <true/>
    <key>UILaunchScreen</key>
    <dict/>
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
</dict>
</plist>
EOF

/usr/bin/python3 - "${PROJECT_ROOT}" "${PROJ_ROOT}" "${APP_VERSION}" "${BUNDLE_ID}" "${TEAM_ID:-}" << 'PY_GEN_XCODEPROJ'
import glob, hashlib, os, sys

project_root, proj_root, app_ver, bundle_id, team_id = sys.argv[1:6]
xcodeproj = os.path.join(proj_root, "EasyColab.xcodeproj")
schemes_dir = os.path.join(xcodeproj, "xcshareddata", "xcschemes")
os.makedirs(schemes_dir, exist_ok=True)

def uid(tag: str) -> str:
    return hashlib.sha1(tag.encode("utf-8")).hexdigest()[:24].upper()

swift_files = sorted(glob.glob(os.path.join(project_root, "ios_app", "Sources", "*.swift")))
res_files = [
    os.path.join(project_root, "VERSION"),
    os.path.join(project_root, "app.py"),
    os.path.join(project_root, "EasyColab_Server.ipynb"),
    os.path.join(proj_root, "Assets.xcassets"),
]
res_files = [p for p in res_files if os.path.exists(p)]

file_refs = []
build_files = []
src_build_ids = []
res_build_ids = []
group_children = []

for sf in swift_files:
    name = os.path.basename(sf)
    f_id = uid("fref:" + name)
    b_id = uid("bfile:" + name)
    file_refs.append(f'\t\t{f_id} /* {name} */ = {{isa = PBXFileReference; lastKnownFileType = sourcecode.swift; name = "{name}"; path = "{sf}"; sourceTree = "<absolute>"; }};')
    build_files.append(f'\t\t{b_id} /* {name} in Sources */ = {{isa = PBXBuildFile; fileRef = {f_id} /* {name} */; }};')
    src_build_ids.append(f'\t\t\t\t{b_id} /* {name} in Sources */,')
    group_children.append(f'\t\t\t\t{f_id} /* {name} */,')

for rf in res_files:
    name = os.path.basename(rf)
    ftype = "folder.assetcatalog" if name.endswith(".xcassets") else "text"
    f_id = uid("rref:" + name)
    b_id = uid("rbfile:" + name)
    file_refs.append(f'\t\t{f_id} /* {name} */ = {{isa = PBXFileReference; lastKnownFileType = {ftype}; name = "{name}"; path = "{rf}"; sourceTree = "<absolute>"; }};')
    build_files.append(f'\t\t{b_id} /* {name} in Resources */ = {{isa = PBXBuildFile; fileRef = {f_id} /* {name} */; }};')
    res_build_ids.append(f'\t\t\t\t{b_id} /* {name} in Resources */,')
    group_children.append(f'\t\t\t\t{f_id} /* {name} */,')

prod_id = uid("product:EasyColab.app")
main_grp = uid("group:main")
prod_grp = uid("group:products")
src_phase = uid("phase:sources")
res_phase = uid("phase:resources")
fw_phase = uid("phase:frameworks")
target_id = uid("target:EasyColab")
proj_id = uid("project:EasyColab")
cfg_list_proj = uid("cfglist:proj")
cfg_list_tgt = uid("cfglist:tgt")
cfg_proj_dbg = uid("cfg:proj:Debug")
cfg_proj_rel = uid("cfg:proj:Release")
cfg_tgt_dbg = uid("cfg:tgt:Debug")
cfg_tgt_rel = uid("cfg:tgt:Release")

team_line = f'\t\t\t\tDEVELOPMENT_TEAM = "{team_id}";\n' if team_id else ""
info_plist_path = os.path.join(proj_root, "Info.plist")

pbxproj = f"""// !$*UTF8*$!
{{
	archiveVersion = 1;
	classes = {{
	}};
	objectVersion = 56;
	objects = {{

/* Begin PBXBuildFile section */
{chr(10).join(build_files)}
/* End PBXBuildFile section */

/* Begin PBXFileReference section */
		{prod_id} /* EasyColab.app */ = {{isa = PBXFileReference; explicitFileType = wrapper.application; includeInIndex = 0; path = EasyColab.app; sourceTree = BUILT_PRODUCTS_DIR; }};
{chr(10).join(file_refs)}
/* End PBXFileReference section */

/* Begin PBXFrameworksBuildPhase section */
		{fw_phase} /* Frameworks */ = {{
			isa = PBXFrameworksBuildPhase;
			buildActionMask = 2147483647;
			files = (
			);
			runOnlyForDeploymentPostprocessing = 0;
		}};
/* End PBXFrameworksBuildPhase section */

/* Begin PBXGroup section */
		{main_grp} = {{
			isa = PBXGroup;
			children = (
{chr(10).join(group_children)}
				{prod_grp} /* Products */,
			);
			sourceTree = "<group>";
		}};
		{prod_grp} /* Products */ = {{
			isa = PBXGroup;
			children = (
				{prod_id} /* EasyColab.app */,
			);
			name = Products;
			sourceTree = "<group>";
		}};
/* End PBXGroup section */

/* Begin PBXNativeTarget section */
		{target_id} /* EasyColab */ = {{
			isa = PBXNativeTarget;
			buildConfigurationList = {cfg_list_tgt} /* Build configuration list for PBXNativeTarget "EasyColab" */;
			buildPhases = (
				{src_phase} /* Sources */,
				{fw_phase} /* Frameworks */,
				{res_phase} /* Resources */,
			);
			buildRules = (
			);
			dependencies = (
			);
			name = EasyColab;
			productName = EasyColab;
			productReference = {prod_id} /* EasyColab.app */;
			productType = "com.apple.product-type.application";
		}};
/* End PBXNativeTarget section */

/* Begin PBXProject section */
		{proj_id} /* Project object */ = {{
			isa = PBXProject;
			attributes = {{
				BuildIndependentTargetsInParallel = 1;
				LastSwiftUpdateCheck = 1600;
				LastUpgradeCheck = 1600;
				TargetAttributes = {{
					{target_id} = {{
						CreatedOnToolsVersion = 16.0;
						ProvisioningStyle = Automatic;
					}};
				}};
			}};
			buildConfigurationList = {cfg_list_proj} /* Build configuration list for PBXProject "EasyColab" */;
			compatibilityVersion = "Xcode 14.0";
			developmentRegion = zh_CN;
			hasScannedForEncodings = 0;
			knownRegions = (
				zh_CN,
				en,
				Base,
			);
			mainGroup = {main_grp};
			productRefGroup = {prod_grp} /* Products */;
			projectDirPath = "";
			projectRoot = "";
			targets = (
				{target_id} /* EasyColab */,
			);
		}};
/* End PBXProject section */

/* Begin PBXResourcesBuildPhase section */
		{res_phase} /* Resources */ = {{
			isa = PBXResourcesBuildPhase;
			buildActionMask = 2147483647;
			files = (
{chr(10).join(res_build_ids)}
			);
			runOnlyForDeploymentPostprocessing = 0;
		}};
/* End PBXResourcesBuildPhase section */

/* Begin PBXSourcesBuildPhase section */
		{src_phase} /* Sources */ = {{
			isa = PBXSourcesBuildPhase;
			buildActionMask = 2147483647;
			files = (
{chr(10).join(src_build_ids)}
			);
			runOnlyForDeploymentPostprocessing = 0;
		}};
/* End PBXSourcesBuildPhase section */

/* Begin XCBuildConfiguration section */
		{cfg_proj_dbg} /* Debug */ = {{
			isa = XCBuildConfiguration;
			buildSettings = {{
				ALWAYS_SEARCH_USER_PATHS = NO;
				IPHONEOS_DEPLOYMENT_TARGET = 16.0;
				SDKROOT = iphoneos;
				SWIFT_VERSION = 5.0;
			}};
			name = Debug;
		}};
		{cfg_proj_rel} /* Release */ = {{
			isa = XCBuildConfiguration;
			buildSettings = {{
				ALWAYS_SEARCH_USER_PATHS = NO;
				IPHONEOS_DEPLOYMENT_TARGET = 16.0;
				SDKROOT = iphoneos;
				SWIFT_COMPILATION_MODE = wholemodule;
				SWIFT_OPTIMIZATION_LEVEL = "-O";
				SWIFT_VERSION = 5.0;
				VALIDATE_PRODUCT = YES;
			}};
			name = Release;
		}};
		{cfg_tgt_dbg} /* Debug */ = {{
			isa = XCBuildConfiguration;
			buildSettings = {{
				ASSETCATALOG_COMPILER_APPICON_NAME = AppIcon;
				CODE_SIGN_STYLE = Automatic;
{team_line}				CURRENT_PROJECT_VERSION = "{app_ver}";
				ENABLE_TESTABILITY = NO;
				INFOPLIST_FILE = "{info_plist_path}";
				IPHONEOS_DEPLOYMENT_TARGET = 16.0;
				LD_RUNPATH_SEARCH_PATHS = (
					"$(inherited)",
					"@executable_path/Frameworks",
				);
				MARKETING_VERSION = "{app_ver}";
				PRODUCT_BUNDLE_IDENTIFIER = "{bundle_id}";
				PRODUCT_NAME = EasyColab;
				SUPPORTED_PLATFORMS = "iphoneos iphonesimulator";
				SUPPORTS_MACCATALYST = NO;
				TARGETED_DEVICE_FAMILY = "1,2";
			}};
			name = Debug;
		}};
		{cfg_tgt_rel} /* Release */ = {{
			isa = XCBuildConfiguration;
			buildSettings = {{
				ASSETCATALOG_COMPILER_APPICON_NAME = AppIcon;
				CODE_SIGN_STYLE = Automatic;
				DEBUG_INFORMATION_FORMAT = "dwarf-with-dsym";
{team_line}				CURRENT_PROJECT_VERSION = "{app_ver}";
				ENABLE_NS_ASSERTIONS = NO;
				ENABLE_TESTABILITY = NO;
				INFOPLIST_FILE = "{info_plist_path}";
				IPHONEOS_DEPLOYMENT_TARGET = 16.0;
				LD_RUNPATH_SEARCH_PATHS = (
					"$(inherited)",
					"@executable_path/Frameworks",
				);
				MARKETING_VERSION = "{app_ver}";
				PRODUCT_BUNDLE_IDENTIFIER = "{bundle_id}";
				PRODUCT_NAME = EasyColab;
				SUPPORTED_PLATFORMS = "iphoneos iphonesimulator";
				SUPPORTS_MACCATALYST = NO;
				SWIFT_COMPILATION_MODE = wholemodule;
				SWIFT_OPTIMIZATION_LEVEL = "-O";
				TARGETED_DEVICE_FAMILY = "1,2";
			}};
			name = Release;
		}};
/* End XCBuildConfiguration section */

/* Begin XCConfigurationList section */
		{cfg_list_proj} /* Build configuration list for PBXProject "EasyColab" */ = {{
			isa = XCConfigurationList;
			buildConfigurations = (
				{cfg_proj_dbg} /* Debug */,
				{cfg_proj_rel} /* Release */,
			);
			defaultConfigurationIsVisible = 0;
			defaultConfigurationName = Release;
		}};
		{cfg_list_tgt} /* Build configuration list for PBXNativeTarget "EasyColab" */ = {{
			isa = XCConfigurationList;
			buildConfigurations = (
				{cfg_tgt_dbg} /* Debug */,
				{cfg_tgt_rel} /* Release */,
			);
			defaultConfigurationIsVisible = 0;
			defaultConfigurationName = Release;
		}};
/* End XCConfigurationList section */
	}};
	rootObject = {proj_id} /* Project object */;
}}
"""

with open(os.path.join(xcodeproj, "project.pbxproj"), "w", encoding="utf-8") as f:
    f.write(pbxproj)

# Write Shared Scheme locked to Release + Debug Executable OFF (PosixSpawn, no LLDB!)
xcscheme = f"""<?xml version="1.0" encoding="UTF-8"?>
<Scheme
   LastUpgradeVersion = "1600"
   version = "1.7">
   <BuildAction
      parallelizeBuildables = "YES"
      buildImplicitDependencies = "YES">
      <BuildActionEntries>
         <BuildActionEntry
            buildForTesting = "NO"
            buildForRunning = "YES"
            buildForProfiling = "YES"
            buildForArchiving = "YES"
            buildForAnalyzing = "YES">
            <BuildableReference
               BuildableIdentifier = "primary"
               BlueprintIdentifier = "{target_id}"
               BuildableName = "EasyColab.app"
               BlueprintName = "EasyColab"
               ReferencedContainer = "container:EasyColab.xcodeproj">
            </BuildableReference>
         </BuildActionEntry>
      </BuildActionEntries>
   </BuildAction>
   <LaunchAction
      buildConfiguration = "Release"
      selectedDebuggerIdentifier = ""
      selectedLauncherIdentifier = "Xcode.IDEFoundation.Launcher.PosixSpawn"
      launchStyle = "0"
      useCustomWorkingDirectory = "NO"
      ignoresPersistentStateOnLaunch = "NO"
      debugDocumentVersioning = "YES"
      debugServiceExtension = "internal"
      allowLocationSimulation = "YES">
      <BuildableProductRunnable
         runnableDebuggingMode = "0">
         <BuildableReference
            BuildableIdentifier = "primary"
            BlueprintIdentifier = "{target_id}"
            BuildableName = "EasyColab.app"
            BlueprintName = "EasyColab"
            ReferencedContainer = "container:EasyColab.xcodeproj">
         </BuildableReference>
      </BuildableProductRunnable>
   </LaunchAction>
   <ArchiveAction
      buildConfiguration = "Release"
      revealArchiveInOrganizer = "YES">
   </ArchiveAction>
</Scheme>
"""
with open(os.path.join(schemes_dir, "EasyColab.xcscheme"), "w", encoding="utf-8") as f:
    f.write(xcscheme)
PY_GEN_XCODEPROJ

echo "✅ Generated clean Release-locked Xcode project (git-ignored): ${XCODEPROJ_DIR}"

if [ "${MODE}" = "open_xcode" ]; then
    echo "🚀 Opening Release-locked project in Xcode (Run scheme is pre-set to Release + Debug Executable OFF)..."
    open "${XCODEPROJ_DIR}"
    exit 0
fi

if [ "${MODE}" = "build_only" ]; then
    echo "🔨 Verifying Release xcodebuild (unsigned check)..."
    xcodebuild \
        -project "${XCODEPROJ_DIR}" \
        -scheme "${APP_NAME}" \
        -configuration Release \
        -sdk iphoneos \
        -derivedDataPath "${DERIVED_DATA}" \
        CODE_SIGNING_ALLOWED=NO \
        CODE_SIGNING_REQUIRED=NO \
        CODE_SIGN_IDENTITY="" \
        build | tail -n 15
    echo "✅ Release xcodebuild verification passed!"
    exit 0
fi

# 5. Verify Apple Developer TEAM_ID is available
if [ -z "${TEAM_ID:-}" ]; then
    echo "⚠️  尚未在本机检测到已登录的 Apple 开发者团队 ID (DEVELOPMENT_TEAM)。"
    echo "👉 解决方法（任选其一）："
    echo "   1) 打开 Xcode -> Settings (⌘,) -> Accounts 登录你的开发者 Apple ID，或直接运行："
    echo "      bash ios_app/install_release_iphone.sh --open-xcode"
    echo "   2) 或者手动指定你的 10 位 Team ID 运行一次（会自动保存在被 Git 忽略的 LocalSigning.xcconfig 中）："
    echo "      TEAM_ID=你的10位TeamID bash ios_app/install_release_iphone.sh"
    exit 1
fi

# 6. Detect connected iPhone / iPad via CoreDevice (USB or Wi-Fi)
DEVICE_JSON="${PROJ_ROOT}/devices.json"
xcrun devicectl list devices --json-output "${DEVICE_JSON}" >/dev/null 2>&1 || true

/usr/bin/python3 - "${DEVICE_JSON}" > "${PROJ_ROOT}/.dev_info" << 'PY_FIND_DEVICE'
import json, sys

try:
    data = json.load(open(sys.argv[1], "r", encoding="utf-8"))
    devices = data.get("result", {}).get("devices", [])
except Exception:
    devices = []

for d in devices:
    hw = d.get("hardwareProperties", {}) or d.get("properties", {}).get("hardware", {})
    conn = d.get("connectionProperties", {}) or d.get("properties", {}).get("connection", {})
    dev_props = d.get("deviceProperties", {}) or d.get("properties", {}).get("device", {})
    platform = (hw.get("platform") or "").lower()
    dtype = (hw.get("deviceType") or "").lower()
    pairing = (conn.get("pairingState") or "").lower()
    tunnel = (conn.get("tunnelState") or "").lower()
    if ("ios" in platform or "iphone" in dtype or "ipad" in dtype) and pairing == "paired" and tunnel != "unavailable":
        core_id = d.get("identifier", "")
        udid = hw.get("udid") or core_id
        name = (dev_props.get("name") or "iPhone").replace(" ", "_")
        print(f"{core_id}\t{udid}\t{name}")
        raise SystemExit(0)
PY_FIND_DEVICE

DEV_INFO="$(cat "${PROJ_ROOT}/.dev_info" 2>/dev/null || true)"
rm -f "${PROJ_ROOT}/.dev_info"
DEVICE_CORE_ID="$(printf '%s' "${DEV_INFO}" | cut -f1)"
DEVICE_UDID="$(printf '%s' "${DEV_INFO}" | cut -f2)"
DEVICE_NAME="$(printf '%s' "${DEV_INFO}" | cut -f3)"

if [ -z "${DEVICE_UDID:-}" ]; then
    echo "⚠️  未检测到已连接并配对的 iPhone / iPad。"
    echo "👉 请用数据线将手机连接到 Mac（首次连接请在手机上点「信任此电脑」并开启「开发者模式」），然后重跑："
    echo "   bash ios_app/install_release_iphone.sh"
    exit 1
fi

echo "📱 Target Device : ${DEVICE_NAME} (${DEVICE_UDID})"
echo "📦 Bundle ID     : ${BUNDLE_ID} (Release -O, Standalone)"
echo "🔨 Building & Auto-Provisioning Release app via Xcode..."

xcodebuild \
    -project "${XCODEPROJ_DIR}" \
    -scheme "${APP_NAME}" \
    -configuration Release \
    -destination "id=${DEVICE_UDID}" \
    -derivedDataPath "${DERIVED_DATA}" \
    -allowProvisioningUpdates \
    DEVELOPMENT_TEAM="${TEAM_ID}" \
    PRODUCT_BUNDLE_IDENTIFIER="${BUNDLE_ID}" \
    build

SIGNED_APP="${DERIVED_DATA}/Build/Products/Release-iphoneos/${APP_NAME}.app"
if [ ! -d "${SIGNED_APP}" ]; then
    echo "❌ Signed Release app bundle not found at ${SIGNED_APP}"
    exit 1
fi

echo "📲 Installing Release app onto ${DEVICE_NAME}..."
xcrun devicectl device install app --device "${DEVICE_CORE_ID}" "${SIGNED_APP}"

echo "🚀 Launching ${APP_NAME} (Standalone Release, no debugger attached)..."
xcrun devicectl device process launch --terminate-existing --device "${DEVICE_CORE_ID}" "${BUNDLE_ID}" || true

echo "✅ Done! ${APP_NAME} Release is installed on ${DEVICE_NAME} — you can unplug the cable anytime!"
