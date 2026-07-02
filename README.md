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

### 1. API 인증키를 GitHub Secret으로 등록

리포지토리 **Settings → Secrets and variables → Actions → New repository secret** 에서
아래 이름으로 **디코딩된** 인증키를 등록하세요. (요청 시 requests 라이브러리가 URL 인코딩을
자동으로 처리하므로 인코딩된 키를 넣으면 이중 인코딩되어 오류가 납니다.)

```
이름: BUS_SERVICE_KEY
값:   (공공데이터포털에서 발급받은 디코딩 인증키)
```

### 2. 관심 버스 등록 (`config/buses.json`)

```json
{
  "order": 1,
  "mobileNo": "27109",             // 버스정류장에 표시된 정류소번호(ARS번호)
  "stationName": "인덕원퍼스비엘아파트.동아에코빌",
  "favorite": false,               // 즐겨타기 여부 (⭐ 표시용)
  "routeName": "1-1",              // 관심 노선번호
  "stationId": null                // GBIS 내부 정류소ID (모르면 null로 두면 자동 조회)
}
```

- `mobileNo` 는 버스 정류장 표지판에 적힌 **정류소번호(ARS번호)** 입니다.
- GBIS 도착정보 API는 `mobileNo`가 아닌 내부 `stationId` 를 요구하기 때문에,
  `stationId` 가 `null` 이면 실행 시 정류소 검색 API로 자동으로 찾습니다.
  - 자동 조회가 실패하거나 결과가 여러 개라 정확한 정류소를 특정하기 어려운 경우,
    아래 디버그 스크립트로 직접 확인 후 `stationId` 값을 채워 넣으면
    이후 실행부터는 검색 없이 바로 조회합니다(더 빠르고 안정적).

    ```bash
    BUS_SERVICE_KEY=디코딩키 python scripts/lookup_station.py "인덕원퍼스비엘아파트"
    ```

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
  (현재는 별도 푸시 알림 없이 Actions 실행 결과로만 확인하는 구성입니다. 텔레그램이나
  ntfy.sh 같은 푸시 알림이 필요하면 언제든 추가해 드릴 수 있습니다.)

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
