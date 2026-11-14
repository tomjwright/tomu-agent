"""HTTP API: POST /api/chat runs one turn and streams each step as it happens.

The stream is Server-Sent Events: one `data: {...json event...}` line per step.
Run it with `uv run uvicorn tomu.server:app --reload`.
"""

import json
import queue
import threading
import time

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from tomu.agent import run_agent

load_dotenv()
app = FastAPI(title="Tomu")
# Let the Next.js page on localhost:3000 call this API from the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["POST"],
    allow_headers=["content-type"],
)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)


@app.post("/api/chat")
def chat(request: ChatRequest) -> StreamingResponse:
    return StreamingResponse(stream_turn(request.message), media_type="text/event-stream")


def stream_turn(message: str):
    """Run the agent in a background thread and yield its events as they arrive."""
    events: queue.Queue = queue.Queue()

    def worker():
        run_agent(message, events.put)
        events.put(None)  # end of turn

    threading.Thread(target=worker, daemon=True).start()
    while (event := events.get()) is not None:
        yield f"data: {json.dumps(event | {'at': time.time()})}\n\n"
