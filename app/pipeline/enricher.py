"""
데이터 보강 + 점수 재계산 파이프라인
- Dirty-flag 기반 부분 재계산
- 우선순위 큐: 상위 500 (30초) / 중위 2000 (5분) / 나머지 (30분)
- 데이터별 차등 갱신 주기
- VERBOSE_LOGS=true 환경변수로 주기 갱신 로그 ON/OFF
- ⭐ v2: SI% 후처리 계산 + 우선순위 큐 개선 (squeeze 후보 우선)
"""
import os
import time
import threading
from datetime import datetime, timezone

from app import state
from app.config import (
    RESCORE_TOP_INTERVAL,
    RESCORE_MID_INTERVAL,
    RESCORE_LOW_INTERVAL,
    TOP_N_SYMBOLS,
    MID_N_SYMBOLS,
)
from app.scoring import sqs, grade, estimate_ctb
from app.providers import polygon, social
from app.pipeline.analyzers import detect_anomalies, check_event_alerts

# ============================================================
# 로그 제어 (환경변수)
# ============================================================
VERBOSE = os.getenv("VERBOSE_LOGS", "false").lower() in ("true", "1", "yes")

def _log(msg):
    """verbose 모드에서만 출력 (주기 갱신 로그용)"""
    if VERBOSE:
        print(msg)

# 마지막 갱신 시각 추적
_last = {
    "grouped": 0,
    "social": 0,
    "aggs_top": 0,
    "aggs_mid": 0,
    "macd": 0,
    "news": 0,
    "options": 0,
    "si": 0,
    "sv": 0,
    "float": 0,
    "fundamentals": 0,
    "events": 0,
    "rescore_top": 0,
    "rescore_mid": 0,
    "rescore_low": 0,
    "anomaly": 0,
}


# ============================================================
# ⭐ SI% 후처리 (Float 데이터 받은 후 계산)
# ============================================================
def _recompute_si_pct():
    """
    SI shares + Float shares → SI% 계산.
    fetch_short_interest_batch()는 si_shares만 주고,
    fetch_float_batch()는 float_shares를 주므로 둘 다 들어온 후 계산해야 함.
    """
    cnt = 0
    for sym, m in state.stocks.items():
        si_sh = m.get("si_shares", 0) or 0
        fs = m.get("float_shares", 0) or 0
        if si_sh > 0 and fs > 0:
            si_pct = round((si_sh / fs) * 100, 2)
            # 비현실적인 값 (>100%) 은 cap
            if si_pct > 100:
                si_pct = 100.0
            m["si_pct"] = si_pct
            # CTB / Util 추정 (실제 데이터 없으므로 SI%+DTC 기반)
            ctb, util = estimate_ctb(si_pct, m.get("dtc", 0) or 0)
            m["ctb"] = ctb
            m["util"] = util
            cnt += 1
    return cnt


