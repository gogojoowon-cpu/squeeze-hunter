"""Polygon/Massive API 클라이언트 — 옵션/펀더멘털/이벤트 확장"""
import time, requests, urllib.parse as up
from datetime import date, datetime, timedelta, timezone
from app.config import POLYGON_API_KEY
from app import state

BASE = "https://api.polygon.io"

# 세션 재사용 (Keep-Alive)
_session = requests.Session()
_session.headers.update({"User-Agent": "ShortSqueezeHunter/4.0"})


def _key_ok() -> bool:
    return bool(POLYGON_API_KEY)


def _api_call(url: str, params: dict, timeout: int = 15):
    """API 호출 + 메트릭 추적"""
    state.metrics["polygon_api_calls"] += 1
    try:
        r = _session.get(url, params=params, timeout=timeout)
        if r.status_code != 200:
            state.metrics["polygon_api_errors"] += 1
        return r
    except Exception:
        state.metrics["polygon_api_errors"] += 1
        raise


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 티커 목록
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def fetch_all_tickers() -> list[dict]:
    """전체 미국 상장 종목 (NASDAQ + NYSE)"""
    if not _key_ok():
        print("❌ POLYGON_API_KEY 미설정")
        return []

    out = []
    seen = set()
    for exchange in ["XNAS", "XNYS"]:
        print(f"  📋 {exchange} 수집 중...")
        cursor = None
        while True:
            try:
                params = {
                    "market": "stocks", "exchange": exchange,
                    "active": "true", "limit": 1000,
                    "apiKey": POLYGON_API_KEY,
                }
                if cursor:
                    params["cursor"] = cursor

                r = _api_call(f"{BASE}/v3/reference/tickers", params, timeout=30)
                if r.status_code != 200:
                    print(f"    ⚠️ {exchange} {r.status_code}: {r.text[:150]}")
                    break

                data = r.json()
                results = data.get("results", [])
                if not results:
                    break

                for item in results:
                    sym = item.get("ticker", "")
                    name = item.get("name", "")
                    t = item.get("type", "")
                    if (sym and sym not in seen and sym.isalpha()
                            and 1 <= len(sym) <= 5
                            and t not in ("WARRANT", "RIGHT", "UNIT", "SP",
                                          "ETF", "ETV", "ETN")
                            and "WARRANT" not in name.upper()
                            and "PREFERRED" not in name.upper()):
                        out.append({
                            "symbol": sym, "name": name,
                            "sic": int(item.get("sic_code", 0) or 0),
                        })
                        seen.add(sym)

                next_url = data.get("next_url", "")
                if not next_url:
                    break
                cursor = dict(up.parse_qsl(up.urlparse(next_url).query)).get("cursor", "")
                if not cursor:
                    break
                time.sleep(0.4)
            except Exception as e:
                print(f"    ⚠️ {exchange} 예외: {e}")
                break
        print(f"  ✅ {exchange} 누적 {len(out)}개")
        time.sleep(1)

    print(f"✅ 전체 티커: {len(out)}개")
    return out


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 가격 데이터
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def fetch_grouped_daily() -> dict:
    """grouped daily — 가장 최근 거래일 전체 종목 OHLCV"""
    if not _key_ok():
        return {}
    out = {}
    for days_back in range(1, 6):
        try_date = (date.today() - timedelta(days=days_back)).strftime("%Y-%m-%d")
        try:
            r = _api_call(
                f"{BASE}/v2/aggs/grouped/locale/us/market/stocks/{try_date}",
                params={"adjusted": "true", "apiKey": POLYGON_API_KEY},
                timeout=30,
            )
            if r.status_code != 200:
                continue
            results = r.json().get("results", [])
            if not results:
                continue
            for res in results:
                sym = res.get("T", "")
                if not sym:
                    continue
                price = float(res.get("c", 0))
                if price <= 0:
                    continue
                prev_o = float(res.get("o", price))
                out[sym] = {
                    "price": round(price, 2),
                    "volume": int(res.get("v", 0) or 0),
                    "change_pct": round((price - prev_o) / max(prev_o, 0.01) * 100, 2),
                    "high": float(res.get("h", price)),
                    "low": float(res.get("l", price)),
                }
            print(f"  📡 grouped {try_date}: {len(out)}개")
            break
        except Exception as e:
            print(f"  ⚠️ grouped {try_date}: {e}")
    return out


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 일봉 90일 + 매집 지표 + 이상거래
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def fetch_aggs(sym: str) -> dict:
    """90일 OHLCV → RSI/52주/매집/이상거래 (1시간 캐시)"""
    if not _key_ok():
        return {}
    cached = state.aggs_cache.get(sym)
    if cached and time.time() - cached.get("_ts", 0) < 3600:
        return cached

    try:
        end_dt = date.today()
        for _ in range(5):
            if end_dt.weekday() < 5:
                break
            end_dt -= timedelta(days=1)
        end = end_dt.strftime("%Y-%m-%d")
        start = (end_dt - timedelta(days=90)).strftime("%Y-%m-%d")

        r = _api_call(
            f"{BASE}/v2/aggs/ticker/{sym}/range/1/day/{start}/{end}",
            params={"adjusted": "true", "sort": "asc", "limit": 90,
                    "apiKey": POLYGON_API_KEY},
            timeout=10,
        )
        if r.status_code != 200:
            return {}
        results = r.json().get("results", [])
        if len(results) < 20:
            return {}

        closes = [x["c"] for x in results]
        opens = [x["o"] for x in results]
        vols = [x["v"] for x in results]
        highs = [x["h"] for x in results]
        lows = [x["l"] for x in results]

        rsi_v = _calc_rsi(closes)
        avg_vol_20 = sum(vols[-20:]) / max(len(vols[-20:]), 1)
        avg_vol_50 = sum(vols[-50:]) / max(len(vols[-50:]), 1) if len(vols) >= 50 else avg_vol_20
        h52, l52, cur = max(highs), min(lows), closes[-1]

        # 매집 지표
        accumulation = _calc_accumulation(opens, closes, highs, lows, vols)

        # 🆕 이상 거래 Z-score
        anomaly = _calc_anomaly(closes, vols)

        result = {
            "rsi14": rsi_v,
            "avg_vol": avg_vol_20,
            "avg_vol_50": avg_vol_50,
            "high_52w": round(h52, 2),
            "low_52w": round(l52, 2),
            "dist_52w": round((h52 - cur) / max(h52, 1), 3),
            "vol_spike": round(vols[-1] / max(avg_vol_20, 1), 3),
            **accumulation,
            **anomaly,
            "_ts": time.time(),
        }
        state.aggs_cache[sym] = result
        return result
    except Exception:
        return {}


