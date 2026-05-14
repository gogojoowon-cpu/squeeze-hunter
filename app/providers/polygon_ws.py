"""Polygon WebSocket 실시간 클라이언트 — 거래/분봉 스트리밍"""
import asyncio, json, time
from app.config import POLYGON_API_KEY, WS_ENABLED, WS_TOP_N
from app import state

# WebSocket URL (Stocks)
WS_URL = "wss://socket.polygon.io/stocks"


async def polygon_ws_loop():
    """Polygon WebSocket 메인 루프 — 자동 재연결"""
    if not WS_ENABLED:
        print("⚠️ Polygon WS 비활성화 (WS_ENABLED=false)")
        return
    if not POLYGON_API_KEY:
        print("⚠️ POLYGON_API_KEY 없음 — WS 스킵")
        return

    # 데이터 로딩 대기
    while not state.ready:
        await asyncio.sleep(5)

    print("🌐 Polygon WebSocket 시작...")

    while True:
        try:
            await _connect_and_stream()
        except Exception as e:
            print(f"⚠️ Polygon WS 오류: {e}")
            state.ws_connected = False
        print("🔄 Polygon WS 10초 후 재연결...")
        await asyncio.sleep(10)


async def _connect_and_stream():
    """WebSocket 연결 + 메시지 스트리밍"""
    try:
        import websockets
    except ImportError:
        print("❌ websockets 라이브러리 없음 — pip install websockets")
        return

    async with websockets.connect(WS_URL, ping_interval=20) as ws:
        # 1) 인증
        await ws.send(json.dumps({"action": "auth", "params": POLYGON_API_KEY}))
        auth_resp = await ws.recv()
        if "auth_success" not in auth_resp:
            print(f"❌ 인증 실패: {auth_resp}")
            return
        print("✅ Polygon WS 인증 성공")

        # 2) 상위 N개 종목 구독 (분봉 AM)
        top_syms = _get_top_symbols(WS_TOP_N)
        if not top_syms:
            print("⚠️ 구독할 종목 없음")
            return

        # 분봉 (AM) + 거래 (T) 둘 다 구독
        # AM.{symbol} = 분 단위 집계 (가격/거래량)
        subscribe = "AM." + ",AM.".join(top_syms)
        await ws.send(json.dumps({"action": "subscribe", "params": subscribe}))
        print(f"📡 Polygon WS 구독: {len(top_syms)}개 종목 (분봉)")

        state.ws_connected = True

        # 3) 메시지 수신 루프
        async for message in ws:
            try:
                _handle_message(message)
            except Exception as e:
                print(f"⚠️ WS 메시지 처리 오류: {e}")


def _get_top_symbols(n: int) -> list[str]:
    """SQS 점수 + 매집 점수 + 거래량 기준 상위 N개"""
    by_score = sorted(state.stocks.keys(),
                      key=lambda x: state.stocks[x].get("score", 0),
                      reverse=True)[:n]
    by_acc = sorted(state.stocks.keys(),
                    key=lambda x: state.stocks[x].get("acc_score", 0),
                    reverse=True)[:n // 2]
    by_vol = sorted(state.stocks.keys(),
                    key=lambda x: state.stocks[x].get("volume", 0),
                    reverse=True)[:n // 2]

    combined = list(dict.fromkeys(by_score + by_acc + by_vol))[:n]
    return combined


def _handle_message(message: str):
    """WS 메시지 처리 — AM(분봉) 이벤트"""
    state.metrics["ws_messages_received"] += 1
    try:
        events = json.loads(message)
        if not isinstance(events, list):
            return

        for ev in events:
            ev_type = ev.get("ev", "")

            # AM = Aggregate Minute (분봉)
            if ev_type == "AM":
                sym = ev.get("sym", "")
                if sym not in state.stocks:
                    continue

                # 분봉 데이터
                close = float(ev.get("c", 0))      # 종가
                volume = int(ev.get("v", 0))       # 거래량
                vw = float(ev.get("vw", close))    # 가중평균가
                ts = ev.get("e", time.time() * 1000)  # 종료 시간 ms

                if close > 0:
                    d = state.stocks[sym]
                    prev_price = d.get("price", close)

                    # 가격 업데이트
                    d["price"] = round(close, 2)
                    d["ws_last_volume"] = volume
                    d["ws_vwap"] = round(vw, 2)
                    d["ws_ts"] = ts

                    # 일중 변동률 (시가 대비)
                    open_today = d.get("ws_day_open", 0)
                    if open_today == 0:
                        d["ws_day_open"] = close
                    else:
                        d["change_pct"] = round((close - open_today) / open_today * 100, 2)

                    # 분봉 거래량 누적
                    cum_vol = d.get("ws_cum_volume", 0) + volume
                    d["ws_cum_volume"] = cum_vol

                    # 평균 분봉 거래량 (1일 = 390분) → 거래량 spike 계산
                    avg_vol = d.get("avg_vol", 1)
                    if avg_vol > 0:
                        expected_vol_per_min = avg_vol / 390
                        if expected_vol_per_min > 0:
                            d["vol_spike"] = round(volume / expected_vol_per_min, 2)

                    # 🆕 dirty flag — 점수 재계산 필요
                    state.dirty_symbols.add(sym)

                    # ws_prices에도 저장 (디버깅용)
                    state.ws_prices[sym] = {
                        "price": close,
                        "volume": volume,
                        "vwap": vw,
                        "ts": ts,
                    }
    except json.JSONDecodeError:
        pass
def start_ws_thread():
    """
    백그라운드 스레드로 Polygon WebSocket 시작
    파일 안에 정의된 메인 루프 함수를 자동 탐지해서 실행
    """
    import threading
    import sys
    
    # 현재 모듈에서 메인 루프 함수 후보 찾기
    candidates = ["ws_loop", "run_ws", "run", "main_loop", "start", "polygon_ws_loop"]
    module = sys.modules[__name__]
    
    target_func = None
    for name in candidates:
        f = getattr(module, name, None)
        if callable(f):
            target_func = f
            print(f"✅ WebSocket 메인 루프 발견: {name}()")
            break
    
    if not target_func:
        print(f"⚠️ WebSocket 시작 실패: 메인 루프 함수를 찾을 수 없음")
        print(f"   파일 안의 함수 이름을 확인하세요. 후보: {candidates}")
        return None
    
    t = threading.Thread(target=target_func, daemon=True, name="polygon-ws")
    t.start()
    print(f"✅ Polygon WebSocket 스레드 시작")
    return t
