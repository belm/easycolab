#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
OUTPUT_APK="${REPO_ROOT}/EasyColab-Android.apk"

echo "============================================================"
echo "  EasyColab Android — Standalone Signed Release APK Builder"
echo "============================================================"

# 1. Auto-detect JDK 17+ (Required by AGP 8.7 + Gradle 8.11)
detect_java_home() {
    if [[ -n "${JAVA_HOME:-}" && -x "${JAVA_HOME}/bin/java" ]]; then
        local ver
        ver="$("${JAVA_HOME}/bin/java" -version 2>&1 | head -n 1)"
        if [[ "${ver}" =~ \"(17|18|19|20|21|22|23)\. ]]; then
            echo "${JAVA_HOME}"
            return 0
        fi
    fi

    if command -v /usr/libexec/java_home >/dev/null 2>&1; then
        local mac_jdk17
        mac_jdk17="$(/usr/libexec/java_home -v 17 2>/dev/null || true)"
        if [[ -n "${mac_jdk17}" && -x "${mac_jdk17}/bin/java" ]]; then
            echo "${mac_jdk17}"
            return 0
        fi
    fi

    local candidates=(
        "/Applications/Android Studio.app/Contents/jbr/Contents/Home"
        "$HOME/Applications/Android Studio.app/Contents/jbr/Contents/Home"
        "/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home"
        "/usr/local/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home"
    )
    for c in "${candidates[@]}"; do
        if [[ -x "${c}/bin/java" ]]; then
            echo "${c}"
            return 0
        fi
    done
    return 1
}

if DETECTED_JAVA="$(detect_java_home)"; then
    export JAVA_HOME="${DETECTED_JAVA}"
    export PATH="${JAVA_HOME}/bin:${PATH}"
fi

echo "[1/4] Java Toolchain: $(java -version 2>&1 | head -n 1)"

# 2. Auto-detect Android SDK & write git-ignored local.properties
detect_android_sdk() {
    local candidates=(
        "${ANDROID_HOME:-}"
        "${ANDROID_SDK_ROOT:-}"
        "$HOME/Library/Android/sdk"
        "$HOME/Android/Sdk"
        "/usr/local/lib/android/sdk"
        "/opt/homebrew/share/android-commandlinetools"
    )
    for c in "${candidates[@]}"; do
        if [[ -n "${c}" && -d "${c}" ]]; then
            echo "${c}"
            return 0
        fi
    done
    return 1
}

if ! SDK_DIR="$(detect_android_sdk)"; then
    echo "ERROR: Android SDK not found. Install Android Studio or set ANDROID_HOME." >&2
    exit 1
fi

export ANDROID_HOME="${SDK_DIR}"
export ANDROID_SDK_ROOT="${SDK_DIR}"
printf "sdk.dir=%s\n" "${SDK_DIR}" > "${SCRIPT_DIR}/local.properties"
echo "[2/4] Android SDK:    ${SDK_DIR}"

# 3. Build Release APK (R8 shrunk + auto-signed with persistent local release keystore)
cd "${SCRIPT_DIR}"
chmod +x ./gradlew
echo "[3/4] Compiling & signing Release APK..."
./gradlew assembleRelease

BUILT_APK="${SCRIPT_DIR}/app/build/outputs/apk/release/app-release.apk"
if [[ ! -f "${BUILT_APK}" ]]; then
    echo "ERROR: Expected APK not found at ${BUILT_APK}" >&2
    exit 1
fi

cp -f "${BUILT_APK}" "${OUTPUT_APK}"

# 4. Verify bundled Colab server engine & APK v2 signature
APK_ENTRIES="$(unzip -Z1 "${OUTPUT_APK}")"
if ! grep -Fxq "assets/app.py" <<< "${APK_ENTRIES}"; then
    echo "ERROR: assets/app.py missing from ${OUTPUT_APK}!" >&2
    exit 1
fi

APKSIGNER_BIN="$(find "${SDK_DIR}/build-tools" -name apksigner -type f 2>/dev/null | sort -V | tail -n 1 || true)"
if [[ -n "${APKSIGNER_BIN}" && -x "${APKSIGNER_BIN}" ]]; then
    VERIFY_OUT="$("${APKSIGNER_BIN}" verify --verbose "${OUTPUT_APK}")"
    printf "%s\n" "${VERIFY_OUT}" | sed -n '1,4p'
fi

APK_SIZE="$(du -h "${OUTPUT_APK}" | awk '{print $1}')"
echo "============================================================"
echo "[4/4] SUCCESS! Standalone Android Release APK ready:"
echo "      ${OUTPUT_APK} (${APK_SIZE})"
echo "      Install to phone: bash android_app/install_release_android.sh"
echo "============================================================"
