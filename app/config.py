"""환경 설정 및 상수"""
import os

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# API 키 / 외부 서비스
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
POLYGON_API_KEY = os.environ.get("POLYGON_API_KEY", "")

# Discord 알림 (선택)
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")
DISCORD_MIN_GRADE = os.environ.get("DISCORD_MIN_GRADE", "HIGH")  # HIGH/IMMINENT만

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 데이터 필터링
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MIN_PRICE = 0.05
MIN_VOLUME = 50_000
MIN_AVG_VOLUME = 50_000

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 알림 / 히스토리
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ALERT_COOLDOWN_SEC = 1800   # 30분
HISTORY_MAX = 1000          # ~8시간치

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# WebSocket
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WS_ENABLED = os.environ.get("WS_ENABLED", "true").lower() == "true"
WS_TOP_N = 500  # 실시간 스트리밍할 상위 종목 수 (Starter 플랜 제한 고려)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 점수 재계산 우선순위
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RESCORE_TOP_INTERVAL = 30     # 상위 500개: 30초마다
RESCORE_MID_INTERVAL = 300    # 501~2000위: 5분마다
RESCORE_LOW_INTERVAL = 1800   # 그 외: 30분마다
RESCORE_TOP_N = 500
RESCORE_MID_N = 2000

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 이상 거래 탐지
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ANOMALY_VOL_ZSCORE = 3.0   # Z-score 3 이상 = 99.7% 신뢰구간 벗어남
ANOMALY_PRICE_ZSCORE = 2.5
ANOMALY_MIN_HISTORY_DAYS = 20

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 카탈리스트 키워드
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CATALYST_KEYWORDS = [
    "earnings", "fda", "approval", "merger", "acquisition", "buyout",
    "squeeze", "short", "contract", "partnership", "upgrade", "beat",
    "clinical", "trial", "phase", "catalyst", "announcement", "guidance",
    "activist", "coverage", "recall", "investigation", "lawsuit", "license",
    "offering", "dilution", "split", "spinoff",
]

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 상장폐지/제외 종목
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DELISTED = {"UVXY", "BBBY", "SIVB", "FRC", "SI", "SBNY"}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 섹터 한글
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTOR_KR = {
    "Technology": "기술", "Financial Services": "금융", "Healthcare": "헬스케어",
    "Consumer Cyclical": "소비재", "Communication Services": "커뮤니케이션",
    "Energy": "에너지", "Industrials": "산업", "Basic Materials": "소재",
    "Real Estate": "부동산", "Consumer Defensive": "필수소비재", "Utilities": "유틸리티",
}
