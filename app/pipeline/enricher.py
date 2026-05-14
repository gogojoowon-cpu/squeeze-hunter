"""데이터 보강 + 주기적 다중 갱신"""
import time, random
from datetime import datetime, timezone
from app import state
from app.config import ALERT_COOLDOWN_SEC, HISTORY_MAX
from app.scoring import sqs, estimate_ctb
from app.market import is_market_open
from app.providers import polygon, social as social_provider


# 마지막 갱신 시각 추적
_last_refresh = {
    "aggs": 0,         # 일봉 + 매집 (장중 5분 주기)
    "short_int": 0,    # SI/SV (1일 주기)
    "float_data": 0,   # Float (1일 주기)
    "macd": 0,         # MACD (장중 30분 주기)
    "news": 0,         # 뉴스 (10분 주기)
}


def enrich_all():
    """초기 1회 보강 — 전체 데이터 수집"""
    print("  📊 Short Interest...")
    si_data = polygon.fetch_short_interest_batch()

    print("  📊 Short Volume...")
    sv_data = polygon.fetch_short_volume_batch()

    for sym, d in state.stocks.items():
        if sym in si_data:
            sd = si_data[sym]
            d["si_pct"] = sd["si_pct"]
            d["dtc"] = sd["dtc"]
            d["si_shares"] = sd["si_shares"]
            d["si_src"] = "polygon"
            ctb_e, util_e = estimate_ctb(sd["si_pct"], sd["dtc"])
            d["ctb"], d["util"] = ctb_e, util_e

        if sym in sv_data:
            svr = sv_data[sym]["short_vol_ratio"] * 100
            d["short_vol_ratio"] = round(svr, 2)
            if svr > 50:
                d["ctb"] = round(d.get("ctb", 0) * 1.2, 1)

        r = sqs(d)
        d.update(r)

    _last_refresh["short_int"] = time.time()

    print("  📊 Float...")
    float_data = polygon.fetch_float_batch()
    for sym, fd in float_data.items():
        if sym in state.stocks:
            d = state.stocks[sym]
            d["float_shares"] = fd["free_float"]
            d["free_float_pct"] = fd["free_float_pct"]
            if sym in si_data and fd["free_float"] > 0:
                si_sh = si_data[sym].get("si_shares", 0)
                d["si_pct"] = round(si_sh / fd["free_float"] * 100, 2)
            d["rotation"] = round(d["volume"] / max(fd["free_float"], 1), 5)
            r = sqs(d)
            d.update(r)

    _last_refresh["float_data"] = time.time()

    top_syms = sorted(
        [s for s in state.stocks],
        key=lambda x: state.stocks[x].get("score", 0),
        reverse=True,
    )[:200]
    print(f"  📊 MACD ({len(top_syms)}개)...")
    macd_ok = 0
    for sym in top_syms:
        try:
            macd = polygon.fetch_macd(sym)
            if macd:
                d = state.stocks[sym]
                d["macd_golden_cross"] = macd.get("golden_cross", False)
                d["macd_dead_cross"] = macd.get("dead_cross", False)
                d["macd_histogram"] = macd.get("histogram", 0)
                d["macd_value"] = macd.get("macd", 0)
                d["macd_signal"] = macd.get("signal", 0)
                r = sqs(d)
                d.update(r)
                macd_ok += 1
            time.sleep(0.15)
        except Exception:
            pass
    print(f"  ✅ MACD: {macd_ok}개")
    _last_refresh["macd"] = time.time()

    print("  📰 뉴스...")
    news_data = polygon.fetch_news_batch(limit=1000)
    for sym, nd in news_data.items():
        if sym in state.stocks:
            d = state.stocks[sym]
            d["has_catalyst"] = nd["has_catalyst"]
            d["news_count"] = nd["news_count"]
            d["news_sentiment"] = nd.get("sentiment_score", 0)
            d["latest_news"] = nd["news_titles"][:3]
            r = sqs(d)
            d.update(r)
    print(f"  ✅ 뉴스: {len(news_data)}개")
    _last_refresh["news"] = time.time()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 주기적 갱신 함수들
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def refresh_aggs_for_top(n: int = 200):
    """상위 종목 일봉/매집/RSI/52주 갱신 (장중 5분 주기)"""
    if not is_market_open():
        return 0

    # SQS 점수 상위 + 매집 점수 상위 둘 다 갱신
    by_sqs = sorted(state.stocks.keys(),
                    key=lambda x: state.stocks[x].get("score", 0),
                    reverse=True)[:n]
    by_acc = sorted(state.stocks.keys(),
                    key=lambda x: state.stocks[x].get("acc_score", 0),
                    reverse=True)[:n]
    targets = list(set(by_sqs + by_acc))[:n*2]

    # 캐시 강제 무효화
    for sym in targets:
        state.aggs_cache.pop(sym, None)

    updated = 0
    for sym in targets:
        try:
            agg = polygon.fetch_aggs(sym)
            if agg:
                state.stocks[sym].update({
                    "rsi14": agg.get("rsi14", 50),
                    "high_52w": agg.get("high_52w", 0),
                    "low_52w": agg.get("low_52w", 0),
                    "dist_52w": agg.get("dist_52w", 0.5),
                    "vol_spike": agg.get("vol_spike", 1),
                    "acc_score": agg.get("acc_score", 0),
                    "acc_signals": agg.get("acc_signals", []),
                    "obv_slope": agg.get("obv_slope", 0),
                    "cmf": agg.get("cmf", 0),
                    "vol_spike_days": agg.get("vol_spike_days", 0),
                    "spring_recovery": agg.get("spring_recovery", False),
                    "near_support": agg.get("near_support", False),
                })
                r = sqs(state.stocks[sym])
                state.stocks[sym].update(r)
                updated += 1
            time.sleep(0.1)
        except Exception:
            pass
    return updated


