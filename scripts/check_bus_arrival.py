#!/usr/bin/env python3
"""아침에 등록된 관심 버스들의 도착 예정 정보를 조회해 표로 출력한다.

경기도 버스정보시스템(GBIS) API v2 (data.go.kr, 6410000) 사용.
- 정류소 검색: /busstationservice/v2/getBusStationListv2 (ARS번호로 stationId 확인)
- 도착 정보:   /busarrivalservice/v2/getBusArrivalListv2 (정류소에 정차하는 모든 노선)
"""
from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path
from typing import Any

import requests

BASE_URL = "https://apis.data.go.kr/6410000"
ARRIVAL_URL = f"{BASE_URL}/busarrivalservice/v2/getBusArrivalListv2"
STATION_SEARCH_URL = f"{BASE_URL}/busstationservice/v2/getBusStationListv2"

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "buses.json"
REQUEST_TIMEOUT = 10


def get_service_key() -> str:
    key = os.environ.get("BUS_SERVICE_KEY")
    if not key:
        sys.exit(
            "환경변수 BUS_SERVICE_KEY 가 설정되어 있지 않습니다. "
            "공공데이터포털에서 발급받은 디코딩 인증키를 설정해주세요."
        )
    return key


def get_station_key() -> str:
    """정류소 조회 API용 키. 별도 지정이 없으면 도착정보 키를 재사용한다.

    정류소 조회 API가 도착정보 API와 다른 인증키로 발급된 경우
    STATION_SERVICE_KEY 시크릿을 설정하면 그 키로 정류소 검색을 수행한다.
    """
    return os.environ.get("STATION_SERVICE_KEY") or get_service_key()


def _get(url: str, params: dict[str, Any]) -> dict[str, Any] | None:
    try:
        resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except (requests.RequestException, ValueError) as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        print(f"[경고] API 요청 실패 ({url}): {exc}", file=sys.stderr)
        if status == 403 and "busstationservice" in url:
            print(
                "[안내] 정류소 조회 API(busstationservice)가 활용신청되지 않아 stationId 자동 "
                "조회가 불가합니다. 공공데이터포털에서 해당 API를 활용신청하거나, "
                "config/buses.json의 각 항목에 9자리 stationId를 직접 입력하세요.",
                file=sys.stderr,
            )
        return None


DEBUG = os.environ.get("DEBUG_BUS") not in (None, "", "0", "false", "False")


def _debug_dump(label: str, data: Any) -> None:
    if not DEBUG:
        return
    try:
        text = json.dumps(data, ensure_ascii=False)
    except (TypeError, ValueError):
        text = str(data)
    print(f"[디버그] {label}: {text[:2000]}", file=sys.stderr)


def _unwrap(data: dict[str, Any] | None) -> dict[str, Any]:
    """공공데이터 API는 응답을 최상위 또는 'response' 키 아래에 두기도 한다.

    msgHeader / msgBody 가 나오는 실제 계층을 찾아 dict로 돌려준다.
    """
    if not data:
        return {}
    if "msgHeader" in data or "msgBody" in data:
        return data
    for key in ("response", "Response", "OpenAPI_ServiceResponse"):
        inner = data.get(key)
        if isinstance(inner, dict):
            return inner
    return data


def _extract_list(msg_body: dict[str, Any] | None, *keys: str) -> list[dict[str, Any]]:
    if not msg_body:
        return []
    for key in keys:
        value = msg_body.get(key)
        if value is None:
            continue
        if isinstance(value, list):
            return value
        if isinstance(value, dict):
            return [value]
    return []


