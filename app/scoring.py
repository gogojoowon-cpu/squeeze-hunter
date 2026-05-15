"""SQS(Squeeze Score) 점수 계산 — v6

v6 핵심 변경 (옵션 권한 없는 Polygon Starter 환경 최적화):
- 옵션 관련 점수(감마/CP/UOA) 가중치 대폭 축소 (16점 → 4점)
- 다크풀(매집 신호)/거래량 스파이크 가중치 강화
- 매집(acc_score) 가중치 12점 → 18점 (핵심 신호로 격상)
- SI%, 거래량 폭증, 매집 3개를 메인 축으로 재구성
- 데이터 결손에 강한 가산점 구조 (대부분 종목이 50~70점 도달 가능)
- 추격매수 페널티 유지 / 매집 횡보 보너스 강화

만점 구조 (총 ≈ 125점, 100점 캡):
  공매도(SI/DTC/CTB/Util): 50점
  유동/거래(Float/Rot/Spike/Dist): 38점
  매집/기술(Acc/RSI/MACD):  28점 + 횡보 보너스 7점
  소셜/뉴스(Soc/Sen/Cat):   16점
  옵션(Gam/CP/UOA):         4점  (데이터 들어오면 보너스)
  이상거래(Z/DP/Event):     16점
  펀더멘털:                 2점
"""
import math


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def grade(s: float) -> str:
    if s >= 80: return "IMMINENT"
    if s >= 65: return "HIGH"
    if s >= 50: return "WATCH"
    if s >= 35: return "LOW"
    return "NO_SQUEEZE"