# ============================================================
# 초기 데이터 보강 (최초 1회)
# ============================================================
def enrich_all():
    """기동 시 1회: 모든 종목에 대해 보강"""
    print("🔄 [5/5] 데이터 보강 시작...")

    syms = list(state.stocks.keys())
    if not syms:
        print("⚠️ 보강할 종목 없음")
        return

    # 1) Short Interest
    print("  📊 Short Interest 수집...")
    si_data = polygon.fetch_short_interest_batch()
    si_cnt = 0
    for sym, d in si_data.items():
        if sym in state.stocks:
            state.stocks[sym].update(d)
            si_cnt += 1
    print(f"  ✅ SI {si_cnt}개")

    # 2) Short Volume + Dark Pool
    print("  📊 Short Volume + Dark Pool 수집...")
    sv_data = polygon.fetch_short_volume_batch()
    sv_cnt = 0
    for sym, d in sv_data.items():
        if sym in state.stocks:
            state.stocks[sym].update(d)
            sv_cnt += 1
    print(f"  ✅ SV {sv_cnt}개")

    # 3) Float
    print("  📊 Float 수집...")
    fl_data = polygon.fetch_float_batch()
    fl_cnt = 0
    for sym, d in fl_data.items():
        if sym in state.stocks:
            state.stocks[sym].update(d)
            fl_cnt += 1
    print(f"  ✅ Float {fl_cnt}개")

    # 3.5) ⭐ SI% 후처리 계산 (SI shares + Float shares 결합)
    print("  🧮 SI% 계산 중...")
    si_pct_cnt = _recompute_si_pct()
    print(f"  ✅ SI% 계산 {si_pct_cnt}개")

    # 4) 일봉 + 매집 + 이상거래 (상위 1000개만 초기에)
    print("  📊 일봉/매집/이상거래 분석 (상위 1000개)...")
    top_syms = _get_priority_symbols(1000)
    agg_cnt = 0
    for i, sym in enumerate(top_syms):
        try:
            d = polygon.fetch_aggs(sym)
            if d and sym in state.stocks:
                state.stocks[sym].update(d)
                agg_cnt += 1
        except Exception:
            pass
        if (i + 1) % 200 == 0:
            print(f"    ✅ {i+1}/{len(top_syms)} 처리")
    print(f"  ✅ 일봉 {agg_cnt}개")

    # 5) MACD (상위 300)
    print("  📊 MACD (상위 300개)...")
    macd_syms = _get_priority_symbols(300)
    macd_cnt = 0
    for sym in macd_syms:
        try:
            d = polygon.fetch_macd(sym)
            if d and sym in state.stocks:
                state.stocks[sym].update(d)
                macd_cnt += 1
        except Exception:
            pass
    print(f"  ✅ MACD {macd_cnt}개")

    # 6) 뉴스
    print("  📊 뉴스 + 촉매 수집...")
    news_data = polygon.fetch_news_batch(limit=1000)
    news_cnt = 0
    for sym, d in news_data.items():
        if sym in state.stocks:
            state.stocks[sym].update(d)
            news_cnt += 1
    print(f"  ✅ 뉴스 {news_cnt}개")

    # 7) 옵션 체인 (상위 200) — 권한 없으면 자동 skip
    print("  📊 옵션 체인 (상위 200개)...")
    opt_syms = _get_priority_symbols(200)
    opt_cnt = 0
    for sym in opt_syms:
        try:
            d = polygon.fetch_options_chain(sym)
            if d and sym in state.stocks:
                state.stocks[sym].update(d)
                opt_cnt += 1
        except Exception:
            pass
    print(f"  ✅ 옵션 {opt_cnt}개")

    # 8) 펀더멘털 (상위 500)
    print("  📊 펀더멘털 (상위 500개)...")
    fund_syms = _get_priority_symbols(500)
    fund_cnt = 0
    for sym in fund_syms:
        try:
            d = polygon.fetch_fundamentals(sym)
            if d and sym in state.stocks:
                state.stocks[sym].update(d)
                fund_cnt += 1
        except Exception:
            pass
    print(f"  ✅ 펀더멘털 {fund_cnt}개")

    # 9) 기업 이벤트
    print("  📊 기업 이벤트 수집...")
    try:
        divs = polygon.fetch_upcoming_dividends()
        splits = polygon.fetch_upcoming_splits()
        ev_cnt = 0
        for sym, d in divs.items():
            if sym in state.stocks:
                state.stocks[sym]["upcoming_dividend"] = d
                ev_cnt += 1
        for sym, d in splits.items():
            if sym in state.stocks:
                state.stocks[sym]["upcoming_split"] = d
                ev_cnt += 1
        print(f"  ✅ 이벤트 {ev_cnt}개")
    except Exception as e:
        print(f"  ⚠️ 이벤트 수집 실패: {e}")

    # 10) 초기 점수 계산
    print("  📊 초기 점수 계산...")
    _rescore_all()

    # 11) 이상거래 탐지
    print("  📊 이상거래 탐지...")
    detect_anomalies()

    now = time.time()
    for k in _last:
        _last[k] = now

    state.ready = True
    print("🏁 전체 완료!")


# ============================================================
# ⭐ 우선순위 기반 심볼 선택 (Squeeze 후보 우선)
# ============================================================
def _get_priority_symbols(n):
    """
    우선순위 기반 상위 N개 종목 선택.
    
    초기엔 SQS 점수가 0이므로 다음 순으로 우선시:
    1. acc_score (매집 점수)
    2. 거래량
    3. SI 데이터 있는 종목 (스퀴즈 후보군)
    4. $1~$50 가격대 (스퀴즈 자주 발생)
    5. 대형주 페널티 (AAPL/MSFT 등 거대 종목 배제)
    """
    items = []
    for sym, m in state.stocks.items():
        price = m.get("price", 0) or 0
        if price <= 0:
            continue
        score = m.get("sqs_score", 0) or 0
        acc = m.get("acc_score", 0) or 0
        vol = m.get("volume", 0) or 0
        si_sh = m.get("si_shares", 0) or 0
        si_pct = m.get("si_pct", 0) or 0
        mcap = m.get("market_cap", 0) or 0

        priority = (
            score * 3                                # 점수 (가장 강한 신호)
            + acc * 1.5                              # 매집 점수
            + (vol / 1_000_000) * 0.5                # 거래량 (백만 단위)
            + (20 if si_sh > 0 else 0)               # SI 데이터 있으면 큰 보너스
            + (si_pct * 0.5)                         # SI% 높을수록 우선
            + (5 if 1 <= price <= 50 else 0)         # squeeze 가능 가격대 보너스
            - (10 if mcap > 100e9 else 0)            # 대형주(>$100B) 페널티
        )
        items.append((sym, priority))
    items.sort(key=lambda x: -x[1])
    return [s for s, _ in items[:n]]