def refresh_short_interest():
    """SI/SV 전체 갱신 (1일 주기)"""
    si_data = polygon.fetch_short_interest_batch()
    sv_data = polygon.fetch_short_volume_batch()

    for sym, d in state.stocks.items():
        if sym in si_data:
            sd = si_data[sym]
            d["si_pct"] = sd["si_pct"]
            d["dtc"] = sd["dtc"]
            d["si_shares"] = sd["si_shares"]
            ctb_e, util_e = estimate_ctb(sd["si_pct"], sd["dtc"])
            d["ctb"], d["util"] = ctb_e, util_e

        if sym in sv_data:
            svr = sv_data[sym]["short_vol_ratio"] * 100
            d["short_vol_ratio"] = round(svr, 2)

        r = sqs(d)
        d.update(r)

    return len(si_data)


def refresh_float():
    """Float 전체 갱신 (1일 주기)"""
    float_data = polygon.fetch_float_batch()
    for sym, fd in float_data.items():
        if sym in state.stocks:
            d = state.stocks[sym]
            d["float_shares"] = fd["free_float"]
            d["free_float_pct"] = fd["free_float_pct"]
            d["rotation"] = round(d.get("volume", 0) / max(fd["free_float"], 1), 5)
            r = sqs(d)
            d.update(r)
    return len(float_data)


def refresh_macd_top(n: int = 200):
    """상위 종목 MACD 갱신 (30분 주기)"""
    top = sorted(state.stocks.keys(),
                 key=lambda x: state.stocks[x].get("score", 0),
                 reverse=True)[:n]
    ok = 0
    for sym in top:
        try:
            macd = polygon.fetch_macd(sym)
            if macd:
                d = state.stocks[sym]
                d["macd_golden_cross"] = macd.get("golden_cross", False)
                d["macd_dead_cross"] = macd.get("dead_cross", False)
                d["macd_histogram"] = macd.get("histogram", 0)
                d["macd_value"] = macd.get("macd", 0)
                d["macd_signal"] = macd.get("signal", 0)
                r = sqs(d)
                d.update(r)
                ok += 1
            time.sleep(0.15)
        except Exception:
            pass
    return ok


