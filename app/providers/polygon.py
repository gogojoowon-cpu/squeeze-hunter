"""Polygon/Massive API 클라이언트"""
import time, requests, urllib.parse as up
from datetime import date, timedelta
from app.config import POLYGON_API_KEY
from app import state

BASE = "https://api.polygon.io"


def _key_ok() -> bool:
    return bool(POLYGON_API_KEY)


# ────────── 티커 목록 ──────────
def fetch_all_tickers() -> list[dict]:
    """전체 미국 상장 종목 (NASDAQ + NYSE) — 동적 수집"""
    if not _key_ok():
        print("❌ POLYGON_API_KEY 미설정")
        return []

    out = []
    seen = set()
    # XASE(NYSE American)는 페니스탁 위주 + 타임아웃 잦음 → 제외
    for exchange in ["XNAS", "XNYS"]:
        print(f"  📋 {exchange} 수집 중...")
        cursor = None
        while True:
            try:
                params = {
                    "market": "stocks",
                    "exchange": exchange,
                    "active": "true",
                    "limit": 1000,
                    "apiKey": POLYGON_API_KEY,
                }
                if cursor:
                    params["cursor"] = cursor

                r = requests.get(f"{BASE}/v3/reference/tickers",
                                 params=params, timeout=30)
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


# ────────── 가격 데이터 ──────────
def fetch_grouped_daily() -> dict:
    """grouped daily — 가장 최근 거래일 전체 종목 OHLCV"""
    if not _key_ok():
        return {}
    out = {}
    for days_back in range(1, 6):
        try_date = (date.today() - timedelta(days=days_back)).strftime("%Y-%m-%d")
        try:
            r = requests.get(
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


# ────────── 일봉 90일 + 매집 지표 ──────────
def fetch_aggs(sym: str) -> dict:
    """90일 OHLCV → RSI/52주고저/매집지표 (1시간 캐시)"""
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

        r = requests.get(
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

        # 기본 지표
        rsi_v = _calc_rsi(closes)
        avg_vol_20 = sum(vols[-20:]) / max(len(vols[-20:]), 1)
        avg_vol_50 = sum(vols[-50:]) / max(len(vols[-50:]), 1) if len(vols) >= 50 else avg_vol_20
        h52, l52, cur = max(highs), min(lows), closes[-1]

        # ━━━ 매집 지표 계산 ━━━
        accumulation = _calc_accumulation(opens, closes, highs, lows, vols)

        result = {
            "rsi14": rsi_v,
            "avg_vol": avg_vol_20,
            "avg_vol_50": avg_vol_50,
            "high_52w": round(h52, 2),
            "low_52w": round(l52, 2),
            "dist_52w": round((h52 - cur) / max(h52, 1), 3),
            "vol_spike": round(vols[-1] / max(avg_vol_20, 1), 3),
            **accumulation,  # 매집 지표 병합
            "_ts": time.time(),
        }
        state.aggs_cache[sym] = result
        return result
    except Exception:
        return {}


def _calc_rsi(closes: list[float]) -> float:
    """RSI(14) 계산"""
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


def _calc_accumulation(opens, closes, highs, lows, vols) -> dict:
    """Wyckoff + OBV + CMF 기반 매집 신호 계산 (0~100점)"""
    n = len(closes)
    if n < 20:
        return {"acc_score": 0, "acc_signals": []}

    # ━━━ 1. OBV (On-Balance Volume) ━━━
    obv = [0]
    for i in range(1, n):
        if closes[i] > closes[i-1]:
            obv.append(obv[-1] + vols[i])
        elif closes[i] < closes[i-1]:
            obv.append(obv[-1] - vols[i])
        else:
            obv.append(obv[-1])

    # OBV 추세: 최근 20일 기울기
    obv_recent = obv[-20:]
    obv_base = abs(obv_recent[0]) + 1
    obv_slope = (obv_recent[-1] - obv_recent[0]) / obv_base

    # ━━━ 2. CMF (Chaikin Money Flow, 20일) ━━━
    mfv_sum = 0.0
    vol_sum = 0.0
    for i in range(max(n-20, 0), n):
        hl = highs[i] - lows[i]
        if hl == 0:
            mfm = 0
        else:
            mfm = ((closes[i] - lows[i]) - (highs[i] - closes[i])) / hl
        mfv = mfm * vols[i]
        mfv_sum += mfv
        vol_sum += vols[i]
    cmf = mfv_sum / max(vol_sum, 1)

    # ━━━ 3. 거래량 급등 일수 (최근 10일 중) ━━━
    if n >= 30:
        avg_base = sum(vols[-30:-10]) / 20
    else:
        avg_base = sum(vols[:max(n-10, 1)]) / max(n-10, 1)
    vol_spike_days = sum(1 for v in vols[-10:] if v >= avg_base * 2.0)

    # ━━━ 4. 가격 안정성 (ATR / 가격) ━━━
    atr_sum = 0.0
    atr_cnt = 0
    for i in range(max(n-10, 1), n):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i-1]),
            abs(lows[i] - closes[i-1]),
        )
        atr_sum += tr
        atr_cnt += 1
    atr = atr_sum / max(atr_cnt, 1)
    price_stability = atr / max(closes[-1], 0.01)

    # ━━━ 5. Wyckoff Spring (하단 지지 테스트 + 회복) ━━━
    near_support = False
    spring_recovery = False
    if n >= 60:
        low_60 = min(lows[-60:])
        low_20 = min(lows[-20:])
        near_support = (low_20 - low_60) / max(low_60, 0.01) < 0.05
        for i in range(max(n-15, 1), n):
            if lows[i] <= low_60 * 1.03 and closes[i] > lows[i] * 1.02:
                if vols[i] >= avg_base * 2:
                    spring_recovery = True
                    break

    # ━━━ 6. 매집 vs 분산 캔들 비율 ━━━
    acc_candles = 0
    dist_candles = 0
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

    # ━━━ 점수 산정 ━━━
    signals = []
    score = 0

    # OBV 상승 추세 (25점)
    if obv_slope > 0.1:
        score += 25
        signals.append(f"OBV+{obv_slope*100:.1f}%")
    elif obv_slope > 0:
        score += 12
        signals.append("OBV 약상승")

    # CMF (20점)
    if cmf > 0.15:
        score += 20
        signals.append(f"CMF강세{cmf:+.2f}")
    elif cmf > 0.05:
        score += 10
        signals.append(f"CMF{cmf:+.2f}")
    elif cmf < -0.1:
        score -= 5

    # 거래량 폭증 일수 (15점)
    if vol_spike_days >= 5:
        score += 15
        signals.append(f"거래량폭증{vol_spike_days}일")
    elif vol_spike_days >= 3:
        score += 8
        signals.append(f"거래량증가{vol_spike_days}일")

    # 가격 안정 + 거래량 (15점)
    if price_stability < 0.03 and vol_spike_days >= 2:
        score += 15
        signals.append("횡보+거래량↑")
    elif price_stability < 0.05 and vol_spike_days >= 2:
        score += 8

    # Wyckoff Spring (15점)
    if spring_recovery:
        score += 15
        signals.append("⚡Spring매집막바지")
    elif near_support and vol_spike_days >= 2:
        score += 8
        signals.append("지지선테스트")

    # 매집 캔들 우세 (10점)
    if acc_ratio >= 0.7 and (acc_candles + dist_candles) >= 5:
        score += 10
        signals.append(f"매집{acc_candles}:{dist_candles}분산")
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


