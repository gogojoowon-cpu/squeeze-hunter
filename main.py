"""
🔥 숏 스퀴즈 헌터 MEGA v3 — 모듈화 + 동적 티커 수집
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio, threading

from app.api.routes import register_routes
from app.pipeline.loader import init_data
from app.pipeline.enricher import tick_loop
from app.api.routes import push_loop

app = FastAPI(title="ShortSqueezeHunter-v3")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

register_routes(app)


@app.on_event("startup")
async def on_startup():
    # 백그라운드 데이터 로딩
    threading.Thread(target=init_data, daemon=True).start()
    # 30초마다 가격/소셜 갱신
    threading.Thread(target=tick_loop, daemon=True).start()
    # WebSocket 푸시 루프
    asyncio.create_task(push_loop())


if __name__ == "__main__":
    import uvicorn, os
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