def refresh_news():
    """뉴스 갱신 (10분 주기)"""
    news_data = polygon.fetch_news_batch(limit=1000)
    cnt = 0
    for sym, nd in news_data.items():
        if sym in state.stocks:
            d = state.stocks[sym]
            d["has_catalyst"] = nd["has_catalyst"]
            d["news_count"] = nd["news_count"]
            d["news_sentiment"] = nd.get("sentiment_score", 0)
            d["latest_news"] = nd["news_titles"][:3]
            r = sqs(d)
            d.update(r)
            cnt += 1
    return cnt


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 30초 주기 tick
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def tick_once():
    """30초마다: 가격 + 소셜 + 점수 + 시간별 보강"""
    if not state.ready or not state.stocks:
        return

    prev_grades = {s: state.stocks[s].get("grade", "NO_SQUEEZE") for s in state.stocks}

    # 1) 가격 (장중에만, 100개 샘플)
    if is_market_open():
        sample = random.sample(list(state.stocks.keys()), min(100, len(state.stocks)))
        snaps = polygon.fetch_snapshots(sample)
        for sym, snap in snaps.items():
            if sym in state.stocks:
                state.stocks[sym].update(snap)

    # 2) 소셜 (Apewisdom 2분 캐시는 내부에 있음)
    soc = social_provider.fetch_social()
    for sym, sd in soc.items():
        if sym in state.stocks:
            d = state.stocks[sym]
            d["social_velocity"] = float(sd.get("social_velocity", 0))
            d["sentiment"] = float(sd.get("sentiment", 0))
            d["mentions"] = int(sd.get("mentions", 0))

    # 3) 시간별 보강 (장중 5분 주기 - 상위 종목 일봉/매집)
    now = time.time()
    if is_market_open() and now - _last_refresh["aggs"] > 300:
        print("🔄 [5분 주기] 상위 종목 일봉/매집 갱신...")
        n = refresh_aggs_for_top(200)
        print(f"  ✅ {n}개 갱신 완료")
        _last_refresh["aggs"] = now

    # 4) MACD (장중 30분 주기)
    if is_market_open() and now - _last_refresh["macd"] > 1800:
        print("🔄 [30분 주기] MACD 갱신...")
        ok = refresh_macd_top(200)
        print(f"  ✅ MACD {ok}개 갱신")
        _last_refresh["macd"] = now

    # 5) 뉴스 (10분 주기 - 24시간 작동)
    if now - _last_refresh["news"] > 600:
        print("🔄 [10분 주기] 뉴스 갱신...")
        cnt = refresh_news()
        print(f"  ✅ 뉴스 {cnt}개 종목")
        _last_refresh["news"] = now

    # 6) SI/SV (1일 주기 - 86400초)
    if now - _last_refresh["short_int"] > 86400:
        print("🔄 [1일 주기] Short Interest 갱신...")
        n = refresh_short_interest()
        print(f"  ✅ SI {n}개 갱신")
        _last_refresh["short_int"] = now

    # 7) Float (1일 주기)
    if now - _last_refresh["float_data"] > 86400:
        print("🔄 [1일 주기] Float 갱신...")
        n = refresh_float()
        print(f"  ✅ Float {n}개 갱신")
        _last_refresh["float_data"] = now

    # 8) 점수 재계산 + 히스토리 + 알림
    ts = datetime.now(timezone.utc).isoformat()
    gkr = {"IMMINENT": "임박", "HIGH": "높음"}

    for sym, d in state.stocks.items():
        prev_score = d.get("score", 0)
        r = sqs(d)
        d.update(r)
        d["delta"] = round(d["score"] - prev_score, 2)
        d["ts"] = ts

        h = state.history.setdefault(sym, [])
        h.append({"ts": ts, "score": d["score"], "grade": d["grade"]})
        if len(h) > HISTORY_MAX:
            h.pop(0)

        if d["grade"] in ("IMMINENT", "HIGH") and d["grade"] != prev_grades.get(sym):
            if time.time() - state.alert_cooldown.get(sym, 0) > ALERT_COOLDOWN_SEC:
                state.alert_cooldown[sym] = time.time()
                state.alerts.insert(0, {
                    "id": len(state.alerts) + 1,
                    "symbol": sym,
                    "grade": d["grade"],
                    "score": d["score"],
                    "created_at": ts,
                    "theme": d.get("theme", "기타"),
                    "message": f"[{d.get('theme','?')}] {sym}({d.get('name',sym)}) → {gkr.get(d['grade'],'')} — {d['score']:.1f}점",
                })
                if len(state.alerts) > 300:
                    state.alerts.pop()


def tick_loop():
    """30초 주기 메인 루프"""
    while True:
        time.sleep(30)
        try:
            tick_once()
        except Exception as e:
            print(f"⚠️ tick 오류: {e}")
