"""SQS(Squeeze Score) 점수 계산 — 매집 구간 선호 + 추격매수 방지

v5 핵심 변경:
- dist_52w 부호 원복: 52주 저점~중간 구간(매집 구간)에 가산점
- 신고가 근처(>70% 도달) 페널티
- vol_spike 가중치 5점 → 12점 (스퀴즈 핵심 트리거)
- acc_score 가중치 8점 → 12점 (매집 = 스퀴즈 전조)
- change_pct 페널티 추가: 당일 +10% 이상 추격매수 방지
- 횡보 보너스: RSI 40~55 + 저변동성 = 매집 구간 가산점
- estimate_ctb 랜덤 제거: 일관된 추정값
"""
import math


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def grade(s: float) -> str:
    if s >= 85: return "IMMINENT"
    if s >= 70: return "HIGH"
    if s >= 55: return "WATCH"
    if s >= 40: return "LOW"
    return "NO_SQUEEZE"


def sqs(m: dict) -> dict:
    """v5 점수식 — 매집 구간 선호 + 추격매수 방지"""

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

    # ━━━ ✅ v5: 거래량 급증 (5점 → 12점, 스퀴즈 핵심 트리거) ━━━
    # vol_spike 1.0 = 평균, 2.0 = 2배, 5.0 = 5배
    vs_raw = m.get("vol_spike", 1)
    if vs_raw >= 5.0:
        spk = 12.0
    elif vs_raw >= 3.0:
        spk = 9.0 + (vs_raw - 3.0) / 2.0 * 3.0  # 3~5배: 9~12점
    elif vs_raw >= 2.0:
        spk = 5.0 + (vs_raw - 2.0) * 4.0  # 2~3배: 5~9점
    elif vs_raw >= 1.5:
        spk = 2.0 + (vs_raw - 1.5) * 6.0  # 1.5~2배: 2~5점
    else:
        spk = 0.0

    # ━━━ ✅ v5: dist_52w 매집 구간 선호 (부호 원복) ━━━
    # dist_raw = 52주 저가 대비 현재 위치 (0=저가, 1=고가)
    # 0~30%  : 깊은 저점 (매집 의심 → 강한 보너스)
    # 30~60% : 매집 구간 (이상적 → 만점)
    # 60~70% : 중립
    # 70~100%: 이미 상승 (페널티)
    dist_raw = m.get("dist_52w", 0.5)
    if dist_raw <= 0.30:
        dist = 6.0  # 깊은 저점 + 매집 신호 좋음
    elif dist_raw <= 0.60:
        dist = 8.0  # 매집 구간 (Sweet Spot)
    elif dist_raw <= 0.70:
        dist = 4.0
    elif dist_raw <= 0.85:
        dist = 0.0
    else:
        dist = -3.0  # 신고가 근처 = 이미 늦음

    # ━━━ RSI (매집 구간 선호 강화) ━━━
    r14 = m.get("rsi14", 50)
    if   30 <= r14 <= 45: rsi = 4.0   # 과매도~매집 (이상적)
    elif 45 <  r14 <= 55: rsi = 3.0   # 횡보 매집
    elif 55 <  r14 <= 65: rsi = 1.0   # 초기 상승
    elif 65 <  r14 <= 75: rsi = -1.0  # 과열 시작
    elif r14 > 75:        rsi = -3.0  # 명백한 과매수 (추격매수 위험)
    elif r14 < 30:        rsi = 2.0   # 극단 과매도
    else:                 rsi = 0.0

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

    # ━━━ ✅ v5: 매집 신호 (8점 → 12점, 핵심 가중치) ━━━
    acc_score_raw = m.get("acc_score", 0)
    acc = (acc_score_raw / 100) * 12

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

    # ━━━ 옵션 - C/P Ratio (콜/풋 비율) ━━━
    cp_ratio = m.get("call_put_ratio", 1.0)
    if cp_ratio >= 3.0:
        cp_score = 4.0
    elif cp_ratio >= 2.0:
        cp_score = 2.5
    elif cp_ratio >= 1.5:
        cp_score = 1.0
    else:
        cp_score = 0.0

    # ━━━ 비정상 옵션 활동 (Unusual Options Activity) ━━━
    uoa = m.get("unusual_options_score", 0)
    # unusual_options_score는 0~100 (polygon.py에서 그렇게 반환) 또는 0~1 둘 다 대응
    if uoa > 1:
        uoa_norm = uoa / 100.0
    else:
        uoa_norm = uoa
    uoa_score = clamp(uoa_norm, 0, 1) * 4

    # ━━━ 이상 거래 (Z-score 통계적 이상치) ━━━
    vol_z = m.get("vol_zscore", 0)
    if vol_z >= 4:
        anom_score = 5.0
    elif vol_z >= 3:
        anom_score = 3.0
    elif vol_z >= 2:
        anom_score = 1.0
    else:
        anom_score = 0.0

    # ━━━ 펀더멘털 신호 ━━━
    fund_score = 0.0
    debt_eq = m.get("debt_to_equity", 0)
    if debt_eq > 5:
        fund_score += 2.0
    cash_runway = m.get("cash_runway_months", 99)
    if 0 < cash_runway < 6:
        fund_score -= 3.0

    # ━━━ 어닝 임박 (이벤트) ━━━
    days_to_earnings = m.get("days_to_earnings", 999)
    if 0 <= days_to_earnings <= 7:
        event_score = 4.0
    elif 0 <= days_to_earnings <= 14:
        event_score = 2.0
    else:
        event_score = 0.0

    # ━━━ 다크풀 거래량 비율 (기관 매집) ━━━
    dark_pool = m.get("dark_pool_ratio", 0)
    if dark_pool >= 0.6:
        dp_score = 4.0
    elif dark_pool >= 0.5:
        dp_score = 2.5
    elif dark_pool >= 0.4:
        dp_score = 1.0
    else:
        dp_score = 0.0

    # ━━━ 🆕 v5: 횡보 매집 보너스 ━━━
    # RSI 40~55 + 저변동성(당일 ±3% 이내) + dist_52w 0.2~0.6
    # = "조용히 매집 중인 종목" 가산점
    change_pct = m.get("change_pct", 0)
    consolidation_bonus = 0.0
    if (40 <= r14 <= 55 and
        abs(change_pct) <= 3.0 and
        0.20 <= dist_raw <= 0.60):
        consolidation_bonus = 5.0
        # 거래량까지 살짝 늘어나는 중이면 추가 보너스
        if vs_raw >= 1.3:
            consolidation_bonus += 2.0  # 최대 7점

    # ━━━ 🆕 v5: 추격매수 페널티 ━━━
    # 당일 이미 +10% 이상 오른 종목은 점수 깎기
    chase_penalty = 0.0
    if change_pct >= 30:
        chase_penalty = 25.0  # +30% 이상: 거의 제외
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

    # 기존 페널티
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
            # 🆕 신규 지표
            "consolidation_bonus": round(consolidation_bonus, 2),
            "chase_penalty": round(chase_penalty, 2),
            "penalty": round(pen, 2), "raw_total": round(raw, 2),
        }
    }


def estimate_ctb(si: float, dtc: float) -> tuple[float, float]:
    """SI%+DTC 기반 결정론적 추정 (랜덤 제거 → 일관성 확보)

    실제 CTB(Cost To Borrow)는 폐쇄적 데이터라 정확히 구할 수 없음.
    SI%와 DTC가 높을수록 차입 수요가 높아 CTB도 비례해서 상승하는
    경험적 공식을 사용.
    """
    if si <= 0 and dtc <= 0:
        return 0.0, 0.0

    # CTB 추정: SI% × 1.8 + DTC × 3.2 (경험적 공식)
    ctb = round(clamp(si * 1.8 + dtc * 3.2, 0.3, 300), 1)

    # 차입 가능 주식 사용률 추정
    util = round(clamp(si * 2.2 + dtc * 1.8, 0, 100), 1)

    return ctb, util
