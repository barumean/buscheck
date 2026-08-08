package com.barumean.buscheck

/** 관심 정류소·노선 한 건. config/buses.json 과 동일한 등록 목록을 코드로 옮긴 것. */
data class BusConfig(
    val order: Int,
    val mobileNo: String,
    val stationName: String,
    val routeName: String,
    val stationId: String,
)

/** config/buses.json 과 동일한 등록 목록. 노선을 바꾸려면 여기와 저장소 config 를 함께 수정. */
val BUS_LIST = listOf(
    BusConfig(1, "27109", "인덕원퍼스비엘아파트.동아에코빌", "1-1", "226000059"),
    BusConfig(2, "27101", "두산위브2단지", "12", "226000022"),
    BusConfig(3, "27146", "내손초등학교.인덕원퍼스비엘아파트", "7", "226000142"),
)

/** 한 노선의 조회 결과. */
data class BusResult(
    val config: BusConfig,
    val arrival: String,
    val isError: Boolean = false,
)