# ────────── 종목 상세 ──────────
def fetch_ticker_details(sym: str) -> dict:
    if not _key_ok():
        return {}
    try:
        r = requests.get(f"{BASE}/v3/reference/tickers/{sym}",
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


# ────────── Short Interest ──────────
def fetch_short_interest_batch() -> dict:
    if not _key_ok():
        return {}
    out = {}
    end = date.today().strftime("%Y-%m-%d")
    start = (date.today() - timedelta(days=30)).strftime("%Y-%m-%d")
    try:
        r = requests.get(
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
                    "avg_vol": avg_v,
                    "si_pct": 0.0,
                }
        print(f"  ✅ Short Interest: {len(out)}개")
    except Exception as e:
        print(f"  ❌ SI 오류: {e}")
    return out


# ────────── Short Volume ──────────
def fetch_short_volume_batch() -> dict:
    if not _key_ok():
        return {}
    out = {}
    target = date.today()
    for _ in range(5):
        if target.weekday() < 5:
            break
        target -= timedelta(days=1)
    date_str = target.strftime("%Y-%m-%d")
    try:
        r = requests.get(
            f"{BASE}/stocks/v1/short-volume",
            params={"date": date_str, "limit": 50000, "sort": "ticker.asc",
                    "apiKey": POLYGON_API_KEY},
            timeout=30,
        )
        if r.status_code != 200:
            return {}
        for res in r.json().get("results", []):
            sym = res.get("ticker", "")
            ratio = float(res.get("short_volume_ratio", 0) or 0)
            if sym and ratio > 0:
                out[sym] = {
                    "short_vol_ratio": round(ratio, 2),
                    "short_volume": int(res.get("short_volume", 0) or 0),
                    "total_volume": int(res.get("total_volume", 1) or 1),
                }
        print(f"  ✅ Short Volume: {len(out)}개")
    except Exception as e:
        print(f"  ❌ SV 오류: {e}")
    return out


# ────────── Float ──────────
def fetch_float_batch() -> dict:
    if not _key_ok():
        return {}
    out = {}
    cursor = None
    while True:
        try:
            params = {"limit": 5000, "sort": "ticker.asc", "apiKey": POLYGON_API_KEY}
            if cursor:
                params["cursor"] = cursor
            r = requests.get(f"{BASE}/stocks/vX/float", params=params, timeout=30)
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
                    out[sym] = {"free_float": ff, "free_float_pct": round(ffp, 2)}
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


# ────────── 기술 지표 ──────────
def fetch_rsi(sym: str) -> float:
    if not _key_ok():
        return 50.0
    try:
        r = requests.get(
            f"{BASE}/v1/indicators/rsi/{sym}",
            params={"timespan": "day", "adjusted": "true", "window": 14,
                    "series_type": "close", "order": "desc", "limit": 1,
                    "apiKey": POLYGON_API_KEY},
            timeout=8,
        )
        if r.status_code != 200:
            return 50.0
        values = r.json().get("results", {}).get("values", [])
        if not values:
            return 50.0
        return round(float(values[0].get("value", 50)), 1)
    except Exception:
        return 50.0


def fetch_macd(sym: str) -> dict:
    if not _key_ok():
        return {}
    try:
        r = requests.get(
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
            "macd": round(float(cur.get("value", 0) or 0), 4),
            "signal": round(float(cur.get("signal", 0) or 0), 4),
            "histogram": round(hist_v, 4),
            "golden_cross": hist_v > 0 and prev_h <= 0,
            "dead_cross": hist_v < 0 and prev_h >= 0,
        }
    except Exception:
        return {}


# ────────── 뉴스 ──────────
def fetch_news_batch(limit: int = 1000) -> dict:
    from datetime import datetime, timezone
    from app.config import CATALYST_KEYWORDS
    if not _key_ok():
        return {}
    out = {}
    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        r = requests.get(
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
            out[sym]["sentiment_score"] = round((out[sym]["pos"] - out[sym]["neg"]) / max(n, 1), 2)
        print(f"  ✅ 뉴스: {len(out)}개 종목")
    except Exception as e:
        print(f"  ❌ 뉴스 오류: {e}")
    return out


# ────────── 실시간 스냅샷 ──────────
def fetch_snapshots(syms: list[str]) -> dict:
    if not _key_ok() or not syms:
        return {}
    out = {}
    for i in range(0, len(syms), 100):
        batch = syms[i:i+100]
        try:
            r = requests.get(
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
