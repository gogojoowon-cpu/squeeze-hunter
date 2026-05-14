"""
이상거래 탐지 + 알림 트리거
- Z-score 기반 볼륨/가격 이상치
- 감마 스퀴즈 임박 감지
- 어닝/배당/분할 임박 알림
- 등급 변동 알림
"""
import time
from datetime import datetime, timezone, timedelta

from app import state
from app.config import (
    ANOMALY_VOL_Z_THRESHOLD,
    ANOMALY_PRICE_Z_THRESHOLD,
    ALERT_COOLDOWN_SEC,
)

# 알림 쿨다운 추적 (sym + type -> last_time)
_alert_cooldown = {}


def _can_alert(sym, alert_type):
    """쿨다운 체크"""
    key = f"{sym}:{alert_type}"
    now = time.time()
    last = _alert_cooldown.get(key, 0)
    if now - last < ALERT_COOLDOWN_SEC:
        return False
    _alert_cooldown[key] = now
    return True


def _push_alert(sym, alert_type, msg, level="info", data=None):
    """알림 추가"""
    if not _can_alert(sym, alert_type):
        return
    alert = {
        "t": time.time(),
        "symbol": sym,
        "type": alert_type,
        "level": level,
        "msg": msg,
        "data": data or {},
    }
    state.alerts.append(alert)
    # 최대 500개만 유지
    if len(state.alerts) > 500:
        del state.alerts[:-500]


# ============================================================
# 이상거래 탐지
# ============================================================
def detect_anomalies():
    """전체 종목 이상거래 탐지"""
    found = 0
    state.anomalies.clear()

    for sym, m in state.stocks.items():
        if m.get("price", 0) <= 0:
            continue

        anomalies = []

        # 1) 거래량 Z-score
        vol_z = m.get("volume_zscore", 0) or 0
        if abs(vol_z) >= ANOMALY_VOL_Z_THRESHOLD:
            anomalies.append({
                "type": "volume_spike",
                "z": round(vol_z, 2),
                "severity": "critical" if vol_z >= 5 else "high",
            })

        # 2) 가격 변동 Z-score
        price_z = m.get("price_zscore", 0) or 0
        if abs(price_z) >= ANOMALY_PRICE_Z_THRESHOLD:
            anomalies.append({
                "type": "price_spike",
                "z": round(price_z, 2),
                "direction": "up" if price_z > 0 else "down",
                "severity": "critical" if abs(price_z) >= 5 else "high",
            })

        # 3) 이상 옵션 활동
        unusual_opt = m.get("unusual_options_score", 0) or 0
        if unusual_opt >= 70:
            anomalies.append({
                "type": "unusual_options",
                "score": unusual_opt,
                "severity": "high",
            })

        # 4) 감마 집중 임박 (call ratio + 감마 집중)
        gamma_conc = m.get("gamma_concentration", 0) or 0
        cp_ratio = m.get("call_put_ratio", 0) or 0
        if gamma_conc >= 0.75 and cp_ratio >= 2.5:
            anomalies.append({
                "type": "gamma_squeeze_imminent",
                "gamma": round(gamma_conc, 2),
                "cp_ratio": round(cp_ratio, 2),
                "severity": "critical",
            })

        # 5) Dark Pool 비율 이상 (60% 이상)
        dp = m.get("dark_pool_ratio", 0) or 0
        if dp >= 0.6:
            anomalies.append({
                "type": "dark_pool_heavy",
                "ratio": round(dp, 2),
                "severity": "high" if dp >= 0.7 else "info",
            })

        if anomalies:
            state.anomalies[sym] = {
                "t": time.time(),
                "price": m.get("price"),
                "score": m.get("sqs_score"),
                "anomalies": anomalies,
            }
            found += 1

            # 알림 트리거 (critical 만)
            for a in anomalies:
                if a.get("severity") == "critical":
                    _push_alert(
                        sym,
                        a["type"],
                        f"⚠️ {sym} {a['type']} 감지 (점수 {m.get('sqs_score',0):.1f})",
                        level="critical",
                        data=a,
                    )

    if found > 0:
        print(f"⚠️ 이상거래 {found}개 종목 탐지")


# ============================================================
# 이벤트/등급 변동 알림
# ============================================================
_last_grades = {}  # sym -> grade


def check_event_alerts():
    """등급 상승, 어닝/배당 임박 등 알림"""
    now = datetime.now(timezone.utc)

    for sym, m in state.stocks.items():
        if m.get("price", 0) <= 0:
            continue

        score = m.get("sqs_score", 0) or 0
        cur_grade = m.get("grade", "")

        # 1) 등급 IMMINENT/HIGH 진입
        prev_grade = _last_grades.get(sym, "")
        if cur_grade in ("IMMINENT", "HIGH") and prev_grade not in ("IMMINENT", "HIGH"):
            _push_alert(
                sym,
                "grade_up",
                f"🚀 {sym} 등급 상승: {prev_grade or 'NEW'} → {cur_grade} (점수 {score:.1f})",
                level="high",
                data={"from": prev_grade, "to": cur_grade, "score": score},
            )
        _last_grades[sym] = cur_grade

        # 2) 점수 80 이상 진입
        if score >= 80 and m.get("_alerted_80") != True:
            _push_alert(
                sym,
                "score_80",
                f"🔥 {sym} 점수 80 돌파 ({score:.1f})",
                level="critical",
                data={"score": score},
            )
            m["_alerted_80"] = True
        elif score < 75:
            m["_alerted_80"] = False

        # 3) 어닝 임박 (3일 이내)
        earnings = m.get("earnings_date")
        if earnings:
            try:
                edt = datetime.fromisoformat(earnings.replace("Z", "+00:00"))
                days = (edt - now).days
                if 0 <= days <= 3:
                    _push_alert(
                        sym,
                        "earnings_soon",
                        f"📅 {sym} 어닝 {days}일 후 ({earnings[:10]})",
                        level="info",
                        data={"date": earnings, "days": days},
                    )
            except Exception:
                pass

        # 4) 배당락 임박
        div = m.get("upcoming_dividend")
        if div and div.get("ex_date"):
            try:
                edt = datetime.fromisoformat(div["ex_date"]).replace(tzinfo=timezone.utc)
                days = (edt - now).days
                if 0 <= days <= 2:
                    _push_alert(
                        sym,
                        "dividend_soon",
                        f"💰 {sym} 배당락 {days}일 후",
                        level="info",
                        data=div,
                    )
            except Exception:
                pass

        # 5) 분할 임박
        split = m.get("upcoming_split")
        if split and split.get("execution_date"):
            try:
                edt = datetime.fromisoformat(split["execution_date"]).replace(tzinfo=timezone.utc)
                days = (edt - now).days
                if 0 <= days <= 5:
                    _push_alert(
                        sym,
                        "split_soon",
                        f"✂️ {sym} 분할 {days}일 후 ({split.get('split_from')}:{split.get('split_to')})",
                        level="high",
                        data=split,
                    )
            except Exception:
                pass

        # 6) 매집 신호 STRONG 진입
        acc = m.get("acc_score", 0) or 0
        if acc >= 75 and not m.get("_alerted_acc"):
            _push_alert(
                sym,
                "accumulation_strong",
                f"📈 {sym} 매집 STRONG ({acc:.0f}점) - {', '.join(m.get('acc_signals',[])[:2])}",
                level="high",
                data={"acc_score": acc, "signals": m.get("acc_signals", [])},
            )
            m["_alerted_acc"] = True
        elif acc < 60:
            m["_alerted_acc"] = False
