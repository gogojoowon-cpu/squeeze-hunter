"""SQS(Squeeze Score) 점수 계산 — 버그 픽스 + 펀더멘털 + 이상거래"""
import math, random


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def grade(s: float) -> str:
    if s >= 85: return "IMMINENT"
    if s >= 70: return "HIGH"
    if s >= 55: return "WATCH"
    if s >= 40: return "LOW"
    return "NO_SQUEEZE"


def sqs(m: dict) -> dict:
    """v4 점수식 — 버그 픽스 + 옵션 감마 + 펀더멘털 + 이상거래"""
    
    # ━━━ 공매도 SI% (비선형 25점) ━━━
    si_raw = m.get("si_pct", 0)
    si = clamp(si_raw / 30, 0, 1) * 20 + clamp((si_raw - 30) / 100, 0, 1) * 5

    # ━━━ DTC / CTB / Util ━━━
    dtc = clamp(m.get("dtc", 0) / 10, 0, 1) * 10
    ctb = clamp(m.get("ctb", 0) / 50, 0, 1) * 10
    util = clamp(m.get("util", 0) / 100, 0, 1) * 5

    # ━━━ Float (작을수록 점수↑) ━━━
    fs = m.get("float_shares", 0)
    flt = clamp(1 - math.log10(max(fs, 1)) / 8, 0, 1) * 10 if fs > 0 else 0
    rot = clamp(m.get("rotation", 0) / 2, 0, 1) * 8
    spk = clamp((m.get("vol_spike", 1) - 1) / 4, 0, 1) * 5

    # ━━━ ✅ 버그 픽스: dist_52w 부호 반전 ━━━
    # 신고가 근처(dist=0)일수록 점수↑ (스퀴즈는 신고가에서 터짐)
    dist_raw = m.get("dist_52w", 0.5)
    dist = clamp(1 - dist_raw, 0, 1) * 5

    # ━━━ RSI ━━━
    r14 = m.get("rsi14", 50)
    if   30 < r14 <= 50: rsi = 3.0
    elif 50 < r14 <= 60: rsi = 1.0
    elif 60 < r14 <= 70: rsi = 0.0
    else:                rsi = -1.0

    # ━━━ 감마 집중도 (옵션) ━━━
    gam = clamp(m.get("gamma_conc", 0), 0, 1) * 8

    # ━━━ MACD ━━━
    macd_score = 0.0
    if m.get("macd_golden_cross", False):
        macd_score = 5.0
    elif m.get("macd_dead_cross", False):
        macd_score = -3.0
    elif m.get("macd_histogram", 0) > 0:
        macd_score = 2.0

    # ━━━ 매집 신호 (Wyckoff + OBV + CMF) ━━━
    acc_score_raw = m.get("acc_score", 0)
    acc = (acc_score_raw / 100) * 8

    # ━━━ 소셜 (로그) ━━━
    sv = m.get("social_velocity", 0)
    if sv <= 0:
        soc = 0.0
    elif sv <= 500:
        soc = clamp(sv / 500, 0, 1) * 6
    else:
        soc = 6.0 + clamp(math.log10(max(sv / 500, 1)) / math.log10(10), 0, 1) * 2

    sen = max(0, m.get("sentiment", 0)) * 4
    cat = 4.0 if m.get("has_catalyst", False) else 0.0

    # ━━━ 🆕 옵션 - C/P Ratio (콜/풋 비율) ━━━
    # 콜이 풋보다 2배 이상 = 강한 강세 베팅
    cp_ratio = m.get("call_put_ratio", 1.0)
    if cp_ratio >= 3.0:
        cp_score = 4.0
    elif cp_ratio >= 2.0:
        cp_score = 2.5
    elif cp_ratio >= 1.5:
        cp_score = 1.0
    else:
        cp_score = 0.0

    # ━━━ 🆕 비정상 옵션 활동 (Unusual Options Activity) ━━━
    # 거래량/OI 비율이 1 이상 = 새로운 베팅 폭증
    uoa = m.get("unusual_options_score", 0)  # 0~1
    uoa_score = clamp(uoa, 0, 1) * 4

    # ━━━ 🆕 이상 거래 (Z-score 통계적 이상치) ━━━
    # 거래량 Z-score 3 이상 = 99.7% 신뢰구간 벗어남
    vol_z = m.get("vol_zscore", 0)
    if vol_z >= 4:
        anom_score = 5.0
    elif vol_z >= 3:
        anom_score = 3.0
    elif vol_z >= 2:
        anom_score = 1.0
    else:
        anom_score = 0.0

    # ━━━ 🆕 펀더멘털 신호 ━━━
    # 부채/자본 높고 현금 부족 = 공매도 타깃 가능성
    fund_score = 0.0
    debt_eq = m.get("debt_to_equity", 0)
    if debt_eq > 5:
        fund_score += 2.0  # 파산 위험 (공매도 우세)
    cash_runway = m.get("cash_runway_months", 99)
    if 0 < cash_runway < 6:
        fund_score -= 3.0  # 곧 희석 발행 (스퀴즈 깨질 가능성)

    # ━━━ 🆕 어닝 임박 (이벤트) ━━━
    days_to_earnings = m.get("days_to_earnings", 999)
    if 0 <= days_to_earnings <= 7:
        event_score = 4.0   # 어닝 D-7: 변동성 폭발
    elif 0 <= days_to_earnings <= 14:
        event_score = 2.0
    else:
        event_score = 0.0

    # ━━━ 🆕 다크풀 거래량 비율 ━━━
    # 다크풀 50% 이상 = 기관 매집
    dark_pool = m.get("dark_pool_ratio", 0)
    if dark_pool >= 0.6:
        dp_score = 3.0
    elif dark_pool >= 0.5:
        dp_score = 1.5
    else:
        dp_score = 0.0

    # ━━━ 합산 ━━━
    raw = (si + dtc + ctb + util + flt + rot + spk + dist + rsi + gam +
           soc + sen + cat + acc + macd_score +
           cp_score + uoa_score + anom_score +
           fund_score + event_score + dp_score)

    # 페널티
    pen = (10 if m.get("market_cap", 1e9) < 50e6 else 0) + \
          (15 if m.get("has_dilution", False) else 0)

    final = round(clamp(raw - pen, 0, 100), 1)

    return {
        "score": final,
        "grade": grade(final),
        "breakdown": {
            "si_score": round(si, 2), "dtc_score": round(dtc, 2),
            "ctb_score": round(ctb, 2), "util_score": round(util, 2),
            "float_score": round(flt, 2), "rotation_score": round(rot, 2),
            "vol_spike_score": round(spk, 2), "dist_52w_score": round(dist, 2),
            "rsi_score": round(rsi, 2), "gamma_score": round(gam, 2),
            "social_score": round(soc, 2), "sentiment_score": round(sen, 2),
            "catalyst_score": round(cat, 2), "accumulation_score": round(acc, 2),
            "macd_score": round(macd_score, 2),
            # 🆕 신규 지표
            "cp_ratio_score": round(cp_score, 2),
            "uoa_score": round(uoa_score, 2),
            "anomaly_score": round(anom_score, 2),
            "fundamental_score": round(fund_score, 2),
            "event_score": round(event_score, 2),
            "darkpool_score": round(dp_score, 2),
            "penalty": round(pen, 2), "raw_total": round(raw, 2),
        }
    }


def estimate_ctb(si: float, dtc: float) -> tuple[float, float]:
    """SI%+DTC 기반 다변수 추정"""
    base = si * 1.8 + dtc * 3.2
    ctb = round(clamp(base * random.uniform(0.85, 1.15), 0.3, 300), 1)
    util = round(clamp(si * 2.2 + dtc * 1.8, 0, 100), 1)
    return ctb, util
