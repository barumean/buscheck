# 폰에서 원탭으로 실행하기 (홈 화면 버튼)

아침에 나가면서 홈 화면 아이콘 **한 번**만 누르면 워크플로가 실행되고,
약 20초 뒤 텔레그램으로 도착정보가 오도록 만드는 방법입니다.

원리: 홈 화면 버튼이 GitHub의 "워크플로 수동 실행" API에 POST 요청 1건을 보냅니다.

```
POST https://api.github.com/repos/barumean/buscheck/actions/workflows/bus-check.yml/dispatches
Headers:
  Authorization: Bearer <토큰>
  Accept: application/vnd.github+json
Body(JSON):
  {"ref": "claude/bus-arrival-api-ceyrmn"}
```

`ref` 는 워크플로가 있는 브랜치(= 이 저장소 기본 브랜치)입니다.

---

## 1단계. GitHub 파인그레인드 토큰 발급 (공통, 1회)

버튼이 GitHub에 요청하려면 인증 토큰이 필요합니다. 권한을 이 저장소 Actions로만
최소화해 발급합니다.

1. GitHub 웹 로그인 → 우측 상단 프로필 → **Settings**
2. 좌측 맨 아래 **Developer settings**
3. **Personal access tokens → Fine-grained tokens → Generate new token**
4. 설정값
   - **Token name**: `buscheck-trigger` (아무거나)
   - **Expiration**: 원하는 기간(예: 1년 / No expiration)
   - **Repository access**: **Only select repositories** → `barumean/buscheck` 선택
   - **Permissions → Repository permissions → Actions**: **Read and write** 로 설정
     - (이 한 가지 권한만 있으면 됩니다. 나머지는 기본 No access 그대로)
5. **Generate token** → 나오는 `github_pat_...` 값을 복사
   - ⚠️ 이 값은 다시 볼 수 없으니 바로 다음 단계에 붙여넣으세요.
   - ⚠️ 이 토큰은 폰의 단축어/앱에만 저장하고 외부에 노출하지 마세요.

---

## 2-A단계. iPhone (기본 "단축어" 앱)

1. **단축어** 앱 → **+** (새 단축어)
2. 동작 검색 → **"URL의 내용 가져오기"(Get Contents of URL)** 추가
3. URL 입력:
   ```
   https://api.github.com/repos/barumean/buscheck/actions/workflows/bus-check.yml/dispatches
   ```
4. "**요청 표시**"(Show More) 펼치고:
   - **방법(Method)**: `POST`
   - **헤더(Headers)** 추가:
     - `Authorization` = `Bearer github_pat_...(발급받은 토큰)`
     - `Accept` = `application/vnd.github+json`
   - **본문(Request Body)**: `JSON` 선택 → 필드 추가
     - 키 `ref` (텍스트) = `claude/bus-arrival-api-ceyrmn`
5. (선택) 맨 아래 동작으로 **"알림 표시"** 추가 → "버스 요청 보냄 🚌" 같은 문구
6. 우측 상단 이름 지정(예: **버스확인**) → 완료
7. 단축어를 홈 화면에 추가: 단축어 길게 누르기 → **공유** → **홈 화면에 추가**
   - 이제 홈 화면 아이콘 한 번 = 실행. 결과는 텔레그램으로 도착.

> 팁: "뒤로 탭"(설정 → 손쉬운 사용 → 터치 → 뒤로 탭)에 이 단축어를 지정하면
> 폰 뒷면을 두 번 톡톡 쳐서 실행할 수도 있습니다.

---

## 2-B단계. Android ("HTTP Shortcuts" 무료 앱)

1. Play 스토어에서 **HTTP Shortcuts** 설치
2. **+** → **Regular shortcut**
3. 설정:
   - **Method**: `POST`
   - **URL**:
     ```
     https://api.github.com/repos/barumean/buscheck/actions/workflows/bus-check.yml/dispatches
     ```
   - **Request Headers** 추가:
     - `Authorization` = `Bearer github_pat_...(발급받은 토큰)`
     - `Accept` = `application/vnd.github+json`
   - **Request Body** → Content type `application/json`, 내용:
     ```json
     {"ref": "claude/bus-arrival-api-ceyrmn"}
     ```
4. 이름 지정(예: **버스확인**), 아이콘 선택 → 저장
5. 목록에서 해당 단축어 → **Place on home screen**(홈 화면에 위젯/아이콘 배치)
   - 이제 홈 화면 아이콘 한 번 = 실행. 결과는 텔레그램으로 도착.

---

## 동작 확인 / 문제 해결

- **성공 응답**: GitHub는 이 요청에 본문 없이 **HTTP 204 No Content** 를 반환합니다.
  화면에 아무 내용이 없어도 정상입니다. 약 20초 뒤 텔레그램 메시지가 오면 성공.
- **401 Unauthorized**: 토큰이 틀렸거나 만료됨 → 토큰 재발급/재입력.
- **403 / "Resource not accessible"**: 토큰의 **Actions: Read and write** 권한 또는
  저장소 접근 범위가 빠짐 → 토큰 권한 다시 확인.
- **404**: URL의 저장소/워크플로 파일명(`bus-check.yml`)이나 `ref` 브랜치명이 틀림.
- 실행 자체는 **GitHub 앱 → Actions** 에서도 확인할 수 있습니다.

---

## (대안) GitHub 모바일 앱으로 실행 — 설정 불필요

토큰 발급이 번거로우면, **GitHub 모바일 앱**에서 바로 실행할 수도 있습니다.

1. GitHub 앱 → `barumean/buscheck` 저장소
2. **Actions** 탭 → **아침 버스 도착정보 확인**
3. **Run workflow** → 브랜치 `claude/bus-arrival-api-ceyrmn` → 실행

탭 수는 더 많지만 추가 설정(토큰)이 필요 없습니다.