def sqs(m: dict) -> dict:
    """v6 점수식 — 옵션 없는 환경 최적화 + 매집 구간 선호"""

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

    # ━━━ 거래량 급증 (스퀴즈 핵심 트리거, 최대 12점) ━━━
    vs_raw = m.get("vol_spike", 1)
    if vs_raw >= 5.0:
        spk = 12.0
    elif vs_raw >= 3.0:
        spk = 9.0 + (vs_raw - 3.0) / 2.0 * 3.0
    elif vs_raw >= 2.0:
        spk = 5.0 + (vs_raw - 2.0) * 4.0
    elif vs_raw >= 1.5:
        spk = 2.0 + (vs_raw - 1.5) * 6.0
    elif vs_raw >= 1.2:
        spk = (vs_raw - 1.2) / 0.3 * 2.0
    else:
        spk = 0.0

    # ━━━ dist_52w 매집 구간 선호 ━━━
    dist_raw = m.get("dist_52w", 0.5)
    if dist_raw <= 0.30:
        dist = 6.0
    elif dist_raw <= 0.60:
        dist = 8.0
    elif dist_raw <= 0.70:
        dist = 4.0
    elif dist_raw <= 0.85:
        dist = 0.0
    else:
        dist = -3.0

    # ━━━ RSI ━━━
    r14 = m.get("rsi14", 50)
    if   30 <= r14 <= 45: rsi = 4.0
    elif 45 <  r14 <= 55: rsi = 3.0
    elif 55 <  r14 <= 65: rsi = 1.0
    elif 65 <  r14 <= 75: rsi = -1.0
    elif r14 > 75:        rsi = -3.0
    elif r14 < 30:        rsi = 2.0
    else:                 rsi = 0.0

    # ━━━ ⭐ v6: 매집 신호 12점 → 18점 (핵심 신호로 격상) ━━━
    # acc_score는 0~100 (Wyckoff + OBV + CMF 합산)
    acc_score_raw = m.get("acc_score", 0)
    acc = (acc_score_raw / 100) * 18

    # ━━━ MACD ━━━
    macd_score = 0.0
    if m.get("macd_golden_cross", False):
        macd_score = 5.0
    elif m.get("macd_dead_cross", False):
        macd_score = -3.0
    elif m.get("macd_histogram", 0) > 0:
        macd_score = 2.0

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

    # ━━━ ⭐ v6: 옵션 관련 대폭 축소 (16점 → 4점) ━━━
    # Polygon Options 권한 없는 환경에서 영구 0이므로 점수 비중 최소화
    # 데이터 있으면 보너스로 작용
    gam = clamp(m.get("gamma_conc", 0), 0, 1) * 2  # 8 → 2

    cp_ratio = m.get("call_put_ratio", 1.0)
    if cp_ratio >= 3.0:
        cp_score = 1.0
    elif cp_ratio >= 2.0:
        cp_score = 0.5
    else:
        cp_score = 0.0

    uoa = m.get("unusual_options_score", 0)
    uoa_norm = uoa / 100.0 if uoa > 1 else uoa
    uoa_score = clamp(uoa_norm, 0, 1) * 1  # 4 → 1

    # ━━━ ⭐ v6: 다크풀 강화 (4점 → 8점, 기관 매집 신호) ━━━
    dark_pool = m.get("dark_pool_ratio", 0)
    if dark_pool >= 0.6:
        dp_score = 8.0
    elif dark_pool >= 0.5:
        dp_score = 5.0
    elif dark_pool >= 0.4:
        dp_score = 3.0
    elif dark_pool >= 0.3:
        dp_score = 1.0
    else:
        dp_score = 0.0

    # ━━━ 이상 거래 Z-score ━━━
    vol_z = m.get("vol_zscore", 0)
    if vol_z >= 4:
        anom_score = 5.0
    elif vol_z >= 3:
        anom_score = 3.0
    elif vol_z >= 2:
        anom_score = 1.0
    else:
        anom_score = 0.0

    # ━━━ 펀더멘털 ━━━
    fund_score = 0.0
    debt_eq = m.get("debt_to_equity", 0)
    if debt_eq > 5:
        fund_score += 2.0
    cash_runway = m.get("cash_runway_months", 99)
    if 0 < cash_runway < 6:
        fund_score -= 3.0

    # ━━━ 어닝 임박 ━━━
    days_to_earnings = m.get("days_to_earnings", 999)
    if 0 <= days_to_earnings <= 7:
        event_score = 4.0
    elif 0 <= days_to_earnings <= 14:
        event_score = 2.0
    else:
        event_score = 0.0

    # ━━━ ⭐ v6: 횡보 매집 보너스 강화 (최대 7점 → 10점) ━━━
    change_pct = m.get("change_pct", 0)
    consolidation_bonus = 0.0
    if (40 <= r14 <= 55 and
        abs(change_pct) <= 3.0 and
        0.20 <= dist_raw <= 0.60):
        consolidation_bonus = 6.0
        if vs_raw >= 1.3:
            consolidation_bonus += 2.0
        if acc_score_raw >= 50:  # 매집 점수도 높으면 추가 보너스
            consolidation_bonus += 2.0

    # ━━━ 추격매수 페널티 ━━━
    chase_penalty = 0.0
    if change_pct >= 30:
        chase_penalty = 25.0
    elif change_pct >= 20:
        chase_penalty = 15.0
    elif change_pct >= 15:
        chase_penalty = 10.0
    elif change_pct >= 10:
        chase_penalty = 5.0
    elif change_pct >= 7:
        chase_penalty = 2.0

    # ━━━ 합산 ━━━
    raw = (si + dtc + ctb + util + flt + rot + spk + dist + rsi + gam +
           soc + sen + cat + acc + macd_score +
           cp_score + uoa_score + anom_score +
           fund_score + event_score + dp_score +
           consolidation_bonus)

    pen = (10 if m.get("market_cap", 1e9) < 50e6 else 0) + \
          (15 if m.get("has_dilution", False) else 0) + \
          chase_penalty

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
            "cp_ratio_score": round(cp_score, 2),
            "uoa_score": round(uoa_score, 2),
            "anomaly_score": round(anom_score, 2),
            "fundamental_score": round(fund_score, 2),
            "event_score": round(event_score, 2),
            "darkpool_score": round(dp_score, 2),
            "consolidation_bonus": round(consolidation_bonus, 2),
            "chase_penalty": round(chase_penalty, 2),
            "penalty": round(pen, 2), "raw_total": round(raw, 2),
        }
    }


def estimate_ctb(si: float, dtc: float) -> tuple[float, float]:
    """SI%+DTC 기반 결정론적 추정 (랜덤 제거 → 일관성 확보)"""
    if si <= 0 and dtc <= 0:
        return 0.0, 0.0
    ctb = round(clamp(si * 1.8 + dtc * 3.2, 0.3, 300), 1)
    util = round(clamp(si * 2.2 + dtc * 1.8, 0, 100), 1)
    return ctb, util
