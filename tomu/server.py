"""HTTP API: POST /api/chat runs one turn and streams each step as it happens.

The stream is Server-Sent Events: one `data: {...json event...}` line per step.
When a tool needs your approval, the turn waits until the page answers with
POST /api/approve {"id", "approved"}.
Run it with `uv run uvicorn tomu.server:app --reload`.
"""

import json
import queue
import threading
import time

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
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


APPROVAL_TIMEOUT = 300  # seconds to wait for your answer before counting it as no
waiting: dict[str, queue.Queue] = {}  # call id -> where your answer goes


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)


class ApprovalAnswer(BaseModel):
    id: str
    approved: bool


@app.post("/api/chat")
def chat(request: ChatRequest) -> StreamingResponse:
    return StreamingResponse(stream_turn(request.message), media_type="text/event-stream")


@app.post("/api/approve")
def approve(answer: ApprovalAnswer) -> dict:
    if (box := waiting.get(answer.id)) is None:
        raise HTTPException(404, "Nothing is waiting for that approval.")
    try:
        box.put_nowait(answer.approved)
    except queue.Full:
        raise HTTPException(409, "That action was already answered.") from None
    return {"ok": True}


def wait_for_approval(id: str, name: str, input: dict) -> bool:
    try:
        return waiting[id].get(timeout=APPROVAL_TIMEOUT)
    except queue.Empty:
        return False
    finally:
        waiting.pop(id, None)


def stream_turn(message: str):
    """Run the agent in a background thread and yield its events as they arrive."""
    events: queue.Queue = queue.Queue()

    def emit(event: dict):
        if event["type"] == "approval_request":  # ready for the answer before the page asks
            waiting[event["id"]] = queue.Queue(maxsize=1)
        events.put(event)

    def worker():
        try:
            run_agent(message, emit, approve=wait_for_approval)
        finally:
            events.put(None)  # end of turn, even if the agent crashed

    threading.Thread(target=worker, daemon=True).start()
    while (event := events.get()) is not None:
        yield f"data: {json.dumps(event | {'at': time.time()})}\n\n"
