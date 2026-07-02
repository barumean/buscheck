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


def _get(url: str, params: dict[str, Any]) -> dict[str, Any] | None:
    try:
        resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except (requests.RequestException, ValueError) as exc:
        print(f"[경고] API 요청 실패 ({url}): {exc}", file=sys.stderr)
        return None


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
    """ARS번호(정류소번호)로 내부 stationId를 검색한다."""
    data = _get(
        STATION_SEARCH_URL,
        {"serviceKey": service_key, "keyword": station_name, "format": "json"},
    )
    if not data:
        return None
    msg_header = data.get("msgHeader", {})
    if msg_header.get("resultCode") not in (0, "0", 200, "200"):
        print(
            f"[경고] 정류소 검색 실패 ({station_name}): {msg_header.get('resultMessage')}",
            file=sys.stderr,
        )
        return None

    items = _extract_list(data.get("msgBody"), "busStationList", "busStationItem")
    for item in items:
        if str(item.get("mobileNo")) == str(mobile_no):
            station_id = item.get("stationId")
            return str(station_id) if station_id is not None else None

    if items:
        print(
            f"[경고] '{station_name}' 검색 결과 중 ARS번호 {mobile_no} 와 일치하는 "
            "정류소를 찾지 못했습니다. config/buses.json 에 stationId를 직접 입력해주세요.",
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

    msg_header = data.get("msgHeader", {})
    result_code = msg_header.get("resultCode")
    if result_code not in (0, "0", 200, "200"):
        return f"조회 실패 ({msg_header.get('resultMessage', result_code)})"

    items = _extract_list(data.get("msgBody"), "busArrivalList", "busArrivalItem")
    matches = [it for it in items if str(it.get("routeName", "")).strip() == route_name.strip()]

    if not matches:
        return "노선 정보 없음"

    matches.sort(key=lambda it: it.get("staOrder") or 0)
    return format_arrival(matches[0])


def load_config() -> list[dict[str, Any]]:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def build_rows(service_key: str, buses: list[dict[str, Any]]) -> list[dict[str, str]]:
    rows = []
    for bus in sorted(buses, key=lambda b: b.get("order", 0)):
        station_id = bus.get("stationId")
        if not station_id:
            station_id = resolve_station_id(service_key, bus["mobileNo"], bus["stationName"])

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


def main() -> None:
    service_key = get_service_key()
    buses = load_config()
    rows = build_rows(service_key, buses)

    table = render_markdown_table(rows)
    print(table)

    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as f:
            f.write("## 오늘 아침 버스 도착정보\n\n")
            f.write(table)
            f.write("\n")


if __name__ == "__main__":
    main()
