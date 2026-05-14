"""전역 상태 (메모리)"""
from typing import Any

# 종목 데이터 {symbol: {...}}
stocks: dict[str, dict] = {}

# 점수 히스토리 {symbol: [{ts, score, grade}, ...]}
history: dict[str, list] = {}

# 알림
alerts: list[dict] = []

# 알림 쿨다운 {symbol: timestamp}
alert_cooldown: dict[str, float] = {}

# 로딩 상태
ready = False
enrich_done = False

# 캐시들
aggs_cache: dict[str, dict] = {}              # 종목별 90일 OHLCV 캐시
options_cache: dict[str, dict] = {}           # 🆕 옵션 체인 캐시
fundamentals_cache: dict[str, dict] = {}      # 🆕 펀더멘털 캐시

# WebSocket 클라이언트 (브라우저)
ws_clients: list[Any] = []

# 🆕 Polygon WebSocket 실시간 가격 (티커별)
ws_prices: dict[str, dict] = {}               # {sym: {price, volume, ts}}
ws_connected: bool = False                    # Polygon WS 연결 상태

# 🆕 이상 거래 감지 결과 {symbol: {vol_zscore, price_zscore, signals}}
anomalies: dict[str, dict] = {}

# 🆕 점수 재계산용 dirty flag {symbol: bool}
dirty_symbols: set[str] = set()

# 🆕 마지막 재계산 시각 {symbol: timestamp}
last_rescore: dict[str, float] = {}

# 🆕 통계
metrics = {
    "polygon_api_calls": 0,
    "polygon_api_errors": 0,
    "ws_messages_received": 0,
    "discord_alerts_sent": 0,
}
