"""REST + WebSocket 라우트"""
import asyncio, json, random
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from app import state
from app.config import DELISTED
from app.market import market_status, is_market_open
from app.themes import THEMES
from app.web.ui import HTML_PAGE


def _row(k, v):
    return {
        "symbol": k, "score": v.get("score", 0), "grade": v.get("grade", "NO_SQUEEZE"),
        "price": v.get("price", 0), "si_pct": v.get("si_pct", 0),
        "ctb": v.get("ctb", 0), "dtc": v.get("dtc", 0), "util": v.get("util", 0),
        "volume": v.get("volume", 0), "change_pct": v.get("change_pct", 0),
        "name": v.get("name", k), "sector": v.get("sector", "기타"),
        "theme": v.get("theme", "기타"), "delta": v.get("delta", 0),
        "high_52w": v.get("high_52w", 0), "low_52w": v.get("low_52w", 0),
        "rsi14": v.get("rsi14", 50), "gamma_conc": v.get("gamma_conc", 0),
        "social_velocity": v.get("social_velocity", 0),
        "mentions": v.get("mentions", 0),
        "has_catalyst": v.get("has_catalyst", False),
        "ctb_src": v.get("ctb_src", "demo"),
        "soc_src": v.get("soc_src", "demo"),
        "si_shares": v.get("si_shares", 0),
        "float_shares": v.get("float_shares", 0),
        "market_cap": v.get("market_cap", 0),
        "vol_spike": v.get("vol_spike", 1),
    }


async def broadcast(msg: str):
    dead = []
    for ws in state.ws_clients:
        try:
            await ws.send_text(msg)
        except Exception:
            dead.append(ws)
    for ws in dead:
        if ws in state.ws_clients:
            state.ws_clients.remove(ws)


async def push_loop():
    """4초마다 일부 종목 푸시"""
    await asyncio.sleep(8)
    while True:
        await asyncio.sleep(4)
        if not state.ready or not state.stocks:
            continue
        sample = random.sample(list(state.stocks.keys()),
                               min(12, len(state.stocks)))
        for sym in sample:
            d = state.stocks[sym]
            await broadcast(json.dumps({
                "type": "score_update", "symbol": sym,
                "score": d.get("score", 0), "grade": d.get("grade", ""),
                "delta": d.get("delta", 0), "ts": d.get("ts", ""),
                "price": d.get("price", 0), "si_pct": d.get("si_pct", 0),
                "ctb": d.get("ctb", 0), "dtc": d.get("dtc", 0),
                "util": d.get("util", 0), "volume": d.get("volume", 0),
                "change_pct": d.get("change_pct", 0),
                "name": d.get("name", sym), "theme": d.get("theme", "기타"),
                "rsi14": d.get("rsi14", 50),
                "social_velocity": d.get("social_velocity", 0),
                "mentions": d.get("mentions", 0),
                "has_catalyst": d.get("has_catalyst", False),
                "vol_spike": d.get("vol_spike", 1),
            }))


def register_routes(app):
    @app.get("/api/scores/top")
    def top(limit: int = 200, min_score: float = 0,
            theme: str = "", grade_f: str = ""):
        rows = [v for v in state.stocks.values() if v.get("score", 0) >= min_score]
        if theme:
            rows = [r for r in rows if r.get("theme", "") == theme]
        if grade_f:
            rows = [r for r in rows if r.get("grade", "") == grade_f]
        return sorted(rows, key=lambda x: x.get("score", 0), reverse=True)[:limit]

    @app.get("/api/themes")
    def themes_api():
        return [
            {"id": k, "desc": v["desc"], "event": v["event"], "color": v["color"],
             "count": sum(1 for s in state.stocks.values() if s.get("theme") == k)}
            for k, v in THEMES.items()
        ]

    @app.get("/api/scores/{symbol}/history")
    def history(symbol: str):
        return state.history.get(symbol.upper(), [])

    @app.get("/api/scores/{symbol}/breakdown")
    def breakdown(symbol: str):
        d = state.stocks.get(symbol.upper())
        if not d:
            return {"symbol": symbol, "breakdown": None}
        return {
            "symbol": symbol, "score": d.get("score", 0),
            "grade": d.get("grade", ""),
            "breakdown": d.get("breakdown", {}),
            "data_sources": {
                "price": "polygon", "si_pct": "polygon",
                "ctb": d.get("ctb_src", "estimated"),
                "social": d.get("soc_src", "demo"),
            }
        }

    @app.get("/api/alerts")
    def alerts(limit: int = 100):
        return state.alerts[:limit]

    @app.get("/api/news/{symbol}")
    def stock_news(symbol: str):
        d = state.stocks.get(symbol.upper())
        if not d:
            return {"news": [], "symbol": symbol}
        return {
            "symbol": symbol,
            "news": d.get("latest_news", []),
            "has_catalyst": d.get("has_catalyst", False),
            "news_count": d.get("news_count", 0),
            "news_sentiment": d.get("news_sentiment", 0),
        }

    @app.get("/api/accumulation")
    def accumulation(limit: int = 50):
        rows = []
        for v in state.stocks.values():
            vs = v.get("vol_spike", 1)
            pc = abs(v.get("change_pct", 0))
            price = v.get("price", 0)
            if vs >= 2.0 and pc <= 5.0 and 0 < price <= 20:
                rows.append({**v, "acc_ratio": round(vs / max(pc, 0.1), 1)})
        return sorted(rows, key=lambda x: x.get("acc_ratio", 0), reverse=True)[:limit]

    @app.get("/api/market")
    def market_api():
        return {"status": market_status(), "is_open": is_market_open()}

    @app.get("/api/snapshot")
    def snapshot():
        return [_row(k, v) for k, v in state.stocks.items()]

    @app.get("/api/status")
    def status():
        loaded = sum(1 for v in state.stocks.values() if v.get("price", 0) > 0)
        return {
            "loaded": loaded,
            "total": len(state.stocks),
            "ready": state.ready,
            "enrich_done": state.enrich_done,
            "real_social": sum(1 for v in state.stocks.values()
                               if v.get("soc_src") == "apewisdom"),
            "themes": len(THEMES),
            "delisted": len(DELISTED),
            "market": market_status(),
            "is_open": is_market_open(),
        }

    @app.websocket("/ws/scores")
    async def ws_ep(websocket: WebSocket):
        await websocket.accept()
        state.ws_clients.append(websocket)
        await websocket.send_text(json.dumps({
            "type": "snapshot",
            "data": [_row(k, v) for k, v in state.stocks.items()]
        }))
        try:
            while True:
                try:
                    d = await asyncio.wait_for(websocket.receive_text(), timeout=25)
                    if d == "ping":
                        await websocket.send_text('{"type":"pong"}')
                except asyncio.TimeoutError:
                    await websocket.send_text('{"type":"heartbeat"}')
        except WebSocketDisconnect:
            pass
        finally:
            if websocket in state.ws_clients:
                state.ws_clients.remove(websocket)

    @app.get("/", response_class=HTMLResponse)
    def index():
        return HTML_PAGE
