"""Apewisdom 소셜 데이터 — NoneType 오류 수정"""
import time, requests

_HDR = {"User-Agent": "Mozilla/5.0 research-tool"}
_CACHE: dict[str, dict] = {}
_LAST_FETCH = 0.0


def _to_int(v, default=0) -> int:
    """안전한 int 변환 — None/문자열/실수 모두 처리"""
    if v is None:
        return default
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return default


def _to_float(v, default=0.0) -> float:
    if v is None:
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def fetch_social() -> dict:
    """Apewisdom 소셜 멘션 데이터 (2분 캐시)"""
    global _LAST_FETCH
    if time.time() - _LAST_FETCH < 120:
        return _CACHE.copy()

    out = {}
    try:
        for pg in range(1, 4):
            r = requests.get(
                f"https://apewisdom.io/api/v1.0/filter/all-stocks/page/{pg}",
                headers=_HDR, timeout=10,
            )
            if r.status_code != 200:
                break
            data = r.json()
            items = data.get("results", [])
            if not items:
                break

            for item in items:
                sym = str(item.get("ticker", "")).upper()
                if not sym:
                    continue

                # ✅ NoneType 오류 수정: 안전한 변환
                m = _to_int(item.get("mentions"), 0)
                p24 = _to_int(item.get("mentions_24h_ago"), 1)
                p24 = max(p24, 1)
                vel = ((m - p24) / p24) * 100
                sent = _to_float(item.get("sentiment"), 0.0)
                sent = max(-1.0, min(1.0, sent))

                out[sym] = {
                    "social_velocity": round(vel, 1),
                    "sentiment": round(sent, 4),
                    "mentions": m,
                    "src": "apewisdom",
                }

            if pg >= data.get("page_count", 1):
                break
            time.sleep(1)

        _CACHE.clear()
        _CACHE.update(out)
        _LAST_FETCH = time.time()
        print(f"  📱 소셜: {len(out)}개")
    except Exception as e:
        print(f"  ⚠️ 소셜 전체 실패: {e}")

    return out
