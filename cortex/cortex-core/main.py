# main.py

import json

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from cortex_core import CortexCore
from models import ConversationMessage
from notification_queue import notification_queue


app = FastAPI(
    title="Cortex Core PoC (API + SSE)",
    description="Combined API endpoint for processing input and SSE notifications",
    version="0.1",
)

# Allow CORS for testing purposes.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize a single CortexCore instance.
core = CortexCore()


# Request model for processing input.
class ProcessInputRequest(BaseModel):
    user_id: str
    token: str
    input_text: str


@app.post("/process", summary="Process user input through the Cortex Core")
def process_input(request_data: ProcessInputRequest):
    response = core.process_input(
        request_data.user_id, request_data.input_text, request_data.token
    )
    if response == "Authentication failed":
        raise HTTPException(status_code=401, detail="Authentication failed")
    return {"response": response}


async def event_generator():
    while True:
        message = await notification_queue.get()
        if isinstance(message, ConversationMessage):
            # Convert the dataclass to a dict and then to JSON
            message_str = json.dumps(message.__dict__)
        else:
            message_str = str(message)
        yield message_str + "\n\n"


@app.get("/notifications", summary="Stream notifications via SSE")
async def notifications():
    headers = {
        "Cache-Control": "no-cache",
        "Content-Type": "text/event-stream",
        "Connection": "keep-alive",
    }
    return EventSourceResponse(event_generator(), headers=headers)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
