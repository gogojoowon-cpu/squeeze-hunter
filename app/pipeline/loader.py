"""초기 데이터 로딩 — 동적 티커 수집 + Polygon"""
import time
from datetime import datetime, timezone
from app import state
from app.config import MIN_PRICE, MIN_VOLUME, MIN_AVG_VOLUME, DELISTED
from app.scoring import sqs, estimate_ctb
from app.themes import classify_theme
from app.providers import polygon, social as social_provider


def init_data():
    """동적 티커 수집 → 가격 → 점수 계산 → 보강"""
    print("=" * 60)
    print("🔥 숏 스퀴즈 헌터 v3 — 데이터 로딩 시작")
    print("=" * 60)

    # 1) 전체 티커 수집
    print("\n📋 [1/5] 전체 미국 상장 종목 수집...")
    tickers = polygon.fetch_all_tickers()
    if not tickers:
        print("❌ 티커 수집 실패 — API 키/플랜 확인")
        state.ready = True
        state.enrich_done = True
        return

    ticker_info = {t["symbol"]: t for t in tickers if t["symbol"] not in DELISTED}
    print(f"✅ 필터 후 {len(ticker_info)}개 종목")

    # 2) 소셜
    print("\n📱 [2/5] 소셜 데이터...")
    social = social_provider.fetch_social()

    # 3) 가격 (grouped daily)
    print("\n📡 [3/5] 가격 스냅샷 (grouped daily)...")
    snaps = polygon.fetch_grouped_daily()
    print(f"✅ 가격 데이터: {len(snaps)}개")

    # 4) 종목별 처리
    print("\n📊 [4/5] 종목별 상세 처리...")
    processed = 0
    for sym, snap in snaps.items():
        if sym not in ticker_info:
            continue
        try:
            price = snap["price"]
            vol = snap["volume"]
            if price < MIN_PRICE or vol < MIN_VOLUME:
                continue

            agg = polygon.fetch_aggs(sym)
            avg_vol = agg.get("avg_vol", max(vol, 1))
            if avg_vol < MIN_AVG_VOLUME:
                continue

            info = ticker_info[sym]
            name = info["name"]
            sic = info.get("sic", 0)
            theme = classify_theme(sic, name, price)

            ctb_e, util_e = estimate_ctb(0, 0)
            sd = social.get(sym, {})

            d = {
                "symbol": sym, "name": name, "sector": "기타", "theme": theme,
                "market_cap": 0, "has_dilution": False,
                "price": price, "volume": vol,
                "vol_spike": agg.get("vol_spike", 1.0),
                "dist_52w": agg.get("dist_52w", 0.5),
                "high_52w": agg.get("high_52w", price),
                "low_52w": agg.get("low_52w", price),
                "rsi14": agg.get("rsi14", 50.0),
                "si_pct": 0.0, "si_shares": 0, "dtc": 0.0,
                "float_shares": 0, "rotation": 0,
                "ctb": ctb_e, "util": util_e, "ctb_src": "estimated",
                "gamma_conc": 0.0,
                "social_velocity": float(sd.get("social_velocity", 0)),
                "sentiment": float(sd.get("sentiment", 0)),
                "mentions": int(sd.get("mentions", 0)),
                "soc_src": sd.get("src", "demo"),
                "has_catalyst": False,
                "change_pct": snap.get("change_pct", 0),
            }

            r = sqs(d)
            d.update(r)
            d["ts"] = datetime.now(timezone.utc).isoformat()
            d["delta"] = 0.0

            state.stocks[sym] = d
            state.history[sym] = []
            processed += 1

            if processed % 500 == 0:
                print(f"  ✅ {processed}개 처리...")
        except Exception:
            pass

    print(f"\n✅ [4/5] 기본 로딩 완료: {processed}개 종목")
    state.ready = True

    # 5) 보강
    print("\n🔧 [5/5] 데이터 보강 시작 (SI/Float/MACD/뉴스)...")
    from app.pipeline.enricher import enrich_all
    enrich_all()
    state.enrich_done = True

    print("\n" + "=" * 60)
    print(f"🏁 전체 완료! {len(state.stocks)}개 종목 활성화")
    print("=" * 60)