# ============================================================
# 점수 재계산
# ============================================================
def _rescore_all():
    """전체 재계산 (초기 1회만 사용)"""
    cnt = 0
    for sym, m in state.stocks.items():
        try:
            r = sqs(m)
            m["sqs_score"] = r["score"]
            m["grade"] = r["grade"]
            m["breakdown"] = r["breakdown"]
            cnt += 1
        except Exception:
            pass
    state.dirty_symbols.clear()
    print(f"    ✅ 전체 재계산 {cnt}개")


def _rescore_dirty():
    """Dirty-flag 된 종목만 재계산"""
    if not state.dirty_symbols:
        return 0
    dirty = list(state.dirty_symbols)
    state.dirty_symbols.clear()
    cnt = 0
    for sym in dirty:
        m = state.stocks.get(sym)
        if not m:
            continue
        try:
            old = m.get("sqs_score", 0)
            r = sqs(m)
            m["sqs_score"] = r["score"]
            m["grade"] = r["grade"]
            m["breakdown"] = r["breakdown"]
            if abs(r["score"] - old) >= 1:
                hist = state.history.setdefault(sym, [])
                hist.append({"t": time.time(), "s": r["score"]})
                if len(hist) > 200:
                    del hist[:-200]
            cnt += 1
        except Exception:
            pass
    return cnt


def _mark_dirty(syms):
    if isinstance(syms, str):
        state.dirty_symbols.add(syms)
    else:
        state.dirty_symbols.update(syms)


# ============================================================
# 주기적 갱신 함수들
# ============================================================
# 파일 상단 (import 아래) 또는 함수 바로 위에 모듈 변수 추가
_grouped_log_counter = 0

def _refresh_grouped():
    """30초 주기 가격/거래량 갱신 (grouped daily)"""
    global _grouped_log_counter
    
    try:
        data = polygon.fetch_grouped_daily()
    except Exception as e:
        print(f"⚠️ grouped 수집 실패: {e}")
        return
    
    if not data:
        return
    
    # 🛡️ 응답이 list인지 확인 (dict면 .values()로 변환)
    if isinstance(data, dict):
        # {ticker: {...}} 형태일 수도 있고, {"results": [...]} 형태일 수도 있음
        if "results" in data:
            data = data["results"]
        else:
            data = list(data.values())
    
    if not isinstance(data, list):
        print(f"⚠️ grouped 응답 형식 이상: {type(data).__name__}")
        return
    
    updated = 0
    dirty_added = 0
    skipped = 0
    
    for row in data:
        # 🛡️ row가 dict가 아니면 스킵
        if not isinstance(row, dict):
            skipped += 1
            continue
        
        sym = row.get("T") or row.get("ticker") or row.get("symbol")
        # ✅ state.stocks 로 통일 (state.symbols 아님!)
        if not sym or sym not in state.stocks:
            continue
        
        d = state.stocks[sym]
        if not isinstance(d, dict):
            skipped += 1
            continue
        
        old_price = d.get("price", 0) or 0
        new_price = row.get("c", 0) or row.get("close", 0) or 0
        new_vol = row.get("v", 0) or row.get("volume", 0) or 0
        
        if new_price > 0:
            d["price"] = new_price
            d["volume"] = new_vol
            updated += 1
            
            # 0.3% 이상 변동시 dirty 마크
            if old_price > 0:
                change = abs(new_price - old_price) / old_price
                if change > 0.003:
                    state.dirty_symbols.add(sym)
                    dirty_added += 1
    
    # 10번에 1번만 출력 (≈ 5분마다)
    _grouped_log_counter += 1
    if _grouped_log_counter % 10 == 1:
        msg = f"  📡 grouped: {len(data)}개 수신, {updated}개 적용, dirty +{dirty_added}"
        if skipped > 0:
            msg += f", skipped {skipped}"
        print(msg)



