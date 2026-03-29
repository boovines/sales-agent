import asyncio

sse_queues: list = []


async def broadcast(event: str, data: dict) -> None:
    for q in sse_queues:
        try:
            q.put_nowait({'event': event, 'data': data})
        except asyncio.QueueFull:
            pass
