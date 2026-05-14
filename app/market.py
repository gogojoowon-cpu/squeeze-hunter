"""
미국 시장 시간 판정
- 정규장: 09:30 ~ 16:00 ET (월~금)
- 프리장: 04:00 ~ 09:30 ET
- 애프터: 16:00 ~ 20:00 ET
"""
from datetime import datetime, timezone, timedelta


def _nth_weekday(year, month, weekday, n):
    d = datetime(year, month, 1)
    days_ahead = (weekday - d.weekday()) % 7
    d += timedelta(days=days_ahead + 7 * (n - 1))
    return d


def _now_et():
    utc = datetime.now(timezone.utc)
    year = utc.year
    dst_start = _nth_weekday(year, 3, 6, 2)   # 3월 둘째 일요일
    dst_end = _nth_weekday(year, 11, 6, 1)    # 11월 첫째 일요일
    is_dst = dst_start <= utc.replace(tzinfo=None) < dst_end
    offset = -4 if is_dst else -5
    return utc + timedelta(hours=offset)


def get_market_session():
    """'pre' | 'regular' | 'after' | 'closed'"""
    et = _now_et()
    if et.weekday() >= 5:
        return "closed"
    m = et.hour * 60 + et.minute
    if 240 <= m < 570:    return "pre"        # 04:00 ~ 09:30
    if 570 <= m < 960:    return "regular"    # 09:30 ~ 16:00
    if 960 <= m < 1200:   return "after"      # 16:00 ~ 20:00
    return "closed"


def is_market_open():
    return get_market_session() == "regular"


def is_market_active():
    return get_market_session() in ("pre", "regular", "after")


def session_label_kr():
    return {
        "pre":     "🌅 프리장",
        "regular": "🟢 정규장",
        "after":   "🌆 애프터",
        "closed":  "🔴 마감",
    }.get(get_market_session(), "❓")
