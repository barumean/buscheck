import java.util.Properties

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

// local.properties 또는 -PBUS_SERVICE_KEY 로 넘긴 서비스 키를 읽는다(없으면 빈 문자열).
// 이 값은 공개 저장소에 커밋되지 않는다(local.properties 는 .gitignore 처리됨).
fun readServiceKey(): String {
    (project.findProperty("BUS_SERVICE_KEY") as String?)?.let { if (it.isNotBlank()) return it }
    val f = rootProject.file("local.properties")
    if (f.exists()) {
        val props = Properties()
        f.inputStream().use { props.load(it) }
        return props.getProperty("BUS_SERVICE_KEY", "")
    }
    return ""
}

android {
    namespace = "com.barumean.buscheck"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.barumean.buscheck"
        minSdk = 26
        targetSdk = 34
        versionCode = 1
        versionName = "1.0"

        buildConfigField("String", "BUS_SERVICE_KEY", "\"${readServiceKey()}\"")
    }

    buildFeatures {
        compose = true
        buildConfig = true
    }
    composeOptions {
        kotlinCompilerExtensionVersion = "1.5.14"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro",
            )
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.2")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.2")
    implementation("androidx.activity:activity-compose:1.9.0")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.8.1")

    implementation(platform("androidx.compose:compose-bom:2024.06.00"))
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-graphics")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.compose.material3:material3")

    debugImplementation("androidx.compose.ui:ui-tooling")
}
