"""전역 상태 (메모리)"""
import asyncio
from typing import Any

# 종목 데이터 {symbol: {...}}
stocks: dict[str, dict] = {}
# 점수 히스토리 {symbol: [{ts, score, grade}, ...]}
history: dict[str, list] = {}
# 알림
alerts: list[dict] = []
# 알림 쿨다운 {symbol: timestamp}
alert_cooldown: dict[str, float] = {}
# 로딩 상태
ready = False
enrich_done = False
# Aggs 캐시 {sym: {data, _ts}}
aggs_cache: dict[str, dict] = {}
# WebSocket 클라이언트
ws_clients: list[Any] = []