def resolve_station_id(service_key: str, mobile_no: str, station_name: str) -> str | None:
    """ARS번호(정류소번호)로 내부 stationId를 검색한다.

    정류소 조회 API의 keyword 는 정류소명뿐 아니라 정류소번호(ARS)도 지원하므로,
    ARS번호로 검색해 정확히 일치하는 정류소의 stationId 를 돌려준다. ARS 검색이
    비면 정류소명으로 한 번 더 시도한다.
    """
    for keyword in (str(mobile_no), station_name):
        if not keyword:
            continue
        data = _get(
            STATION_SEARCH_URL,
            {"serviceKey": service_key, "keyword": keyword, "format": "json"},
        )
        if not data:
            return None
        _debug_dump(f"정류소 검색 원문 (keyword={keyword})", data)
        body = _unwrap(data)
        msg_header = body.get("msgHeader") or {}
        if msg_header.get("resultCode") not in (0, "0", 200, "200"):
            # 코드 4(결과 없음)면 다음 keyword로 재시도, 그 외는 경고 후 중단
            if msg_header.get("resultCode") in (4, "4"):
                continue
            print(
                f"[경고] 정류소 검색 실패 (keyword={keyword}): {msg_header.get('resultMessage')}",
                file=sys.stderr,
            )
            return None

        items = _extract_list(body.get("msgBody"), "busStationList", "busStationItem")
        for item in items:
            # API가 mobileNo를 " 27109"처럼 공백 포함으로 주기도 하므로 strip 후 비교
            if str(item.get("mobileNo")).strip() == str(mobile_no).strip():
                station_id = item.get("stationId")
                if station_id is not None:
                    return str(station_id)

    print(
        f"[경고] ARS번호 {mobile_no}({station_name})에 해당하는 stationId를 찾지 못했습니다. "
        "config/buses.json 에 9자리 stationId를 직접 입력해주세요.",
        file=sys.stderr,
    )
    return None


def format_arrival(item: dict[str, Any]) -> str:
    flag = str(item.get("flag") or "").strip()
    predict_sec = item.get("predictTimeSec1")

    if flag and any(word in flag for word in ("종료", "출발대기", "회차")):
        return flag

    if predict_sec in (None, "", 0):
        return "도착 정보 없음"

    try:
        seconds = int(predict_sec)
    except (TypeError, ValueError):
        return "도착 정보 없음"

    if seconds <= 0:
        return "도착 정보 없음"

    minutes = math.ceil(seconds / 60)
    if minutes <= 0:
        return "곧 도착"
    return f"{minutes}분 후 도착예정"


def get_arrival_info(service_key: str, station_id: str, route_name: str) -> str:
    data = _get(
        ARRIVAL_URL,
        {"serviceKey": service_key, "stationId": station_id, "format": "json"},
    )
    if not data:
        return "조회 실패"

    _debug_dump(f"도착정보 원문 (stationId={station_id})", data)
    body = _unwrap(data)
    msg_header = body.get("msgHeader") or {}
    result_code = msg_header.get("resultCode")
    if result_code not in (0, "0", 200, "200"):
        detail = msg_header.get("resultMessage")
        if detail is None:
            # 인증/트래픽 초과 등은 cmmMsgHeader 아래에 오기도 한다.
            detail = (
                body.get("cmmMsgHeader", {}).get("returnAuthMsg")
                or data.get("cmmMsgHeader", {}).get("returnAuthMsg")
                or result_code
            )
        return f"조회 실패 ({detail})"

    items = _extract_list(body.get("msgBody"), "busArrivalList", "busArrivalItem")
    matches = [it for it in items if str(it.get("routeName", "")).strip() == route_name.strip()]

    if not matches:
        return "노선 정보 없음"

    matches.sort(key=lambda it: it.get("staOrder") or 0)
    return format_arrival(matches[0])


def load_config() -> list[dict[str, Any]]:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def build_rows(
    service_key: str, station_key: str, buses: list[dict[str, Any]]
) -> list[dict[str, str]]:
    rows = []
    for bus in sorted(buses, key=lambda b: b.get("order", 0)):
        station_id = bus.get("stationId")
        if not station_id:
            station_id = resolve_station_id(station_key, bus["mobileNo"], bus["stationName"])

        if not station_id:
            arrival = "정류소 ID 확인 실패"
        else:
            arrival = get_arrival_info(service_key, station_id, bus["routeName"])

        rows.append(
            {
                "order": str(bus.get("order", "")),
                "mobileNo": bus["mobileNo"],
                "stationName": bus["stationName"],
                "favorite": "⭐" if bus.get("favorite") else "",
                "routeName": bus["routeName"],
                "arrival": arrival,
            }
        )
    return rows


