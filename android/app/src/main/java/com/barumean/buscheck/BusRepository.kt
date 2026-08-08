package com.barumean.buscheck

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder
import kotlin.math.ceil

/**
 * 경기도 버스정보시스템(GBIS) API v2 로 도착정보를 조회한다.
 * 파이썬 스크립트(scripts/check_bus_arrival.py)의 조회/파싱 로직을 그대로 옮긴 것.
 */
object BusRepository {
    private const val ARRIVAL_URL =
        "https://apis.data.go.kr/6410000/busarrivalservice/v2/getBusArrivalListv2"

    /** 특정 정류소에서 특정 노선의 도착예정 문구를 돌려준다. */
    suspend fun getArrival(serviceKey: String, stationId: String, routeName: String): String =
        withContext(Dispatchers.IO) {
            try {
                val json = fetch(serviceKey, stationId) ?: return@withContext "조회 실패"
                parseArrival(json, routeName)
            } catch (e: Exception) {
                "조회 실패 (${e.message ?: e.javaClass.simpleName})"
            }
        }

    private fun fetch(serviceKey: String, stationId: String): JSONObject? {
        val key = URLEncoder.encode(serviceKey, "UTF-8")
        val urlStr = "$ARRIVAL_URL?serviceKey=$key&stationId=$stationId&format=json"
        val conn = (URL(urlStr).openConnection() as HttpURLConnection).apply {
            requestMethod = "GET"
            connectTimeout = 10_000
            readTimeout = 10_000
        }
        try {
            val code = conn.responseCode
            val stream = if (code in 200..299) conn.inputStream else conn.errorStream
            val text = stream?.bufferedReader()?.use { it.readText() }?.trim() ?: return null
            // 인증키 오류 등에서는 JSON 대신 XML 오류 문서가 오기도 한다.
            if (text.startsWith("<")) {
                throw RuntimeException("인증키/요청 오류(비정상 응답)")
            }
            return JSONObject(text)
        } finally {
            conn.disconnect()
        }
    }

    /** 응답이 최상위 또는 response 키 아래에 올 수 있어 실제 계층을 찾는다. */
    private fun unwrap(data: JSONObject): JSONObject {
        if (data.has("msgHeader") || data.has("msgBody")) return data
        for (key in listOf("response", "Response", "OpenAPI_ServiceResponse")) {
            data.optJSONObject(key)?.let { return it }
        }
        return data
    }

    /** msgBody 아래의 리스트(항목이 하나면 객체로 오기도 함)를 항상 List 로 만든다. */
    private fun extractList(msgBody: JSONObject?, vararg keys: String): List<JSONObject> {
        if (msgBody == null) return emptyList()
        for (key in keys) {
            when (val v = msgBody.opt(key)) {
                is JSONArray -> return (0 until v.length()).mapNotNull { v.optJSONObject(it) }
                is JSONObject -> return listOf(v)
            }
        }
        return emptyList()
    }

    private fun parseArrival(data: JSONObject, routeName: String): String {
        val body = unwrap(data)
        val header = body.optJSONObject("msgHeader")
        val resultCode = header?.opt("resultCode")?.toString()
        if (resultCode != null && resultCode != "0" && resultCode != "200") {
            val detail = header.opt("resultMessage") ?: resultCode
            return "조회 실패 ($detail)"
        }
        val items = extractList(body.optJSONObject("msgBody"), "busArrivalList", "busArrivalItem")
        val matches = items.filter { it.optString("routeName").trim() == routeName.trim() }
        if (matches.isEmpty()) return "노선 정보 없음"
        val best = matches.minByOrNull { it.optInt("staOrder", 0) } ?: return "노선 정보 없음"
        return formatArrival(best)
    }

    private fun formatArrival(item: JSONObject): String {
        val flag = item.optString("flag").trim()
        if (flag.isNotEmpty() && listOf("종료", "출발대기", "회차").any { flag.contains(it) }) {
            return flag
        }
        val seconds = when (val sec = item.opt("predictTimeSec1")) {
            is Number -> sec.toInt()
            is String -> sec.toIntOrNull() ?: 0
            else -> 0
        }
        if (seconds <= 0) return "도착 정보 없음"
        val minutes = ceil(seconds / 60.0).toInt()
        return if (minutes <= 0) "곧 도착" else "${minutes}분 후 도착예정"
    }
}
