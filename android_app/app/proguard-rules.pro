# Keep EasyColab models, FileProvider & OkHttp / Media3 reflection surfaces safe under R8
-keep class app.easycolab.studio.** { *; }
-keep class androidx.core.content.FileProvider { *; }
-dontwarn okhttp3.**
-dontwarn okio.**
-keepattributes Signature, InnerClasses, EnclosingMethod, RuntimeVisibleAnnotations