def _calc_rsi(closes: list[float]) -> float:
    if len(closes) < 15:
        return 50.0
    gains, losses = [], []
    for i in range(1, len(closes)):
        d = closes[i] - closes[i-1]
        gains.append(max(d, 0))
        losses.append(max(-d, 0))
    g = sum(gains[-14:]) / 14
    l = sum(losses[-14:]) / 14
    if l == 0:
        return 100.0
    rs = g / l
    return round(100 - 100 / (1 + rs), 1)


def _calc_anomaly(closes: list[float], vols: list[float]) -> dict:
    """🆕 Z-score 기반 이상 거래 탐지"""
    n = len(vols)
    if n < 20:
        return {"vol_zscore": 0, "price_zscore": 0, "anomaly_signals": []}

    # 거래량 Z-score (오늘 vs 30일)
    hist_vols = vols[-30:-1] if n >= 30 else vols[:-1]
    mean_v = sum(hist_vols) / len(hist_vols)
    var_v = sum((v - mean_v) ** 2 for v in hist_vols) / len(hist_vols)
    std_v = var_v ** 0.5
    today_vol = vols[-1]
    vol_z = (today_vol - mean_v) / max(std_v, 1)

    # 가격 변화 Z-score
    price_changes = [
        (closes[i] - closes[i-1]) / max(closes[i-1], 0.01)
        for i in range(1, len(closes))
    ]
    hist_changes = price_changes[-30:-1] if len(price_changes) >= 30 else price_changes[:-1]
    if hist_changes:
        mean_c = sum(hist_changes) / len(hist_changes)
        var_c = sum((c - mean_c) ** 2 for c in hist_changes) / len(hist_changes)
        std_c = var_c ** 0.5
        today_change = price_changes[-1]
        price_z = (today_change - mean_c) / max(std_c, 0.001)
    else:
        price_z = 0

    signals = []
    if vol_z >= 4:
        signals.append(f"거래량 극단{vol_z:.1f}σ")
    elif vol_z >= 3:
        signals.append(f"거래량 이상{vol_z:.1f}σ")
    if abs(price_z) >= 3:
        signals.append(f"가격 이상{price_z:+.1f}σ")

    return {
        "vol_zscore": round(vol_z, 2),
        "price_zscore": round(price_z, 2),
        "anomaly_signals": signals,
    }


