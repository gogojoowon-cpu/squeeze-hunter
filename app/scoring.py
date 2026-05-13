"""SQS(Squeeze Score) 점수 계산"""
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
    """v2 점수식 — 10가지 개선 반영"""
    si_raw = m.get("si_pct", 0)
    si = clamp(si_raw / 30, 0, 1) * 20 + clamp((si_raw - 30) / 100, 0, 1) * 5

    dtc = clamp(m.get("dtc", 0) / 10, 0, 1) * 10
    ctb = clamp(m.get("ctb", 0) / 50, 0, 1) * 10
    util = clamp(m.get("util", 0) / 100, 0, 1) * 5

    fs = m.get("float_shares", 0)
    flt = clamp(1 - math.log10(max(fs, 1)) / 8, 0, 1) * 10 if fs > 0 else 0
    rot = clamp(m.get("rotation", 0) / 2, 0, 1) * 8
    spk = clamp((m.get("vol_spike", 1) - 1) / 4, 0, 1) * 5
    dist = clamp(m.get("dist_52w", 0.5), 0, 1) * 5

    r14 = m.get("rsi14", 50)
    if   30 < r14 <= 50: rsi = 3.0
    elif 50 < r14 <= 60: rsi = 1.0
    elif 60 < r14 <= 70: rsi = 0.0
    else:                rsi = -1.0

    gam = clamp(m.get("gamma_conc", 0), 0, 1) * 8

    # MACD
    macd_score = 0.0
    if m.get("macd_golden_cross", False):
        macd_score = 5.0
    elif m.get("macd_dead_cross", False):
        macd_score = -3.0
    elif m.get("macd_histogram", 0) > 0:
        macd_score = 2.0

    # 매집 신호
    vs = m.get("vol_spike", 1)
    pc = abs(m.get("change_pct", 0))
    if vs >= 3 and pc <= 3:
        acc = clamp((vs - 3) / 7, 0, 1) * 6
    elif vs >= 2 and pc <= 2:
        acc = clamp((vs - 2) / 8, 0, 1) * 3
    else:
        acc = 0.0

    # 소셜 속도 (로그 스케일)
    sv = m.get("social_velocity", 0)
    if sv <= 0:
        soc = 0.0
    elif sv <= 500:
        soc = clamp(sv / 500, 0, 1) * 6
    else:
        soc = 6.0 + clamp(math.log10(max(sv / 500, 1)) / math.log10(10), 0, 1) * 2

    sen = max(0, m.get("sentiment", 0)) * 4
    cat = 4.0 if m.get("has_catalyst", False) else 0.0

    raw = si + dtc + ctb + util + flt + rot + spk + dist + rsi + gam + soc + sen + cat + acc + macd_score
    pen = (10 if m.get("market_cap", 1e9) < 50e6 else 0) + (15 if m.get("has_dilution", False) else 0)
    final = round(clamp(raw - pen, 0, 100), 1)

    return {
        "score": final, "grade": grade(final),
        "breakdown": {
            "si_score": round(si, 2), "dtc_score": round(dtc, 2),
            "ctb_score": round(ctb, 2), "util_score": round(util, 2),
            "float_score": round(flt, 2), "rotation_score": round(rot, 2),
            "vol_spike_score": round(spk, 2), "dist_52w_score": round(dist, 2),
            "rsi_score": round(rsi, 2), "gamma_score": round(gam, 2),
            "social_score": round(soc, 2), "sentiment_score": round(sen, 2),
            "catalyst_score": round(cat, 2), "accumulation_score": round(acc, 2),
            "macd_score": round(macd_score, 2),
            "penalty": round(pen, 2), "raw_total": round(raw, 2),
        }
    }


def estimate_ctb(si: float, dtc: float) -> tuple[float, float]:
    """SI%+DTC 기반 다변수 추정"""
    base = si * 1.8 + dtc * 3.2
    ctb = round(clamp(base * random.uniform(0.85, 1.15), 0.3, 300), 1)
    util = round(clamp(si * 2.2 + dtc * 1.8, 0, 100), 1)
    return ctb, util
