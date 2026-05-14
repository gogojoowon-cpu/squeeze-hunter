"""
FastAPI 라우트 정의
- REST API (점수, 테마, 이상거래, 이벤트, 옵션, 펀더멘털)
- WebSocket 실시간 푸시 (/ws/scores)
- HTML 메인 페이지 (/)
"""
import asyncio
import json
import time
import random
from datetime import datetime, timezone, timedelta

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse

from app import state
from app.scoring import sqs
from app.web.ui import HTML_PAGE


# ============================================================
# WebSocket 클라이언트 관리
# ============================================================
_clients: set = set()
_clients_lock = asyncio.Lock()


async def _add_client(ws: WebSocket):
    async with _clients_lock:
        _clients.add(ws)


async def _remove_client(ws: WebSocket):
    async with _clients_lock:
        _clients.discard(ws)


async def broadcast(payload: dict):
    """모든 연결된 클라이언트에 전송"""
    if not _clients:
        return
    msg = json.dumps(payload, default=str)
    dead = []
    async with _clients_lock:
        targets = list(_clients)
    for ws in targets:
        try:
            await ws.send_text(msg)
        except Exception:
            dead.append(ws)
    if dead:
        async with _clients_lock:
            for ws in dead:
                _clients.discard(ws)


async def push_loop():
    """4초마다 상위/변동 종목 푸시 + 25초마다 heartbeat"""
    await asyncio.sleep(8)
    last_hb = time.time()
    while True:
        try:
            if state.ready and _clients:
                # 점수 상위 + 최근 변동 종목 우선
                items = []
                top = sorted(
                    state.stocks.items(),
                    key=lambda x: -(x[1].get("sqs_score", 0) or 0),
                )[:50]
                # + 랜덤 샘플 30개
                rest = [s for s in state.stocks.keys() if s not in dict(top)]
                sample = random.sample(rest, min(30, len(rest))) if rest else []

                for sym, m in top:
                    items.append(_row(sym, m))
                for sym in sample:
                    m = state.stocks.get(sym, {})
                    if m.get("price", 0) > 0:
                        items.append(_row(sym, m))

                await broadcast({"type": "update", "items": items, "t": time.time()})

            # heartbeat (25초)
            if time.time() - last_hb > 25:
                await broadcast({"type": "ping", "t": time.time()})
                last_hb = time.time()

        except Exception as e:
            print(f"⚠️ push_loop 오류: {e}")
        await asyncio.sleep(4)


# ============================================================
# 행 빌더
# ============================================================
def _row(sym: str, m: dict) -> dict:
    """스냅샷/푸시용 표준 행"""
    return {
        "symbol": sym,
        "name": m.get("name", ""),
        "theme": m.get("theme", ""),
        "price": m.get("price", 0),
        "change_pct": m.get("change_pct", 0),
        "volume": m.get("volume", 0),
        "market_cap": m.get("market_cap", 0),
        "si_pct": m.get("si_pct", 0),
        "ctb": m.get("ctb", 0),
        "dtc": m.get("dtc", 0),
        "util": m.get("util", 0),
        "float_shares": m.get("float_shares", 0),
        "rotation": m.get("rotation", 0),
        "rsi14": m.get("rsi14", 50),
        "macd_histogram": m.get("macd_histogram", 0),
        "has_catalyst": m.get("has_catalyst", False),
        "social_velocity": m.get("social_velocity", 0),
        "acc_score": m.get("acc_score", 0),
        "acc_signals": m.get("acc_signals", []),
        "gamma_concentration": m.get("gamma_concentration", 0),
        "call_put_ratio": m.get("call_put_ratio", 0),
        "dark_pool_ratio": m.get("dark_pool_ratio", 0),
        "volume_zscore": m.get("volume_zscore", 0),
        "price_zscore": m.get("price_zscore", 0),
        "sqs_score": m.get("sqs_score", 0),
        "grade": m.get("grade", ""),
    }


