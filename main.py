"""
Short Squeeze Hunter v3 - FastAPI 진입점
- 백그라운드 데이터 로딩
- 30초 폴링 + Polygon WebSocket 실시간 스트리밍
- 클라이언트 WebSocket 푸시
"""
import warnings
# RuntimeWarning 억제 (tracemalloc, coroutine 경고 등)
# ⚠️ WebSocket async 실행 버그 수정 후에만 활성화할 것
warnings.filterwarnings("ignore", category=RuntimeWarning)

import asyncio
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import state
from app.config import WS_ENABLED
from app.pipeline.loader import init_data
from app.pipeline.enricher import start_tick_thread
from app.api.routes import register_routes, push_loop


# ============================================================
# 백그라운드 초기화 (별도 스레드)
# ============================================================
def _bootstrap():
    """기동 시 1회: 티커 수집 → 가격 → 보강 → 점수"""
    try:
        print("=" * 60)
        print("🚀 Short Squeeze Hunter v3 부팅")
        print("=" * 60)

        # 1) 티커 + 기본 데이터 로딩 + 보강 (init_data가 내부에서 enrich_all 호출)
        init_data()

        # 2) Tick 루프 시작 (5초 간격)
        start_tick_thread()

        # 3) Polygon WebSocket 시작 (실시간 가격 스트리밍)
        if WS_ENABLED:
            try:
                from app.providers.polygon_ws import start_ws_thread
                start_ws_thread()
                print("✅ Polygon WebSocket 시작")
            except Exception as e:
                print(f"⚠️ WebSocket 시작 실패 (폴링으로 대체): {e}")

        print("=" * 60)
        print("✅ 부팅 완료 - 서비스 준비됨")
        print("=" * 60)
    except Exception as e:
        print(f"❌ 부팅 실패: {e}")
        import traceback
        traceback.print_exc()



# ============================================================
# FastAPI Lifespan
# ============================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 시작: 백그라운드 부팅 스레드 + 클라이언트 푸시 루프
    t = threading.Thread(target=_bootstrap, daemon=True)
    t.start()

    push_task = asyncio.create_task(push_loop())

    yield

    # 종료
    push_task.cancel()
    try:
        await push_task
    except asyncio.CancelledError:
        pass


# ============================================================
# FastAPI 인스턴스
# ============================================================
app = FastAPI(
    title="Short Squeeze Hunter",
    version="3.0",
    lifespan=lifespan,
)

# 라우트 등록
register_routes(app)


# ============================================================
# 헬스체크 (Railway용)
# ============================================================
@app.get("/health")
def health():
    return {
        "status": "ok" if state.ready else "loading",
        "loaded": len(state.stocks),
        "ws_connected": state.ws_connected,
    }
