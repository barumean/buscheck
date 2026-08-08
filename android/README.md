# 버스확인 Android 앱

앱을 실행(또는 새로고침 버튼 탭)하면 GBIS(경기도 버스정보시스템) API v2를 직접 호출해
등록된 세 노선의 도착 예정 정보를 화면에 바로 표시합니다. GitHub Actions / 텔레그램을
거치지 않으므로 1~2초 안에 결과가 뜹니다.

- 언어/UI: Kotlin + Jetpack Compose (Material3)
- 네트워크: `HttpURLConnection` + `org.json` (외부 네트워크 라이브러리 없음)
- 조회 로직: 저장소 루트의 `scripts/check_bus_arrival.py` 와 동일
  (응답 언랩 → `msgHeader.resultCode` 확인 → `busArrivalList`에서 `routeName` 일치 →
   `staOrder` 최소 → `predictTimeSec1`을 분으로 변환)
- 등록 노선: `app/src/main/java/com/barumean/buscheck/BusModels.kt` 의 `BUS_LIST`
  (저장소 `config/buses.json` 과 동일)

## 요구 사항

- Android Studio (Koala/2024.1 이상 권장)
- JDK 17 (Android Studio 내장 JDK 사용 가능)
- Android SDK Platform 34
- minSdk 26 (Android 8.0) 이상 기기/에뮬레이터

## 서비스 인증키 넣는 방법 (둘 중 하나)

공공데이터포털(data.go.kr)에서 발급받은 **일반 인증키(Decoding)** 가 필요합니다.

1. **앱에서 직접 입력 (가장 간단)**
   앱 실행 → 상단 **"인증키"** → 키 붙여넣기 → 저장. 기기에만 저장됩니다.
   (배포용 APK를 그대로 받은 사람이 각자 자기 키를 넣는 방식)

2. **빌드에 주입** (`android/local.properties` 에 아래 한 줄 추가)
   ```properties
   BUS_SERVICE_KEY=여기에_디코딩_인증키
   ```
   `local.properties` 는 `.gitignore` 되어 저장소에 올라가지 않습니다.
   ⚠️ 이 방식으로 빌드한 APK에는 키가 포함되므로, 그 APK를 불특정 다수에게
   배포하지 마세요(내 기기용/가족용 정도로만).

## Android Studio 로 빌드

1. Android Studio → **Open** → 이 저장소의 `android/` 폴더 선택
2. 최초 **Gradle Sync** 를 기다립니다.
   - Gradle 래퍼(jar)가 없다는 안내가 나오면 Android Studio가 자동으로
     내려받아 구성합니다. (CLI로 하려면 `android/` 에서 `gradle wrapper` 한 번 실행)
3. 기기/에뮬레이터 연결 후 ▶ **Run** 으로 실행
4. 배포용 파일 만들기:
   - 디버그 APK: 메뉴 **Build → Build Bundle(s) / APK(s) → Build APK(s)**
     → `app/build/outputs/apk/debug/app-debug.apk`
   - 정식 배포용(서명된 릴리스): **Build → Generate Signed Bundle / APK** 에서
     키스토어를 만들어 서명

## 노선 변경

`BusModels.kt` 의 `BUS_LIST` 와 저장소 `config/buses.json` 을 함께 수정하세요.
`stationId`(9자리)와 `routeName` 이 실제 조회에 쓰입니다.
