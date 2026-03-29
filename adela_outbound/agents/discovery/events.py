import asyncio
from typing import Any

sse_queues: list[asyncio.Queue] = []


async def broadcast(event: str, data: dict) -> None:
    for q in sse_queues:
        try:
            q.put_nowait({"event": event, "data": data})
        except asyncio.QueueFull:
            pass