# ============================================================
# 라우트 등록
# ============================================================
def register_routes(app: FastAPI):

    # ----------------------------------------------------------
    # 메인 페이지
    # ----------------------------------------------------------
    @app.get("/", response_class=HTMLResponse)
    def index():
        return HTMLResponse(content=HTML_PAGE)

    # ----------------------------------------------------------
    # 초기 스냅샷 (페이지 로드 시 1회)
    # ----------------------------------------------------------
    @app.get("/api/snapshot")
    def snapshot(limit: int = 500):
        items = []
        for sym, m in state.stocks.items():
            if m.get("price", 0) <= 0:
                continue
            items.append(_row(sym, m))
        items.sort(key=lambda x: -(x.get("sqs_score") or 0))
        return {
            "ready": state.ready,
            "total": len(state.stocks),
            "loaded": len(items),
            "items": items[:limit],
            "t": time.time(),
        }

    # ----------------------------------------------------------
    # 상위 점수
    # ----------------------------------------------------------
    @app.get("/api/scores/top")
    def top_scores(limit: int = 100, min_score: float = 0, grade: str = ""):
        items = []
        for sym, m in state.stocks.items():
            s = m.get("sqs_score", 0) or 0
            if s < min_score:
                continue
            if grade and m.get("grade") != grade:
                continue
            if m.get("price", 0) <= 0:
                continue
            items.append(_row(sym, m))
        items.sort(key=lambda x: -(x.get("sqs_score") or 0))
        return {"count": len(items), "items": items[:limit]}

    # ----------------------------------------------------------
    # 점수 히스토리
    # ----------------------------------------------------------
    @app.get("/api/scores/{symbol}/history")
    def score_history(symbol: str, limit: int = 100):
        sym = symbol.upper()
        hist = state.history.get(sym, [])
        return {"symbol": sym, "items": hist[-limit:]}

    # ----------------------------------------------------------
    # 점수 세부 (breakdown)
    # ----------------------------------------------------------
    @app.get("/api/scores/{symbol}/breakdown")
    def score_breakdown(symbol: str):
        sym = symbol.upper()
        m = state.stocks.get(sym)
        if not m:
            return {"error": "not found"}
        # 최신 계산
        r = sqs(m)
        return {
            "symbol": sym,
            "name": m.get("name", ""),
            "price": m.get("price", 0),
            "score": r["score"],
            "grade": r["grade"],
            "breakdown": r["breakdown"],
            "metrics": {
                "si_pct": m.get("si_pct", 0),
                "ctb": m.get("ctb", 0),
                "dtc": m.get("dtc", 0),
                "util": m.get("util", 0),
                "float_shares": m.get("float_shares", 0),
                "rotation": m.get("rotation", 0),
                "vol_spike": m.get("vol_spike", 0),
                "dist_52w": m.get("dist_52w", 0),
                "rsi14": m.get("rsi14", 50),
                "social_velocity": m.get("social_velocity", 0),
                "has_catalyst": m.get("has_catalyst", False),
                "macd_histogram": m.get("macd_histogram", 0),
                "acc_score": m.get("acc_score", 0),
            },
        }

    # ----------------------------------------------------------
    # 테마별 그룹
    # ----------------------------------------------------------
    @app.get("/api/themes")
    def themes():
        groups = {}
        for sym, m in state.stocks.items():
            if m.get("price", 0) <= 0:
                continue
            theme = m.get("theme") or "기타"
            groups.setdefault(theme, []).append(_row(sym, m))
        result = []
        for theme, items in groups.items():
            items.sort(key=lambda x: -(x.get("sqs_score") or 0))
            avg = sum((x.get("sqs_score") or 0) for x in items) / max(len(items), 1)
            result.append({
                "theme": theme,
                "count": len(items),
                "avg_score": round(avg, 2),
                "top": items[:10],
            })
        result.sort(key=lambda x: -x["avg_score"])
        return {"themes": result}

    # ----------------------------------------------------------
    # 매집 신호
    # ----------------------------------------------------------
    @app.get("/api/accumulation")
    def accumulation(limit: int = 100, min_score: float = 40):
        items = []
        for sym, m in state.stocks.items():
            acc = m.get("acc_score", 0) or 0
            if acc < min_score:
                continue
            if m.get("price", 0) <= 0:
                continue
            # 시총 100억 달러 이상 제외 (대형주는 매집 의미 약함)
            if (m.get("market_cap", 0) or 0) > 10_000_000_000:
                continue

            tier = "WEAK"
            if acc >= 75:
                tier = "STRONG"
            elif acc >= 60:
                tier = "ACTIVE"
            elif acc >= 45:
                tier = "EMERGING"

            items.append({
                **_row(sym, m),
                "acc_score": acc,
                "acc_signals": m.get("acc_signals", []),
                "acc_summary": " | ".join(m.get("acc_signals", [])[:3]),
                "tier": tier,
                "obv_slope": m.get("obv_slope", 0),
                "cmf": m.get("cmf", 0),
                "vol_spike_days": m.get("vol_spike_days", 0),
                "price_stability": m.get("price_stability", 0),
                "acc_candles": m.get("acc_candles", 0),
                "dist_candles": m.get("dist_candles", 0),
                "acc_ratio": m.get("acc_ratio", 0),
                "near_support": m.get("near_support", False),
                "spring_recovery": m.get("spring_recovery", False),
            })
        items.sort(key=lambda x: -x["acc_score"])
        return {"count": len(items), "items": items[:limit]}

    # ----------------------------------------------------------
    # 뉴스
    # ----------------------------------------------------------
    @app.get("/api/news/{symbol}")
    def news(symbol: str, limit: int = 10):
        sym = symbol.upper()
        m = state.stocks.get(sym, {})
        return {
            "symbol": sym,
            "has_catalyst": m.get("has_catalyst", False),
            "sentiment": m.get("sentiment", 0),
            "news": (m.get("news") or [])[:limit],
        }

    # ----------------------------------------------------------
    # 시장 상태
    # ----------------------------------------------------------
    @app.get("/api/market")
    def market():
        from app.market import is_market_open
        return {
            "is_open": is_market_open(),
            "t": time.time(),
            "ready": state.ready,
            "loaded": len(state.stocks),
        }

    # ----------------------------------------------------------
    # 이상거래 탐지 결과
    # ----------------------------------------------------------
    @app.get("/api/anomalies")
    def get_anomalies(limit: int = 50, severity: str = ""):
        items = []
        for sym, d in state.anomalies.items():
            m = state.stocks.get(sym, {})
            for a in d.get("anomalies", []):
                if severity and a.get("severity") != severity:
                    continue
                items.append({
                    "symbol": sym,
                    "name": m.get("name", ""),
                    "price": m.get("price", 0),
                    "change_pct": m.get("change_pct", 0),
                    "volume": m.get("volume", 0),
                    "sqs_score": m.get("sqs_score", 0),
                    "grade": m.get("grade", ""),
                    "anomaly_type": a.get("type"),
                    "severity": a.get("severity"),
                    "data": a,
                    "detected_at": d.get("t"),
                })
        sev_order = {"critical": 0, "high": 1, "info": 2}
        items.sort(key=lambda x: (sev_order.get(x["severity"], 9), -x["sqs_score"]))
        return {"count": len(items), "items": items[:limit]}

    # ----------------------------------------------------------
    # 다가오는 기업 이벤트 (어닝/배당/분할)
    # ----------------------------------------------------------
    @app.get("/api/events")
    def get_events(days: int = 7):
        now = datetime.now(timezone.utc)
        horizon = now + timedelta(days=days)
        earnings, dividends, splits = [], [], []

        for sym, m in state.stocks.items():
            if m.get("price", 0) <= 0:
                continue
            base = {
                "symbol": sym,
                "name": m.get("name", ""),
                "price": m.get("price", 0),
                "sqs_score": m.get("sqs_score", 0),
                "grade": m.get("grade", ""),
            }

            # 어닝
            edate = m.get("earnings_date")
            if edate:
                try:
                    dt = datetime.fromisoformat(edate.replace("Z", "+00:00"))
                    if now <= dt <= horizon:
                        earnings.append({**base, "date": edate, "days": (dt - now).days})
                except Exception:
                    pass

            # 배당
            div = m.get("upcoming_dividend") or {}
            if div.get("ex_date"):
                try:
                    dt = datetime.fromisoformat(div["ex_date"]).replace(tzinfo=timezone.utc)
                    if now <= dt <= horizon:
                        dividends.append({
                            **base,
                            "ex_date": div["ex_date"],
                            "amount": div.get("cash_amount", 0),
                            "days": (dt - now).days,
                        })
                except Exception:
                    pass

            # 분할
            sp = m.get("upcoming_split") or {}
            if sp.get("execution_date"):
                try:
                    dt = datetime.fromisoformat(sp["execution_date"]).replace(tzinfo=timezone.utc)
                    if now <= dt <= horizon:
                        splits.append({
                            **base,
                            "date": sp["execution_date"],
                            "ratio": f"{sp.get('split_from','?')}:{sp.get('split_to','?')}",
                            "days": (dt - now).days,
                        })
                except Exception:
                    pass

        earnings.sort(key=lambda x: x["days"])
        dividends.sort(key=lambda x: x["days"])
        splits.sort(key=lambda x: x["days"])
        return {
            "earnings": earnings,
            "dividends": dividends,
            "splits": splits,
            "total": len(earnings) + len(dividends) + len(splits),
        }

    # ----------------------------------------------------------
    # 옵션 체인 상세
    # ----------------------------------------------------------
    @app.get("/api/options/{symbol}")
    def get_options(symbol: str):
        sym = symbol.upper()
        m = state.stocks.get(sym)
        if not m:
            return {"error": "not found"}
        return {
            "symbol": sym,
            "name": m.get("name", ""),
            "price": m.get("price", 0),
            "gamma_concentration": m.get("gamma_concentration", 0),
            "call_put_ratio": m.get("call_put_ratio", 0),
            "unusual_options_score": m.get("unusual_options_score", 0),
            "max_pain": m.get("max_pain", 0),
            "total_call_oi": m.get("total_call_oi", 0),
            "total_put_oi": m.get("total_put_oi", 0),
            "total_call_volume": m.get("total_call_volume", 0),
            "total_put_volume": m.get("total_put_volume", 0),
            "iv_avg": m.get("iv_avg", 0),
            "updated_at": m.get("options_updated_at"),
            "warning": (
                "감마 스퀴즈 임박"
                if (m.get("gamma_concentration", 0) >= 0.75
                    and m.get("call_put_ratio", 0) >= 2.5)
                else None
            ),
        }

    # ----------------------------------------------------------
    # 펀더멘털 데이터
    # ----------------------------------------------------------
    @app.get("/api/fundamentals/{symbol}")
    def get_fundamentals(symbol: str):
        sym = symbol.upper()
        m = state.stocks.get(sym)
        if not m:
            return {"error": "not found"}

        debt_eq = m.get("debt_to_equity", 0) or 0
        cash_runway = m.get("cash_runway_months", 0) or 0
        rev_growth = m.get("revenue_growth_yoy", 0) or 0

        warnings = []
        if debt_eq > 3:
            warnings.append(f"높은 부채비율 ({debt_eq:.1f})")
        if 0 < cash_runway < 6:
            warnings.append(f"현금 부족 ({cash_runway:.0f}개월)")
        if rev_growth < -20:
            warnings.append(f"매출 급감 ({rev_growth:.0f}%)")

        return {
            "symbol": sym,
            "name": m.get("name", ""),
            "price": m.get("price", 0),
            "market_cap": m.get("market_cap", 0),
            "debt_to_equity": debt_eq,
            "cash_runway_months": cash_runway,
            "revenue_growth_yoy": rev_growth,
            "total_revenue": m.get("total_revenue", 0),
            "net_income": m.get("net_income", 0),
            "cash_and_equivalents": m.get("cash_and_equivalents", 0),
            "total_debt": m.get("total_debt", 0),
            "warnings": warnings,
            "updated_at": m.get("fundamentals_updated_at"),
        }

    # ----------------------------------------------------------
    # 알림 목록
    # ----------------------------------------------------------
    @app.get("/api/alerts")
    def get_alerts(limit: int = 100, level: str = ""):
        items = list(reversed(state.alerts))
        if level:
            items = [a for a in items if a.get("level") == level]
        return {"count": len(items), "items": items[:limit]}

    # ----------------------------------------------------------
    # 시스템 상태 + 데이터 커버리지 진단
    # ----------------------------------------------------------
    @app.get("/api/status")
    def get_status():
        total = len(state.stocks) or 1
        coverage = {
            "price > 0":           sum(1 for v in state.stocks.values() if v.get("price", 0) > 0),
            "si_pct > 0":          sum(1 for v in state.stocks.values() if v.get("si_pct", 0) > 0),
            "ctb > 0":             sum(1 for v in state.stocks.values() if v.get("ctb", 0) > 0),
            "float_shares > 0":    sum(1 for v in state.stocks.values() if v.get("float_shares", 0) > 0),
            "rsi14 set":           sum(1 for v in state.stocks.values() if v.get("rsi14", 50) != 50),
            "has_catalyst":        sum(1 for v in state.stocks.values() if v.get("has_catalyst")),
            "social_velocity > 0": sum(1 for v in state.stocks.values() if v.get("social_velocity", 0) > 0),
            "macd_set":            sum(1 for v in state.stocks.values() if "macd_histogram" in v),
            "acc_score > 0":       sum(1 for v in state.stocks.values() if v.get("acc_score", 0) > 0),
            "gamma set":           sum(1 for v in state.stocks.values() if v.get("gamma_concentration", 0) > 0),
            "fundamentals set":    sum(1 for v in state.stocks.values() if v.get("debt_to_equity", 0) > 0),
            "dark_pool set":       sum(1 for v in state.stocks.values() if v.get("dark_pool_ratio", 0) > 0),
        }
        coverage_pct = {k: f"{v}/{total} ({v*100//total}%)" for k, v in coverage.items()}

        score_dist = {"0-20": 0, "20-40": 0, "40-60": 0, "60-80": 0, "80+": 0}
        for v in state.stocks.values():
            s = v.get("sqs_score", 0) or 0
            if s < 20: score_dist["0-20"] += 1
            elif s < 40: score_dist["20-40"] += 1
            elif s < 60: score_dist["40-60"] += 1
            elif s < 80: score_dist["60-80"] += 1
            else: score_dist["80+"] += 1

        return {
            "ready": state.ready,
            "total_symbols": total,
            "ws_connected": state.ws_connected,
            "dirty_pending": len(state.dirty_symbols),
            "anomalies_active": len(state.anomalies),
            "alerts_total": len(state.alerts),
            "coverage": coverage_pct,
            "score_distribution": score_dist,
        }

    # ----------------------------------------------------------
    # WebSocket (클라이언트 → 서버 실시간 푸시)
    # ----------------------------------------------------------
    @app.websocket("/ws/scores")
    async def ws_scores(ws: WebSocket):
        await ws.accept()
        await _add_client(ws)
        try:
            # 초기 스냅샷 전송
            items = []
            for sym, m in state.stocks.items():
                if m.get("price", 0) > 0:
                    items.append(_row(sym, m))
            items.sort(key=lambda x: -(x.get("sqs_score") or 0))
            await ws.send_text(json.dumps({
                "type": "snapshot",
                "items": items[:300],
                "t": time.time(),
            }, default=str))

            # 클라이언트로부터 메시지 대기 (ping 등)
            while True:
                data = await ws.receive_text()
                if data == "ping":
                    await ws.send_text(json.dumps({"type": "pong", "t": time.time()}))
        except WebSocketDisconnect:
            pass
        except Exception as e:
            print(f"⚠️ ws 오류: {e}")
        finally:
            await _remove_client(ws)
