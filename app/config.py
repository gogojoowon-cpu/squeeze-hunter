"""
환경 설정 + 상수
- 환경변수: POLYGON_API_KEY (필수)
- 옵션: WS_ENABLED, MIN_PRICE 등
"""
import os

# ============================================================
# API 키
# ============================================================
POLYGON_API_KEY = os.getenv("POLYGON_API_KEY", "").strip()

# ============================================================
# WebSocket 설정
# ============================================================
WS_ENABLED = os.getenv("WS_ENABLED", "true").lower() in ("true", "1", "yes")
WS_URL = "wss://socket.polygon.io/stocks"
WS_TOP_N = int(os.getenv("WS_TOP_N", "500"))   # WebSocket 구독 상위 N개

# ============================================================
# 필터 설정
# ============================================================
MIN_PRICE = float(os.getenv("MIN_PRICE", "0.5"))      # 최저가
MAX_PRICE = float(os.getenv("MAX_PRICE", "1000"))     # 최고가
MIN_VOLUME = int(os.getenv("MIN_VOLUME", "100000"))   # 최저 거래량

# ============================================================
# 우선순위 큐 (재계산 분배)
# ============================================================
TOP_N_SYMBOLS = 500       # 상위 (5분 주기)
MID_N_SYMBOLS = 2000      # 중위 (30분 주기)
RESCORE_TOP_INTERVAL = 30      # 30초마다 dirty 재계산
RESCORE_MID_INTERVAL = 300     # 5분
RESCORE_LOW_INTERVAL = 1800    # 30분

# ============================================================
# 이상거래 임계값
# ============================================================
ANOMALY_VOL_Z_THRESHOLD = 3.0       # 거래량 Z-score
ANOMALY_PRICE_Z_THRESHOLD = 3.0     # 가격 변동 Z-score

# ============================================================
# 알림 쿨다운 (초)
# ============================================================
ALERT_COOLDOWN_SEC = 3600   # 같은 종목+타입 1시간 내 중복 차단

# ============================================================
# 촉매 키워드 (뉴스 분석용)
# ============================================================
CATALYST_KEYWORDS = [
    # 합병/인수
    "merger", "acquisition", "acquire", "buyout", "takeover",
    # FDA/승인
    "fda approval", "fda clearance", "phase 3", "phase iii",
    "breakthrough", "approved", "trial results", "clinical",
    # 실적/계약
    "earnings beat", "record revenue", "contract", "partnership",
    "deal", "agreement", "wins", "secures",
    # 자본 행동
    "buyback", "dividend increase", "stock split", "spin-off",
    # 숏 관련
    "short squeeze", "short interest", "gamma squeeze",
    # 한국어
    "인수", "합병", "승인", "어닝", "계약", "체결", "수주",
]

# ============================================================
# 상장폐지/제외 심볼
# ============================================================
DELISTED_SYMBOLS = {
    "BBBYQ", "BBBY",   # Bed Bath & Beyond
    # 필요시 추가
}

# ============================================================
# 섹터 한글 매핑
# ============================================================
SECTOR_KR = {
    "Technology":            "기술",
    "Healthcare":            "헬스케어",
    "Financial Services":    "금융",
    "Consumer Cyclical":     "임의소비재",
    "Consumer Defensive":    "필수소비재",
    "Communication Services":"통신",
    "Industrials":           "산업재",
    "Energy":                "에너지",
    "Basic Materials":       "소재",
    "Real Estate":           "부동산",
    "Utilities":             "유틸리티",
}

# ============================================================
# 테마 정의 (간략 — 실제 데이터는 themes.py 가 관리)
# ============================================================
DEFAULT_THEME = "기타"