def render_markdown_table(rows: list[dict[str, str]]) -> str:
    header = "| 순번 | 정류소번호 | 관심정류소 | 즐겨타기 | 관심노선 | 도착예정정보 |"
    separator = "|---|---|---|---|---|---|"
    lines = [header, separator]
    for row in rows:
        lines.append(
            f"| {row['order']} | {row['mobileNo']} | {row['stationName']} | "
            f"{row['favorite']} | {row['routeName']} | {row['arrival']} |"
        )
    return "\n".join(lines)


def render_telegram_text(rows: list[dict[str, str]]) -> str:
    lines = ["🚌 오늘 아침 버스 도착정보"]
    for row in rows:
        star = f" {row['favorite']}" if row["favorite"] else ""
        lines.append(
            f"{row['order']}. [{row['routeName']}]{star} {row['stationName']} "
            f"({row['mobileNo']}) - {row['arrival']}"
        )
    return "\n".join(lines)


def build_telegram_token(token: str, bot_id: str | None) -> str:
    """완전한 봇 토큰(`봇번호:인증문자열`)을 만든다.

    - secret에 이미 완전한 토큰(`123456:AAHk...`)을 넣었으면 그대로 사용
    - 인증문자열만 넣고(콜론 없음) TELEGRAM_BOT_ID 를 따로 넣었으면 둘을 합침
    - 앞에 'bot' 접두어나 공백이 섞여도 정리
    """
    token = token.strip()
    if token.lower().startswith("bot"):
        token = token[3:]
    if ":" not in token and bot_id:
        token = f"{bot_id.strip()}:{token}"
    return token


def send_telegram_message(token: str, chat_id: str, text: str, bot_id: str | None = None) -> None:
    token = build_telegram_token(token, bot_id)
    chat_id = chat_id.strip()
    # 토큰 값은 노출하지 않고 형태(길이/콜론 위치)만 디버그로 확인한다.
    if DEBUG:
        colon = token.find(":")
        print(
            f"[디버그] 텔레그램 토큰 길이={len(token)}, ':' 위치={colon}, "
            f"chat_id 길이={len(chat_id)} (정상 토큰은 대략 46자, '숫자:영숫자' 형태)",
            file=sys.stderr,
        )
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        resp = requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        body = resp.json()
        if not body.get("ok"):
            print(f"[경고] 텔레그램 전송 실패: {body}", file=sys.stderr)
        elif DEBUG:
            print("[디버그] 텔레그램 전송 성공", file=sys.stderr)
    except (requests.RequestException, ValueError) as exc:
        detail = getattr(getattr(exc, "response", None), "text", "")
        print(f"[경고] 텔레그램 전송 실패: {exc} {detail}".strip(), file=sys.stderr)


def main() -> None:
    service_key = get_service_key()
    station_key = get_station_key()
    buses = load_config()
    rows = build_rows(service_key, station_key, buses)

    table = render_markdown_table(rows)
    print(table)

    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as f:
            f.write("## 오늘 아침 버스 도착정보\n\n")
            f.write(table)
            f.write("\n")

    telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    telegram_chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    telegram_bot_id = os.environ.get("TELEGRAM_BOT_ID")
    if telegram_token and telegram_chat_id:
        send_telegram_message(
            telegram_token, telegram_chat_id, render_telegram_text(rows), telegram_bot_id
        )
    else:
        print(
            "[안내] TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID 가 설정되지 않아 "
            "텔레그램 알림은 전송하지 않았습니다.",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
