# buscheck

아침에 나갈 때 자주 타는 버스들의 도착 예정 정보를 한 번에 확인하는 프로그램입니다.
경기도 버스정보시스템(GBIS) 공공데이터 API(`https://apis.data.go.kr/6410000/busarrivalservice/v2`)를
사용하며, GitHub Actions로 매일 아침 자동 실행되거나 원할 때마다 수동으로 실행할 수 있습니다.

## 동작 방식

1. `config/buses.json` 에 등록해 둔 정류소 + 관심 노선 목록을 읽는다.
2. 각 정류소의 실시간 도착정보를 GBIS API에서 조회해 등록한 노선의 도착예정 시간을 찾는다.
3. 결과를 표(순번 / 정류소번호 / 관심정류소 / 즐겨타기 / 관심노선 / 도착예정정보)로
   콘솔 로그와 GitHub Actions 실행의 **Summary** 탭에 출력한다.

## 초기 설정

### 1. GitHub Secret 등록 방법 (공통)

이 프로젝트에서 쓰는 키(공공데이터포털 인증키, 텔레그램 봇 토큰 등)는 코드/설정 파일에 직접
적지 않고 전부 **GitHub Secret**으로 등록합니다. Secret은 리포지토리에 암호화되어 저장되고
워크플로 실행 중에만 환경변수로 주입되며, 코드나 로그에 노출되지 않습니다.

1. GitHub에서 리포지토리(`barumean/buscheck`) 페이지로 이동
2. 상단 **Settings** 탭 클릭 (모바일 앱에서는 리포지토리 메뉴 → Settings)
3. 좌측 메뉴에서 **Secrets and variables → Actions**
4. **New repository secret** 클릭
5. `Name`에 아래 secret 이름 중 하나, `Secret`에 해당 값을 입력하고 **Add secret**
6. 필요한 secret 개수만큼 반복

등록해야 할 secret 목록:

| Secret 이름 | 값 | 필수 여부 |
|---|---|---|
| `BUS_SERVICE_KEY` | 도착정보 API(`busarrivalservice`)용 **디코딩** 인증키 | 필수 |
| `STATION_SERVICE_KEY` | 정류소 조회 API(`busstationservice`)용 **디코딩** 인증키 | 선택 (stationId 자동 조회 시) |
| `TELEGRAM_BOT_TOKEN` | 텔레그램 봇 토큰 (아래 2번 참고) | 선택 (알림 원할 때) |
| `TELEGRAM_CHAT_ID` | 알림을 받을 나의 채팅 ID (아래 2번 참고) | 선택 (알림 원할 때) |

`BUS_SERVICE_KEY`는 반드시 **디코딩된** 키(`n/aR5AGp...==` 형태, `%2F`나 `%3D` 같은 URL 인코딩
문자가 없는 값)를 넣어야 합니다. 코드에서 `requests` 라이브러리가 요청 시 자동으로 URL 인코딩을
하기 때문에, 이미 인코딩된 키(`n%2FaR5AGp...%3D%3D`)를 넣으면 이중 인코딩되어 인증 오류가 납니다.

정류소 조회 API(`busstationservice`)가 도착정보 API와 **다른 인증키**로 발급된 경우,
그 디코딩 키를 `STATION_SERVICE_KEY` secret으로 등록하세요. 이 secret이 없으면 정류소 검색에도
`BUS_SERVICE_KEY` 를 그대로 사용합니다. (config의 모든 항목에 `stationId` 를 직접 넣었다면 정류소
조회 API 자체를 호출하지 않으므로 이 키는 불필요합니다.)

### 2. 텔레그램 푸시 알림 설정 (선택)

아침에 GitHub 앱을 열지 않고도 바로 결과를 받고 싶다면 텔레그램 봇으로 알림을 받을 수 있습니다.
설정하면 워크플로 실행 시 자동으로 메시지가 전송되며, 설정하지 않으면 기존처럼
Actions Summary로만 표시됩니다(생략 가능).

1. 텔레그램에서 **@BotFather** 를 검색해 대화 시작
2. `/newbot` 입력 → 봇 이름과 username(끝은 `bot`으로 끝나야 함) 설정
3. 생성 완료 시 나오는 **토큰**(`123456789:AA...` 형태) 복사 →
   `TELEGRAM_BOT_TOKEN` secret 값으로 등록
4. 새로 만든 봇과의 채팅방에서 아무 메시지나 하나 보내기 (예: "hi")
   - 봇은 사용자가 먼저 말을 걸어야 메시지를 보낼 수 있습니다
5. 나의 chat_id 확인: 브라우저에서 아래 주소 접속 (TOKEN을 3번에서 받은 값으로 교체)

   ```
   https://api.telegram.org/bot<TOKEN>/getUpdates
   ```

   응답 JSON에서 `"message":{"chat":{"id": 123456789, ...}}` 의 `id` 값이 chat_id입니다.
   (또는 텔레그램에서 **@userinfobot** 을 검색해 대화하면 내 id를 바로 알려줍니다)
