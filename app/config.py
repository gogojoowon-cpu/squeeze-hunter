"""환경 설정 및 상수"""
import os

POLYGON_API_KEY = os.environ.get("POLYGON_API_KEY", "")

# 데이터 필터링
MIN_PRICE = 0.05
MIN_VOLUME = 50_000
MIN_AVG_VOLUME = 50_000

# 알림
ALERT_COOLDOWN_SEC = 1800  # 30분
HISTORY_MAX = 1000         # ~8시간치

# 카탈리스트 키워드
CATALYST_KEYWORDS = [
    "earnings", "fda", "approval", "merger", "acquisition", "buyout",
    "squeeze", "short", "contract", "partnership", "upgrade", "beat",
    "clinical", "trial", "phase", "catalyst", "announcement", "guidance",
    "activist", "coverage", "recall", "investigation", "lawsuit", "license",
]

# 상장폐지/제외 종목
DELISTED = {"UVXY", "BBBY", "SIVB", "FRC", "SI", "SBNY"}

# 섹터 한글
SECTOR_KR = {
    "Technology": "기술", "Financial Services": "금융", "Healthcare": "헬스케어",
    "Consumer Cyclical": "소비재", "Communication Services": "커뮤니케이션",
    "Energy": "에너지", "Industrials": "산업", "Basic Materials": "소재",
    "Real Estate": "부동산", "Consumer Defensive": "필수소비재", "Utilities": "유틸리티",
}