def _refresh_social():
    """소셜 갱신 (5분)"""
    try:
        data = social.fetch_social()
        cnt = 0
        for sym, d in data.items():
            if sym in state.stocks:
                state.stocks[sym].update(d)
                _mark_dirty(sym)
                cnt += 1
        _log(f"🔄 [5분] 소셜 갱신 {cnt}개")
    except Exception as e:
        print(f"⚠️ 소셜 갱신 실패: {e}")


def _refresh_aggs_top():
    """상위 일봉/매집 갱신 (5분)"""
    try:
        syms = _get_priority_symbols(TOP_N_SYMBOLS)
        cnt = 0
        for sym in syms:
            try:
                d = polygon.fetch_aggs(sym)
                if d and sym in state.stocks:
                    state.stocks[sym].update(d)
                    _mark_dirty(sym)
                    cnt += 1
            except Exception:
                pass
        _log(f"🔄 [5분] 상위 일봉/매집 {cnt}개")
    except Exception as e:
        print(f"⚠️ 일봉 갱신 실패: {e}")


def _refresh_aggs_mid():
    """중위 일봉 갱신 (30분)"""
    try:
        all_top = set(_get_priority_symbols(TOP_N_SYMBOLS))
        mid = [s for s in _get_priority_symbols(MID_N_SYMBOLS) if s not in all_top]
        cnt = 0
        for sym in mid:
            try:
                d = polygon.fetch_aggs(sym)
                if d and sym in state.stocks:
                    state.stocks[sym].update(d)
                    _mark_dirty(sym)
                    cnt += 1
            except Exception:
                pass
        _log(f"🔄 [30분] 중위 일봉 {cnt}개")
    except Exception as e:
        print(f"⚠️ 중위 일봉 실패: {e}")


def _refresh_macd():
    """MACD 갱신 (30분, 상위 300)"""
    try:
        syms = _get_priority_symbols(300)
        cnt = 0
        for sym in syms:
            try:
                d = polygon.fetch_macd(sym)
                if d and sym in state.stocks:
                    state.stocks[sym].update(d)
                    _mark_dirty(sym)
                    cnt += 1
            except Exception:
                pass
        _log(f"🔄 [30분] MACD {cnt}개")
    except Exception as e:
        print(f"⚠️ MACD 실패: {e}")


def _refresh_news():
    """뉴스 갱신 (10분)"""
    try:
        data = polygon.fetch_news_batch(limit=1000)
        cnt = 0
        for sym, d in data.items():
            if sym in state.stocks:
                old_cat = state.stocks[sym].get("has_catalyst", False)
                state.stocks[sym].update(d)
                if d.get("has_catalyst") and not old_cat:
                    _mark_dirty(sym)
                cnt += 1
        _log(f"🔄 [10분] 뉴스 {cnt}개")
    except Exception as e:
        print(f"⚠️ 뉴스 실패: {e}")


def _refresh_options():
    """옵션 체인 갱신 (15분, 상위 200) — 권한 없으면 자동 skip"""
    try:
        syms = _get_priority_symbols(200)
        cnt = 0
        for sym in syms:
            try:
                d = polygon.fetch_options_chain(sym)
                if d and sym in state.stocks:
                    state.stocks[sym].update(d)
                    _mark_dirty(sym)
                    cnt += 1
            except Exception:
                pass
        _log(f"🔄 [15분] 옵션 체인 {cnt}개")
    except Exception as e:
        print(f"⚠️ 옵션 실패: {e}")


def _refresh_si():
    """Short Interest 갱신 (1일)"""
    try:
        data = polygon.fetch_short_interest_batch()
        cnt = 0
        for sym, d in data.items():
            if sym in state.stocks:
                state.stocks[sym].update(d)
                _mark_dirty(sym)
                cnt += 1
        # ⭐ SI 갱신 후 si_pct 재계산
        _recompute_si_pct()
        _log(f"🔄 [1일] SI {cnt}개 + si_pct 재계산")
    except Exception as e:
        print(f"⚠️ SI 실패: {e}")


def _refresh_sv():
    """Short Volume + Dark Pool 갱신 (1일)"""
    try:
        data = polygon.fetch_short_volume_batch()
        cnt = 0
        for sym, d in data.items():
            if sym in state.stocks:
                state.stocks[sym].update(d)
                _mark_dirty(sym)
                cnt += 1
        _log(f"🔄 [1일] SV/DarkPool {cnt}개")
    except Exception as e:
        print(f"⚠️ SV 실패: {e}")