6. 그 값을 `TELEGRAM_CHAT_ID` secret으로 등록

이후 워크플로가 실행되면 `scripts/check_bus_arrival.py`가 두 secret이 모두 설정된 경우에만
텔레그램으로 도착정보를 전송합니다. (`send_telegram_message` 함수, 실패해도 워크플로 자체는
계속 진행되고 경고만 로그에 남습니다.)

### 3. 관심 버스 등록 (`config/buses.json`)

```json
{
  "order": 1,
  "mobileNo": "27109",             // 버스정류장에 표시된 정류소번호(ARS번호)
  "stationName": "인덕원퍼스비엘아파트.동아에코빌",
  "favorite": false,               // 즐겨타기 여부 (⭐ 표시용)
  "routeName": "1-1",              // 관심 노선번호
  "stationId": "27109"             // GBIS 도착정보 API 호출에 쓰이는 정류소 ID
}
```

- `mobileNo` 는 버스 정류장 표지판에 적힌 **정류소번호(ARS번호, 예: 27109)** 이고,
  `stationId` 는 도착정보 API가 실제로 요구하는 **내부 9자리 ID(예: 200000177)** 입니다.
  **이 둘은 서로 다른 값입니다.** ARS번호를 stationId로 넣으면 API가 "결과가 존재하지
  않습니다(코드 4)"를 반환합니다.
- `stationId` 를 모르면 `null` 로 두세요. 실행 시 정류소 조회 API로 ARS번호에 해당하는
  내부 stationId를 자동으로 찾습니다. **단, 이 자동 조회에는 도착정보 API와 별개로
  "정류소 조회 API(busstationservice)" 활용신청이 필요합니다** (아래 참고).
- 자동 조회 대신 stationId를 직접 알고 있다면 그 9자리 값을 `stationId` 에 넣으면
  조회 API 없이 바로 동작합니다.

    ```bash
    # 정류소 조회 API 활용신청이 되어 있으면 stationId를 직접 확인할 수 있음
    BUS_SERVICE_KEY=디코딩키 python scripts/lookup_station.py "정류소명"
    ```

#### 정류소 조회 API(busstationservice) 활용신청

stationId 자동 조회를 쓰려면 공공데이터포털에서 도착정보 API와 **별도로** 정류소 조회
API를 신청해야 합니다(신청 즉시 승인, 무료).

1. 공공데이터포털에서 **경기도 버스정류소 정보 조회** 서비스 검색
   (엔드포인트 `https://apis.data.go.kr/6410000/busstationservice/v2`)
2. **활용신청** → 승인 후 같은 `BUS_SERVICE_KEY` 로 호출됩니다(별도 키 불필요).
3. 신청하지 않으면 자동 조회 시 **403 Forbidden** 이 나며, 이 경우 위처럼 `stationId` 를
   직접 입력해야 합니다.

- 노선이 상/하행 등으로 같은 이름이 여러 개 존재하는 정류소라면, 그 중 정류소 순번(`staOrder`)이
  가장 빠른 노선을 사용합니다. 원하는 방향이 아니라면 `scripts/lookup_station.py` 조회 결과와
  API 미리보기를 참고해 노선을 특정하는 방식으로 스크립트를 조정해야 할 수 있습니다.

## 실행 방법

### GitHub Actions (자동/수동)

- **자동 실행**: 매일 06:20(KST)에 자동 실행됩니다 (`.github/workflows/bus-check.yml`,
  cron은 GitHub Actions 스케줄 특성상 몇 분 지연될 수 있습니다).
- **수동 실행**: GitHub 웹 또는 **GitHub Mobile 앱**에서 리포지토리 →
  **Actions → 아침 버스 도착정보 확인 → Run workflow** 로 언제든 실행할 수 있습니다.
- **결과 확인**: 실행이 끝난 워크플로 런을 열면 **Summary** 탭에 도착정보 표가 표시됩니다.
- **텔레그램 알림**: `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` secret을 등록해두면
  (위 "초기 설정 → 2. 텔레그램 푸시 알림 설정" 참고) 실행할 때마다 텔레그램 메시지로도 받습니다.

### 로컬 실행

```bash
pip install -r requirements.txt
BUS_SERVICE_KEY=디코딩키 python scripts/check_bus_arrival.py
```

## 파일 구조

```
config/buses.json              관심 정류소·노선 등록 목록
scripts/check_bus_arrival.py   도착정보 조회 및 표 출력 메인 스크립트
scripts/lookup_station.py      정류소명으로 stationId를 찾는 디버그용 CLI
.github/workflows/bus-check.yml GitHub Actions 워크플로 (스케줄 + 수동 실행)
```
