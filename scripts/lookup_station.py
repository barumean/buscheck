#!/usr/bin/env python3
"""정류소명(키워드)으로 GBIS 내부 stationId 를 검색하는 디버그용 CLI.

사용법:
  BUS_SERVICE_KEY=발급받은디코딩키 python scripts/lookup_station.py "인덕원퍼스비엘아파트"

자동 조회(check_bus_arrival.py)가 실패할 때, 이 스크립트로 결과를 직접 확인하고
config/buses.json 의 해당 항목에 "stationId" 값을 채워 넣으면 이후에는 검색 없이
바로 도착정보를 조회한다.
"""
from __future__ import annotations

import os
import sys

import requests

STATION_SEARCH_URL = "https://apis.data.go.kr/6410000/busstationservice/v2/getBusStationListv2"


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("사용법: python scripts/lookup_station.py <정류소명 키워드>")

    service_key = os.environ.get("BUS_SERVICE_KEY")
    if not service_key:
        sys.exit("환경변수 BUS_SERVICE_KEY 를 설정해주세요.")

    keyword = sys.argv[1]
    resp = requests.get(
        STATION_SEARCH_URL,
        params={"serviceKey": service_key, "keyword": keyword, "format": "json"},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()

    msg_header = data.get("msgHeader", {})
    if msg_header.get("resultCode") not in (0, "0", 200, "200"):
        sys.exit(f"조회 실패: {msg_header.get('resultMessage')}")

    body = data.get("msgBody", {})
    items = body.get("busStationList") or body.get("busStationItem") or []
    if isinstance(items, dict):
        items = [items]

    if not items:
        print("검색 결과가 없습니다.")
        return

    for item in items:
        print(
            f"stationId={item.get('stationId')}\t"
            f"mobileNo(ARS/정류소번호)={item.get('mobileNo')}\t"
            f"stationName={item.get('stationName')}"
        )


if __name__ == "__main__":
    main()
