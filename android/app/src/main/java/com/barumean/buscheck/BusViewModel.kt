package com.barumean.buscheck

import android.app.Application
import android.content.Context
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class BusViewModel(app: Application) : AndroidViewModel(app) {
    private val prefs = app.getSharedPreferences("buscheck", Context.MODE_PRIVATE)

    /** 사용 중인 서비스 키. 저장된 값이 있으면 그것을, 없으면 빌드에 주입된 값을 쓴다. */
    var serviceKey by mutableStateOf(loadKey())
        private set

    var results by mutableStateOf<List<BusResult>>(emptyList())
        private set
    var loading by mutableStateOf(false)
        private set
    var lastUpdated by mutableStateOf<String?>(null)
        private set

    private fun loadKey(): String {
        val saved = prefs.getString("service_key", null)
        if (!saved.isNullOrBlank()) return saved
        return BuildConfig.BUS_SERVICE_KEY
    }

    fun hasKey(): Boolean = serviceKey.isNotBlank()

    fun saveKey(key: String) {
        val trimmed = key.trim()
        prefs.edit().putString("service_key", trimmed).apply()
        serviceKey = trimmed
        refresh()
    }

    fun refresh() {
        if (!hasKey() || loading) return
        viewModelScope.launch {
            loading = true
            val loaded = BUS_LIST.sortedBy { it.order }.map { cfg ->
                async {
                    val arrival = BusRepository.getArrival(serviceKey, cfg.stationId, cfg.routeName)
                    BusResult(cfg, arrival, isError = isErrorText(arrival))
                }
            }.awaitAll()
            results = loaded
            lastUpdated = SimpleDateFormat("HH:mm:ss", Locale.KOREA).format(Date())
            loading = false
        }
    }

    private fun isErrorText(text: String): Boolean =
        text.contains("실패") || text.contains("오류") || text.contains("없음")
}