def _calc_accumulation(opens, closes, highs, lows, vols) -> dict:
    """Wyckoff + OBV + CMF 매집 신호 (0~100점)"""
    n = len(closes)
    if n < 20:
        return {"acc_score": 0, "acc_signals": []}

    # OBV
    obv = [0]
    for i in range(1, n):
        if closes[i] > closes[i-1]:
            obv.append(obv[-1] + vols[i])
        elif closes[i] < closes[i-1]:
            obv.append(obv[-1] - vols[i])
        else:
            obv.append(obv[-1])
    obv_recent = obv[-20:]
    obv_slope = (obv_recent[-1] - obv_recent[0]) / (abs(obv_recent[0]) + 1)

    # CMF
    mfv_sum, vol_sum = 0.0, 0.0
    for i in range(max(n-20, 0), n):
        hl = highs[i] - lows[i]
        mfm = 0 if hl == 0 else ((closes[i] - lows[i]) - (highs[i] - closes[i])) / hl
        mfv_sum += mfm * vols[i]
        vol_sum += vols[i]
    cmf = mfv_sum / max(vol_sum, 1)

    # 거래량 폭증일
    avg_base = sum(vols[-30:-10]) / 20 if n >= 30 else sum(vols[:max(n-10, 1)]) / max(n-10, 1)
    vol_spike_days = sum(1 for v in vols[-10:] if v >= avg_base * 2.0)

    # ATR
    atr_sum, atr_cnt = 0.0, 0
    for i in range(max(n-10, 1), n):
        tr = max(highs[i] - lows[i],
                 abs(highs[i] - closes[i-1]),
                 abs(lows[i] - closes[i-1]))
        atr_sum += tr
        atr_cnt += 1
    atr = atr_sum / max(atr_cnt, 1)
    price_stability = atr / max(closes[-1], 0.01)

    # Wyckoff Spring
    near_support, spring_recovery = False, False
    if n >= 60:
        low_60 = min(lows[-60:])
        low_20 = min(lows[-20:])
        near_support = (low_20 - low_60) / max(low_60, 0.01) < 0.05
        for i in range(max(n-15, 1), n):
            if lows[i] <= low_60 * 1.03 and closes[i] > lows[i] * 1.02:
                if vols[i] >= avg_base * 2:
                    spring_recovery = True
                    break

    # 매집/분산 캔들
    acc_candles, dist_candles = 0, 0
    for i in range(max(n-20, 0), n):
        if vols[i] >= avg_base * 1.3:
            candle_range = highs[i] - lows[i]
            if candle_range > 0:
                close_position = (closes[i] - lows[i]) / candle_range
                if close_position >= 0.6:
                    acc_candles += 1
                elif close_position <= 0.4:
                    dist_candles += 1
    acc_ratio = acc_candles / max(acc_candles + dist_candles, 1)

    # 점수 산정
    signals = []
    score = 0
    if obv_slope > 0.1:
        score += 25; signals.append(f"OBV+{obv_slope*100:.1f}%")
    elif obv_slope > 0:
        score += 12; signals.append("OBV 약상승")
    if cmf > 0.15:
        score += 20; signals.append(f"CMF강세{cmf:+.2f}")
    elif cmf > 0.05:
        score += 10; signals.append(f"CMF{cmf:+.2f}")
    elif cmf < -0.1:
        score -= 5
    if vol_spike_days >= 5:
        score += 15; signals.append(f"거래량폭증{vol_spike_days}일")
    elif vol_spike_days >= 3:
        score += 8; signals.append(f"거래량증가{vol_spike_days}일")
    if price_stability < 0.03 and vol_spike_days >= 2:
        score += 15; signals.append("횡보+거래량↑")
    elif price_stability < 0.05 and vol_spike_days >= 2:
        score += 8
    if spring_recovery:
        score += 15; signals.append("⚡Spring매집막바지")
    elif near_support and vol_spike_days >= 2:
        score += 8; signals.append("지지선테스트")
    if acc_ratio >= 0.7 and (acc_candles + dist_candles) >= 5:
        score += 10; signals.append(f"매집{acc_candles}:{dist_candles}분산")
    elif acc_ratio >= 0.55 and (acc_candles + dist_candles) >= 5:
        score += 5

    return {
        "acc_score": max(0, min(100, score)),
        "acc_signals": signals,
        "obv_slope": round(obv_slope, 3),
        "cmf": round(cmf, 3),
        "vol_spike_days": vol_spike_days,
        "price_stability": round(price_stability, 4),
        "acc_candles": acc_candles,
        "dist_candles": dist_candles,
        "acc_ratio": round(acc_ratio, 2),
        "near_support": near_support,
        "spring_recovery": spring_recovery,
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 종목 상세
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def fetch_ticker_details(sym: str) -> dict:
    if not _key_ok():
        return {}
    try:
        r = _api_call(f"{BASE}/v3/reference/tickers/{sym}",
                      params={"apiKey": POLYGON_API_KEY}, timeout=10)
        if r.status_code != 200:
            return {}
        d = r.json().get("results", {})
        return {
            "name": d.get("name", sym),
            "market_cap": float(d.get("market_cap", 0) or 0),
            "float_shares": int(d.get("share_class_shares_outstanding", 0) or 0),
            "sector": d.get("sic_description", "기타"),
        }
    except Exception:
        return {}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Short Interest / Short Volume
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def fetch_short_interest_batch() -> dict:
    """
    Short Interest 일괄 수집.
    si_pct는 여기서 계산하지 않음 (float 데이터 필요) → enricher에서 후처리.
    """
    if not _key_ok():
        return {}
    out = {}
    end = date.today().strftime("%Y-%m-%d")
    start = (date.today() - timedelta(days=30)).strftime("%Y-%m-%d")
    try:
        r = _api_call(
            f"{BASE}/stocks/v1/short-interest",
            params={
                "settlement_date.gte": start,
                "settlement_date.lte": end,
                "limit": 50000,
                "sort": "settlement_date.desc",
                "apiKey": POLYGON_API_KEY,
            }, timeout=30,
        )
        if r.status_code != 200:
            print(f"  ⚠️ SI {r.status_code}: {r.text[:200]}")
            return {}
        results = r.json().get("results", [])
        seen = set()
        for res in results:
            sym = res.get("ticker", "")
            if not sym or sym in seen:
                continue
            seen.add(sym)
            si_sh = int(res.get("short_interest", 0) or 0)
            dtc = float(res.get("days_to_cover", 0) or 0)
            avg_v = float(res.get("avg_daily_volume", 1) or 1)
            if si_sh > 0:
                out[sym] = {
                    "si_shares": si_sh,
                    "dtc": round(dtc, 2),
                    "avg_vol_si": avg_v,  # ← 이름 변경 (aggs의 avg_vol과 충돌 방지)
                    # si_pct는 enricher에서 후처리
                }
        print(f"  ✅ Short Interest: {len(out)}개")
    except Exception as e:
        print(f"  ❌ SI 오류: {e}")
    return out



def fetch_short_volume_batch():
    """
    Massive(Polygon) /stocks/v1/short-volume 엔드포인트로 
    전 종목 숏볼륨 + 다크풀 데이터 일괄 수집.
    
    Returns:
        dict: { "AAPL": {
                  "short_volume": int,
                  "total_volume": int,
                  "short_volume_ratio": float (0~1),
                  "dark_pool_ratio": float (0~1),
                  "date": "YYYY-MM-DD"
                }, ... }
    """
    from app.config import POLYGON_API_KEY
    import requests
    
    url = "https://api.polygon.io/stocks/v1/short-volume"
    result = {}
    
    # 가장 최근 거래일 데이터 (date 파라미터 생략 시 최신)
    params = {
        "limit": 50000,
        "sort": "ticker.asc",
        "apiKey": POLYGON_API_KEY,
    }
    
    page_count = 0
    max_pages = 5  # 최대 5페이지 (25만건)
    next_url = url
    
    try:
        while next_url and page_count < max_pages:
            if page_count == 0:
                resp = requests.get(next_url, params=params, timeout=30)
            else:
                # next_url에는 cursor가 이미 포함되어 있음
                sep = "&" if "?" in next_url else "?"
                resp = requests.get(
                    f"{next_url}{sep}apiKey={POLYGON_API_KEY}",
                    timeout=30
                )
            
            if resp.status_code != 200:
                print(f"⚠️ Short Volume HTTP {resp.status_code}: {resp.text[:200]}")
                break
            
            data = resp.json()
            results = data.get("results", [])
            
            if not results:
                break
            
            for r in results:
                ticker = r.get("ticker")
                if not ticker:
                    continue
                
                short_vol = r.get("short_volume", 0) or 0
                total_vol = r.get("total_volume", 0) or 0
                sv_ratio = r.get("short_volume_ratio", 0) or 0
                
                # short_volume_ratio가 퍼센트(0~100)면 0~1로 변환
                if sv_ratio > 1:
                    sv_ratio = sv_ratio / 100.0
                
                # 다크풀 추정: ADF (FINRA Alternative Display Facility) 
                # + Nasdaq Carteret/Chicago 비공개 거래소 데이터
                adf = r.get("adf_short_volume", 0) or 0
                nas_carteret = r.get("nasdaq_carteret_short_volume", 0) or 0
                nas_chicago = r.get("nasdaq_chicago_short_volume", 0) or 0
                
                dark_short = adf + nas_carteret + nas_chicago
                dark_pool_ratio = (dark_short / short_vol) if short_vol > 0 else 0.0
                # 0~1 클램프
                if dark_pool_ratio > 1:
                    dark_pool_ratio = 1.0
                
                result[ticker] = {
                    "short_volume": short_vol,
                    "total_volume": total_vol,
                    "short_volume_ratio": sv_ratio,
                    "dark_pool_ratio": dark_pool_ratio,
                    "date": r.get("date", ""),
                }
            
            # 다음 페이지
            next_url = data.get("next_url")
            page_count += 1
        
        print(f"✅ Short Volume: {len(result)}개 (페이지 {page_count})")
        return result
    
    except Exception as e:
        print(f"❌ fetch_short_volume_batch 실패: {e}")
        return result




# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Float
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def fetch_float_batch() -> dict:
    """Float 일괄 수집 - scoring.py가 읽는 'float_shares' 키로 통일"""
    if not _key_ok():
        return {}
    out = {}
    cursor = None
    while True:
        try:
            params = {"limit": 5000, "sort": "ticker.asc", "apiKey": POLYGON_API_KEY}
            if cursor:
                params["cursor"] = cursor
            r = _api_call(f"{BASE}/stocks/vX/float", params, timeout=30)
            if r.status_code != 200:
                break
            data = r.json()
            results = data.get("results", [])
            if not results:
                break
            for res in results:
                sym = res.get("ticker", "")
                ff = int(res.get("free_float", 0) or 0)
                ffp = float(res.get("free_float_percent", 0) or 0)
                if sym and ff > 0:
                    out[sym] = {
                        "float_shares": ff,        # ← scoring.py 기대 키
                        "free_float": ff,           # 호환용
                        "free_float_pct": round(ffp, 2),
                    }
            next_url = data.get("next_url", "")
            if not next_url:
                break
            cursor = dict(up.parse_qsl(up.urlparse(next_url).query)).get("cursor", "")
            if not cursor:
                break
            time.sleep(0.3)
        except Exception as e:
            print(f"  ❌ Float: {e}")
            break
    print(f"  ✅ Float: {len(out)}개")
    return out



# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 기술 지표 (MACD)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def fetch_macd(sym: str) -> dict:
    """MACD - scoring.py가 읽는 'macd_*' prefix 키로 통일"""
    if not _key_ok():
        return {}
    try:
        r = _api_call(
            f"{BASE}/v1/indicators/macd/{sym}",
            params={"timespan": "day", "adjusted": "true",
                    "short_window": 12, "long_window": 26, "signal_window": 9,
                    "series_type": "close", "order": "desc", "limit": 2,
                    "apiKey": POLYGON_API_KEY},
            timeout=8,
        )
        if r.status_code != 200:
            return {}
        values = r.json().get("results", {}).get("values", [])
        if not values:
            return {}
        cur = values[0]
        prev = values[1] if len(values) > 1 else {}
        hist_v = float(cur.get("histogram", 0) or 0)
        prev_h = float(prev.get("histogram", 0) or 0)
        return {
            # ✅ scoring.py 기대 키로 통일
            "macd_value": round(float(cur.get("value", 0) or 0), 4),
            "macd_signal": round(float(cur.get("signal", 0) or 0), 4),
            "macd_histogram": round(hist_v, 4),
            "macd_golden_cross": hist_v > 0 and prev_h <= 0,
            "macd_dead_cross": hist_v < 0 and prev_h >= 0,
        }
    except Exception:
        return {}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🆕 옵션 체인 스냅샷 (감마 집중도 + UOA + C/P Ratio)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def fetch_options_chain(sym):
    """
    종목별 옵션 체인 수집 + 감마/콜풋비율/특이옵션/맥스페인 계산.
    
    Returns:
        dict: {
            "gamma_concentration": float (0~1),
            "call_put_ratio": float,
            "unusual_options_score": float (0~100),
            "max_pain": float,
            "total_call_oi": int,
            "total_put_oi": int,
            "total_call_volume": int,
            "total_put_volume": int,
            "avg_iv": float,
            "contract_count": int,
            "timestamp": float
        }
    """
    from app.config import POLYGON_API_KEY
    import requests
    import time as _time
    
    url = f"https://api.polygon.io/v3/snapshot/options/{sym}"
    params = {
        "limit": 250,
        "apiKey": POLYGON_API_KEY,
    }
    
    contracts = []
    page_count = 0
    max_pages = 4  # 최대 4페이지 (1000건)
    next_url = url
    
    try:
        while next_url and page_count < max_pages:
            if page_count == 0:
                resp = requests.get(next_url, params=params, timeout=20)
            else:
                sep = "&" if "?" in next_url else "?"
                resp = requests.get(
                    f"{next_url}{sep}apiKey={POLYGON_API_KEY}",
                    timeout=20
                )
            
            if resp.status_code != 200:
                if resp.status_code == 404:
                    return {}  # 옵션 없는 종목
                print(f"⚠️ Options {sym} HTTP {resp.status_code}")
                break
            
            data = resp.json()
            results = data.get("results", [])
            
            if not results:
                break
            
            contracts.extend(results)
            
            next_url = data.get("next_url")
            page_count += 1
        
        if not contracts:
            return {}
        
        # 현재가 추출 (첫 컨트랙트의 underlying_asset.price)
        underlying_price = 0
        for c in contracts:
            ua = c.get("underlying_asset", {}) or {}
            p = ua.get("price", 0) or 0
            if p > 0:
                underlying_price = p
                break
        
        total_call_oi = 0
        total_put_oi = 0
        total_call_vol = 0
        total_put_vol = 0
        otm_call_oi = 0
        unusual_count = 0
        iv_sum = 0.0
        iv_count = 0
        strike_oi = {}  # for max pain: {strike: {"call": oi, "put": oi}}
        
        for c in contracts:
            details = c.get("details", {}) or {}
            day = c.get("day", {}) or {}
            oi = c.get("open_interest", 0) or 0
            vol = day.get("volume", 0) or 0
            iv = c.get("implied_volatility", 0) or 0
            
            ctype = details.get("contract_type", "")  # "call" or "put"
            strike = details.get("strike_price", 0) or 0
            
            if iv > 0:
                iv_sum += iv
                iv_count += 1
            
            # 특이 옵션: 거래량 > 2*OI 그리고 거래량 > 100
            if oi > 0 and vol > 2 * oi and vol > 100:
                unusual_count += 1
            
            # strike별 OI 집계 (max pain용)
            if strike > 0:
                if strike not in strike_oi:
                    strike_oi[strike] = {"call": 0, "put": 0}
                
                if ctype == "call":
                    total_call_oi += oi
                    total_call_vol += vol
                    strike_oi[strike]["call"] += oi
                    # OTM call: strike > 현재가
                    if underlying_price > 0 and strike > underlying_price:
                        otm_call_oi += oi
                
                elif ctype == "put":
                    total_put_oi += oi
                    total_put_vol += vol
                    strike_oi[strike]["put"] += oi
        
        # 감마 집중도: OTM 콜 OI / 전체 콜 OI
        gamma_conc = (otm_call_oi / total_call_oi) if total_call_oi > 0 else 0.0
        
        # 콜풋 비율 (거래량 기준)
        cp_ratio = (total_call_vol / total_put_vol) if total_put_vol > 0 else 0.0
        
        # 특이 옵션 점수 (컨트랙트 대비 비율 → 0~100)
        uo_score = (unusual_count / len(contracts) * 1000) if contracts else 0
        uo_score = min(uo_score, 100)
        
        # Max Pain
        max_pain = _calc_max_pain(strike_oi)
        
        # 평균 IV
        avg_iv = (iv_sum / iv_count) if iv_count > 0 else 0
        
        return {
            "gamma_concentration": round(gamma_conc, 4),
            "call_put_ratio": round(cp_ratio, 3),
            "unusual_options_score": round(uo_score, 1),
            "max_pain": round(max_pain, 2),
            "total_call_oi": total_call_oi,
            "total_put_oi": total_put_oi,
            "total_call_volume": total_call_vol,
            "total_put_volume": total_put_vol,
            "avg_iv": round(avg_iv, 4),
            "contract_count": len(contracts),
            "timestamp": _time.time(),
        }
    
    except Exception as e:
        print(f"❌ fetch_options_chain({sym}) 실패: {e}")
        return {}


def _calc_max_pain(strike_oi):
    """Max Pain: 옵션 매수자가 가장 큰 손실을 보는 가격"""
    if not strike_oi:
        return 0
    
    strikes = sorted(strike_oi.keys())
    min_pain = float("inf")
    max_pain_strike = 0
    
    for test_strike in strikes:
        pain = 0
        for s, oi in strike_oi.items():
            # 콜 손실: 행사가 < 테스트 가격일 때
            if test_strike > s:
                pain += (test_strike - s) * oi["call"]
            # 풋 손실: 행사가 > 테스트 가격일 때
            if test_strike < s:
                pain += (s - test_strike) * oi["put"]
        
        if pain < min_pain:
            min_pain = pain
            max_pain_strike = test_strike
    
    return max_pain_strike
    


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🆕 펀더멘털 (재무제표)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def fetch_fundamentals(sym: str) -> dict:
    """재무제표 → 부채/자본, 현금소진율 (1일 캐시)"""
    if not _key_ok():
        return {}
    cached = state.fundamentals_cache.get(sym)
    if cached and time.time() - cached.get("_ts", 0) < 86400:
        return cached

    try:
        r = _api_call(
            f"{BASE}/vX/reference/financials",
            params={"ticker": sym, "limit": 4, "timeframe": "quarterly",
                    "apiKey": POLYGON_API_KEY},
            timeout=15,
        )
        if r.status_code != 200:
            return {}

        results = r.json().get("results", [])
        if not results:
            return {}

        latest = results[0].get("financials", {})
        balance = latest.get("balance_sheet", {})
        income = latest.get("income_statement", {})
        cash_flow = latest.get("cash_flow_statement", {})

        # 부채/자본 비율
        total_liab = float(balance.get("liabilities", {}).get("value", 0) or 0)
        total_eq = float(balance.get("equity", {}).get("value", 1) or 1)
        debt_to_equity = total_liab / max(abs(total_eq), 1)

        # 현금 소진율 (분기 영업 현금흐름)
        op_cash = float(cash_flow.get("net_cash_flow_from_operating_activities", {}).get("value", 0) or 0)
        current_cash = float(balance.get("current_assets", {}).get("value", 0) or 0)
        # 현금 소진율 (개월 단위, 부정적일 때만 의미)
        if op_cash < 0:
            months_burn = current_cash / (abs(op_cash) / 3)
            cash_runway = round(months_burn, 1)
        else:
            cash_runway = 999

        # 매출 성장
        revenues = float(income.get("revenues", {}).get("value", 0) or 0)
        prev_revenues = 0
        if len(results) >= 5:
            prev = results[4].get("financials", {}).get("income_statement", {})
            prev_revenues = float(prev.get("revenues", {}).get("value", 0) or 0)
        rev_growth_yoy = ((revenues - prev_revenues) / max(prev_revenues, 1)) * 100 if prev_revenues > 0 else 0

        result = {
            "debt_to_equity": round(debt_to_equity, 2),
            "cash_runway_months": cash_runway,
            "revenue_growth_yoy": round(rev_growth_yoy, 1),
            "revenues": revenues,
            "_ts": time.time(),
        }
        state.fundamentals_cache[sym] = result
        return result
    except Exception:
        return {}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🆕 기업 이벤트 (어닝/배당/분할)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def fetch_upcoming_dividends() -> dict:
    """다가오는 배당 일정"""
    if not _key_ok():
        return {}
    out = {}
    today = date.today().strftime("%Y-%m-%d")
    future = (date.today() + timedelta(days=60)).strftime("%Y-%m-%d")
    try:
        r = _api_call(
            f"{BASE}/v3/reference/dividends",
            params={"ex_dividend_date.gte": today,
                    "ex_dividend_date.lte": future,
                    "limit": 1000, "apiKey": POLYGON_API_KEY},
            timeout=20,
        )
        if r.status_code != 200:
            return {}
        for res in r.json().get("results", []):
            sym = res.get("ticker", "")
            ex_date = res.get("ex_dividend_date", "")
            cash = float(res.get("cash_amount", 0) or 0)
            if sym and ex_date:
                d_obj = datetime.strptime(ex_date, "%Y-%m-%d").date()
                days_until = (d_obj - date.today()).days
                if sym not in out or days_until < out[sym].get("days_until_ex_div", 999):
                    out[sym] = {
                        "ex_dividend_date": ex_date,
                        "days_until_ex_div": days_until,
                        "dividend_amount": cash,
                    }
        print(f"  ✅ 배당 일정: {len(out)}개")
    except Exception as e:
        print(f"  ❌ 배당: {e}")
    return out


def fetch_upcoming_splits() -> dict:
    """다가오는 주식 분할"""
    if not _key_ok():
        return {}
    out = {}
    today = date.today().strftime("%Y-%m-%d")
    future = (date.today() + timedelta(days=60)).strftime("%Y-%m-%d")
    try:
        r = _api_call(
            f"{BASE}/v3/reference/splits",
            params={"execution_date.gte": today,
                    "execution_date.lte": future,
                    "limit": 500, "apiKey": POLYGON_API_KEY},
            timeout=15,
        )
        if r.status_code != 200:
            return {}
        for res in r.json().get("results", []):
            sym = res.get("ticker", "")
            exec_date = res.get("execution_date", "")
            split_from = float(res.get("split_from", 1) or 1)
            split_to = float(res.get("split_to", 1) or 1)
            if sym and exec_date:
                d_obj = datetime.strptime(exec_date, "%Y-%m-%d").date()
                days_until = (d_obj - date.today()).days
                out[sym] = {
                    "split_date": exec_date,
                    "days_until_split": days_until,
                    "split_ratio": f"{split_to:.0f}:{split_from:.0f}",
                }
        print(f"  ✅ 분할 일정: {len(out)}개")
    except Exception as e:
        print(f"  ❌ 분할: {e}")
    return out


def fetch_earnings_estimate(sym: str) -> dict:
    """🆕 어닝 예상일 (ticker events 이용)"""
    if not _key_ok():
        return {}
    try:
        r = _api_call(
            f"{BASE}/vX/reference/tickers/{sym}/events",
            params={"types": "ticker_change", "apiKey": POLYGON_API_KEY},
            timeout=10,
        )
        # Polygon이 직접 어닝일을 안 줘서 — 보통 분기마다 정기 발표
        # 마지막 분기 종료일 + 30~45일 추정
        last_quarter_end = state.fundamentals_cache.get(sym, {}).get("_quarter_end", "")
        # 단순화: 다음 어닝까지 30일이라고 가정 (실제론 Yahoo Finance나 EOD 사용 권장)
        return {"days_to_earnings": 999}  # 향후 확장
    except Exception:
        return {"days_to_earnings": 999}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 뉴스
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def fetch_news_batch(limit: int = 1000) -> dict:
    """뉴스 - scoring.py가 읽는 'sentiment' 키로 통일"""
    from app.config import CATALYST_KEYWORDS
    if not _key_ok():
        return {}
    out = {}
    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        r = _api_call(
            f"{BASE}/v2/reference/news",
            params={"published_utc.gte": cutoff, "order": "desc",
                    "sort": "published_utc", "limit": limit, "apiKey": POLYGON_API_KEY},
            timeout=20,
        )
        if r.status_code != 200:
            print(f"  ⚠️ 뉴스 {r.status_code}")
            return {}
        results = r.json().get("results", [])
        for article in results:
            title = (article.get("title", "") or "").lower()
            tickers = article.get("tickers", []) or []
            insights = article.get("insights", []) or []
            is_cat = any(kw in title for kw in CATALYST_KEYWORDS)
            sent_map = {ins.get("ticker", ""): ins.get("sentiment", "neutral")
                        for ins in insights if ins.get("ticker")}
            for sym in tickers:
                if not sym:
                    continue
                if sym not in out:
                    out[sym] = {"has_catalyst": False, "news_titles": [],
                                "pos": 0, "neg": 0, "news_count": 0}
                out[sym]["news_count"] += 1
                out[sym]["news_titles"].append(article.get("title", "")[:80])
                if is_cat:
                    out[sym]["has_catalyst"] = True
                sent = sent_map.get(sym, "neutral")
                if sent == "positive":
                    out[sym]["pos"] += 1
                elif sent == "negative":
                    out[sym]["neg"] += 1
        for sym in out:
            n = out[sym]["news_count"]
            # ✅ 'sentiment' 키로 (scoring.py가 기대하는 이름)
            out[sym]["sentiment"] = round((out[sym]["pos"] - out[sym]["neg"]) / max(n, 1), 2)
            out[sym]["sentiment_score"] = out[sym]["sentiment"]  # 호환용
        print(f"  ✅ 뉴스: {len(out)}개 종목")
    except Exception as e:
        print(f"  ❌ 뉴스 오류: {e}")
    return out

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 실시간 스냅샷
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def fetch_snapshots(syms: list[str]) -> dict:
    if not _key_ok() or not syms:
        return {}
    out = {}
    for i in range(0, len(syms), 100):
        batch = syms[i:i+100]
        try:
            r = _api_call(
                f"{BASE}/v3/snapshot",
                params={"ticker.any_of": ",".join(batch), "apiKey": POLYGON_API_KEY},
                timeout=15,
            )
            if r.status_code != 200:
                continue
            for item in r.json().get("results", []):
                sym = item.get("ticker", "")
                session = item.get("session", {})
                p = float(session.get("close", 0) or 0)
                if p > 0 and sym:
                    out[sym] = {
                        "price": round(p, 2),
                        "volume": int(session.get("volume", 0) or 0),
                        "change_pct": float(session.get("change_percent", 0) or 0),
                    }
        except Exception:
            pass
    return out
