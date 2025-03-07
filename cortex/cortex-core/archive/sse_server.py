# sse_server.py

import asyncio
from fastapi import FastAPI
from sse_starlette.sse import EventSourceResponse
from notification_queue import notification_queue

app = FastAPI(title="Cortex SSE Notification Server", description="Streams notifications via SSE", version="0.1")

async def event_generator():
    """
    Asynchronous generator that waits for notifications in the global queue
    and yields them as SSE messages.
    """
    while True:
        # Wait until a notification is available.
        message = await notification_queue.get()
        # Yield the message as an SSE event.
        yield {"event": "message", "data": message}
        # A short sleep can help in rate limiting.
        await asyncio.sleep(0.1)

@app.get("/notifications", summary="Stream notifications via SSE")
async def notifications():
    """
    SSE endpoint that streams notifications from the global queue.
    Clients can connect to this endpoint to receive real-time updates.
    """
    return EventSourceResponse(event_generator())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
