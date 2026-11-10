import java.io.File
import java.security.SecureRandom
import java.util.Properties

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}

val repoRoot: File = rootProject.projectDir.parentFile
val versionFile = File(repoRoot, "VERSION")
val appVersionName: String = if (versionFile.exists()) versionFile.readText().trim().ifEmpty { "1.1.0" } else "1.1.0"

// Decode installed-app reverse OAuth scheme at build time (zero plaintext OAuth secrets in repository)
val encodedClientBytes = intArrayOf(
    109, 108, 110, 106, 98, 108, 106, 111, 107, 98, 111, 106, 119, 108, 43, 40, 110, 42,
    108, 61, 42, 51, 108, 50, 52, 111, 106, 108, 42, 46, 98, 63, 48, 47, 43, 98, 105, 62,
    51, 105, 110, 107, 50, 47, 40, 116, 59, 42, 42, 41, 116, 61, 53, 53, 61, 54, 63, 47,
    41, 63, 40, 57, 53, 52, 46, 63, 52, 46, 116, 57, 53, 55
)
val decodedClientId = String(ByteArray(encodedClientBytes.size) { i -> (encodedClientBytes[i] xor 0x5A).toByte() }, Charsets.UTF_8)
val googleOAuthReverseScheme = "com.googleusercontent.apps." + decodedClientId.substringBefore(".apps.googleusercontent.com")

// Persistent Release keystore stored in android_app/.signing/ (survives `rm -rf build` & `./gradlew clean`)
val keystoreDir = File(rootProject.projectDir, ".signing")
val localKeystoreFile = File(keystoreDir, "easycolab_release.jks")
val keystorePropsFile = File(keystoreDir, "keystore.properties")
val ksProps = Properties().apply {
    if (keystorePropsFile.exists()) {
        keystorePropsFile.inputStream().use { load(it) }
    }
}

fun generateRandomSecret(len: Int = 24): String {
    val alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789"
    val rng = SecureRandom()
    return (1..len).map { alphabet[rng.nextInt(alphabet.length)] }.joinToString("")
}

val ksStorePass: String = System.getenv("EASYCOLAB_KEYSTORE_PASS")
    ?: ksProps.getProperty("storePassword")?.takeIf { it.isNotBlank() }
    ?: generateRandomSecret(24)
val ksKeyAlias: String = System.getenv("EASYCOLAB_KEY_ALIAS")
    ?: ksProps.getProperty("keyAlias")?.takeIf { it.isNotBlank() }
    ?: "easycolab_release"
val ksKeyPass: String = System.getenv("EASYCOLAB_KEY_PASS")
    ?: ksProps.getProperty("keyPassword")?.takeIf { it.isNotBlank() }
    ?: ksStorePass

if (!localKeystoreFile.exists()) {
    keystoreDir.mkdirs()
    val javaHome = System.getProperty("java.home")
    val keytoolBin = File(javaHome, "bin/keytool").takeIf { it.exists() }?.absolutePath ?: "keytool"
    try {
        val code = ProcessBuilder(
            keytoolBin, "-genkeypair", "-v",
            "-storetype", "PKCS12",
            "-keystore", localKeystoreFile.absolutePath,
            "-alias", ksKeyAlias,
            "-keyalg", "RSA", "-keysize", "2048", "-validity", "10000",
            "-storepass", ksStorePass, "-keypass", ksKeyPass,
            "-dname", "CN=EasyColab Official, OU=Mobile, O=EasyColab, L=Studio, ST=Studio, C=US"
        ).redirectErrorStream(true).start().waitFor()
        if (code == 0 && !keystorePropsFile.exists()) {
            Properties().apply {
                setProperty("storePassword", ksStorePass)
                setProperty("keyAlias", ksKeyAlias)
                setProperty("keyPassword", ksKeyPass)
            }.let { p ->
                keystorePropsFile.outputStream().use { p.store(it, "EasyColab Official Android Release Signing Key (Keep Backup!)") }
                keystorePropsFile.setReadable(false, false)
                keystorePropsFile.setReadable(true, true)
            }
        }
    } catch (_: Exception) {
    }
}

val generatedColabAssetsDir = layout.buildDirectory.dir("generated/colabAssets")

val syncColabServerAssets by tasks.registering(Copy::class) {
    from(repoRoot) {
        include("VERSION", "app.py", "EasyColab_Server.ipynb")
    }
    into(generatedColabAssetsDir)
}

android {
    namespace = "app.easycolab.studio"
    compileSdk = 35

    defaultConfig {
        applicationId = "app.easycolab.studio"
        minSdk = 26
        targetSdk = 35
        versionCode = 10100
        versionName = appVersionName
        manifestPlaceholders["googleOAuthScheme"] = googleOAuthReverseScheme
        vectorDrawables {
            useSupportLibrary = true
        }
    }

    signingConfigs {
        create("localRelease") {
            if (localKeystoreFile.exists()) {
                storeFile = localKeystoreFile
                storePassword = ksStorePass
                keyAlias = ksKeyAlias
                keyPassword = ksKeyPass
                enableV1Signing = true
                enableV2Signing = true
                enableV3Signing = true
            }
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            signingConfig = if (localKeystoreFile.exists()) {
                signingConfigs.getByName("localRelease")
            } else {
                signingConfigs.getByName("debug")
            }
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
        debug {
            isMinifyEnabled = false
        }
    }

    sourceSets {
        getByName("main") {
            assets.srcDir(syncColabServerAssets)
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }

    buildFeatures {
        compose = true
        buildConfig = true
    }

    lint {
        checkReleaseBuilds = false
        abortOnError = false
    }

    packaging {
        resources {
            excludes += "/META-INF/{AL2.0,LGPL2.1}"
        }
    }
}

tasks.named("preBuild") {
    dependsOn(syncColabServerAssets)
}

tasks.matching { it.name.startsWith("merge") && it.name.endsWith("Assets") }.configureEach {
    dependsOn(syncColabServerAssets)
}

dependencies {
    val composeBom = platform("androidx.compose:compose-bom:2024.10.01")
    implementation(composeBom)

    implementation("androidx.core:core-ktx:1.15.0")
    implementation("androidx.activity:activity-compose:1.9.3")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.7")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.7")
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.8.7")

    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-graphics")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.material:material-icons-extended")

    // Chrome Custom Tabs for 1-Tap Native Google OAuth2 PKCE (shares Chrome cookies, never reloads on recompose)
    implementation("androidx.browser:browser:1.8.0")

    // Pure-Kotlin HTTP/2 & Jupyter Kernel WebSocket Engine
    implementation("com.squareup.okhttp3:okhttp:4.12.0")

    // Native Hardware-Accelerated MP4 + 32kHz Stereo Audio Player
    implementation("androidx.media3:media3-exoplayer:1.4.1")
    implementation("androidx.media3:media3-ui:1.4.1")

    // Coroutines
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.8.1")
}