def _refresh_float():
    """Float 갱신 (1일)"""
    try:
        data = polygon.fetch_float_batch()
        cnt = 0
        for sym, d in data.items():
            if sym in state.stocks:
                state.stocks[sym].update(d)
                _mark_dirty(sym)
                cnt += 1
        # ⭐ Float 갱신 후 si_pct 재계산 (float이 바뀌면 si_pct도 바뀜)
        _recompute_si_pct()
        _log(f"🔄 [1일] Float {cnt}개 + si_pct 재계산")
    except Exception as e:
        print(f"⚠️ Float 실패: {e}")


def _refresh_fundamentals():
    """펀더멘털 갱신 (1일, 상위 500)"""
    try:
        syms = _get_priority_symbols(500)
        cnt = 0
        for sym in syms:
            try:
                d = polygon.fetch_fundamentals(sym)
                if d and sym in state.stocks:
                    state.stocks[sym].update(d)
                    _mark_dirty(sym)
                    cnt += 1
            except Exception:
                pass
        _log(f"🔄 [1일] 펀더멘털 {cnt}개")
    except Exception as e:
        print(f"⚠️ 펀더멘털 실패: {e}")


def _refresh_events():
    """기업 이벤트 갱신 (1일)"""
    try:
        divs = polygon.fetch_upcoming_dividends()
        splits = polygon.fetch_upcoming_splits()
        cnt = 0
        for sym, d in divs.items():
            if sym in state.stocks:
                state.stocks[sym]["upcoming_dividend"] = d
                cnt += 1
        for sym, d in splits.items():
            if sym in state.stocks:
                state.stocks[sym]["upcoming_split"] = d
                cnt += 1
        _log(f"🔄 [1일] 이벤트 {cnt}개")
    except Exception as e:
        print(f"⚠️ 이벤트 실패: {e}")


# ============================================================
# 메인 틱 루프
# ============================================================
def tick_once():
    """매 5초마다 호출 - 시간 경과별 작업 실행"""
    now = time.time()

    # 30초: 가격 (WebSocket 켜져 있으면 스킵)
    if now - _last["grouped"] > 30 and not state.ws_connected:
        _refresh_grouped()
        _last["grouped"] = now

    # 5분: 소셜
    if now - _last["social"] > 300:
        _refresh_social()
        _last["social"] = now

    # 5분: 상위 일봉/매집
    if now - _last["aggs_top"] > 300:
        _refresh_aggs_top()
        _last["aggs_top"] = now

    # 10분: 뉴스
    if now - _last["news"] > 600:
        _refresh_news()
        _last["news"] = now

    # 15분: 옵션 체인
    if now - _last["options"] > 900:
        _refresh_options()
        _last["options"] = now

    # 30분: 중위 일봉
    if now - _last["aggs_mid"] > 1800:
        _refresh_aggs_mid()
        _last["aggs_mid"] = now

    # 30분: MACD
    if now - _last["macd"] > 1800:
        _refresh_macd()
        _last["macd"] = now

    # 1일: SI/SV/Float/펀더멘털/이벤트
    if now - _last["si"] > 86400:
        _refresh_si()
        _last["si"] = now
    if now - _last["sv"] > 86400:
        _refresh_sv()
        _last["sv"] = now
    if now - _last["float"] > 86400:
        _refresh_float()
        _last["float"] = now
    if now - _last["fundamentals"] > 86400:
        _refresh_fundamentals()
        _last["fundamentals"] = now
    if now - _last["events"] > 86400:
        _refresh_events()
        _last["events"] = now

    # 점수 재계산 (Dirty-flag, 30초)
    if now - _last["rescore_top"] > RESCORE_TOP_INTERVAL:
        n = _rescore_dirty()
        if n > 0:
            _log(f"🎯 [재계산] {n}개")
        _last["rescore_top"] = now

    # 이상거래 탐지 (5분)
    if now - _last["anomaly"] > 300:
        try:
            detect_anomalies()
        except Exception as e:
            print(f"⚠️ 이상거래 탐지 실패: {e}")
        _last["anomaly"] = now

    # 알림 트리거
    try:
        check_event_alerts()
    except Exception as e:
        print(f"⚠️ 알림 체크 실패: {e}")


def tick_loop():
    """백그라운드 스레드"""
    while True:
        try:
            if state.ready:
                tick_once()
        except Exception as e:
            import traceback
            print(f"❌ tick 오류: {e}")
            traceback.print_exc()
        time.sleep(5)


def start_tick_thread():
    t = threading.Thread(target=tick_loop, daemon=True)
    t.start()
    print("✅ Tick 루프 시작 (5초 간격)")
