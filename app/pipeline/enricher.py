"""데이터 보강 (SI, Float, MACD, 뉴스) + 주기적 갱신"""
import time, random
from datetime import datetime, timezone
from app import state
from app.config import ALERT_COOLDOWN_SEC, HISTORY_MAX
from app.scoring import sqs, estimate_ctb
from app.market import is_market_open
from app.providers import polygon, social as social_provider


def enrich_all():
    """SI/SV/Float/MACD/뉴스 일괄 보강"""
    print("  📊 Short Interest...")
    si_data = polygon.fetch_short_interest_batch()

    print("  📊 Short Volume...")
    sv_data = polygon.fetch_short_volume_batch()

    # SI/SV 반영
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

    # Float
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

    # MACD (상위 200개)
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

    # 뉴스
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


def tick_once():
    """30초마다: 가격 + 소셜 + 점수 재계산 + 알림"""
    if not state.ready or not state.stocks:
        return

    prev_grades = {s: state.stocks[s].get("grade", "NO_SQUEEZE") for s in state.stocks}

    # 장중에만 가격 갱신
    if is_market_open():
        sample = random.sample(list(state.stocks.keys()), min(100, len(state.stocks)))
        snaps = polygon.fetch_snapshots(sample)
        for sym, snap in snaps.items():
            if sym in state.stocks:
                state.stocks[sym].update(snap)

    # 소셜 갱신
    soc = social_provider.fetch_social()
    for sym, sd in soc.items():
        if sym in state.stocks:
            d = state.stocks[sym]
            d["social_velocity"] = float(sd.get("social_velocity", 0))
            d["sentiment"] = float(sd.get("sentiment", 0))
            d["mentions"] = int(sd.get("mentions", 0))

    # 점수 재계산 + 히스토리
    now = datetime.now(timezone.utc).isoformat()
    gkr = {"IMMINENT": "임박", "HIGH": "높음"}

    for sym, d in state.stocks.items():
        prev_score = d.get("score", 0)
        r = sqs(d)
        d.update(r)
        d["delta"] = round(d["score"] - prev_score, 2)
        d["ts"] = now

        h = state.history.setdefault(sym, [])
        h.append({"ts": now, "score": d["score"], "grade": d["grade"]})
        if len(h) > HISTORY_MAX:
            h.pop(0)

        # 알림 (30분 쿨다운)
        if d["grade"] in ("IMMINENT", "HIGH") and d["grade"] != prev_grades.get(sym):
            if time.time() - state.alert_cooldown.get(sym, 0) > ALERT_COOLDOWN_SEC:
                state.alert_cooldown[sym] = time.time()
                state.alerts.insert(0, {
                    "id": len(state.alerts) + 1,
                    "symbol": sym,
                    "grade": d["grade"],
                    "score": d["score"],
                    "created_at": now,
                    "theme": d.get("theme", "기타"),
                    "message": f"[{d.get('theme','?')}] {sym}({d.get('name',sym)}) → {gkr.get(d['grade'],'')} — {d['score']:.1f}점",
                })
                if len(state.alerts) > 300:
                    state.alerts.pop()


def tick_loop():
    """30초 주기"""
    while True:
        time.sleep(30)
        try:
            tick_once()
        except Exception as e:
            print(f"⚠️ tick 오류: {e}")
