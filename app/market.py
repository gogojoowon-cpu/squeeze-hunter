"""미국장 개장/폐장 판단"""
from datetime import datetime

try:
    from zoneinfo import ZoneInfo
    ET_TZ = ZoneInfo("America/New_York")
except ImportError:
    ET_TZ = None


def is_market_open() -> bool:
    if not ET_TZ:
        return True
    now = datetime.now(ET_TZ)
    if now.weekday() >= 5:
        return False
    mo = now.replace(hour=9, minute=30, second=0, microsecond=0)
    mc = now.replace(hour=16, minute=0, second=0, microsecond=0)
    return mo <= now <= mc


def market_status() -> str:
    if not ET_TZ:
        return "🟢 장중"
    now = datetime.now(ET_TZ)
    if now.weekday() >= 5:
        return "주말 휴장"
    h, m = now.hour, now.minute
    if (h == 9 and m >= 30) or (10 <= h <= 15) or (h == 16 and m == 0):
        return f"🟢 장중 {h:02d}:{m:02d} ET"
    if h < 9 or (h == 9 and m < 30):
        return "🟡 프리마켓"
    return "🔴 장 마감"
