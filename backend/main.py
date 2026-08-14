import json
import os
from typing import AsyncGenerator

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from openai import AsyncOpenAI

from telemetry import snapshot
from voice import speak
from event_bus import FallenEvent, bus
from memory import delete_memory, save_memory, search_memory
from permissions import permission_manager

load_dotenv()

app = FastAPI(title="FALLEN AI", version="0.6.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str


class SpeakRequest(BaseModel):
    text: str


class MemoryRequest(BaseModel):
    key: str
    value: str


class PermissionRequest(BaseModel):
    capability: str
    level: str = "read"
    ttl_seconds: int | None = None


async def publish_event(event_type: str, status: str, message: str = "", target: str | None = None, data: dict | None = None) -> None:
    await bus.publish(FallenEvent(type=event_type, status=status, message=message, target=target, data=data))


def get_client() -> AsyncOpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not configured")
    return AsyncOpenAI(api_key=api_key)


@app.get("/health")
def health():
    return {"status": "online", "assistant": "FALLEN AI"}


@app.get("/telemetry")
def telemetry():
    return snapshot()


@app.post("/voice/speak")
async def voice_speak(request: SpeakRequest):
    await publish_event("speaking", "started", "Voice output requested")
    result = speak(request.text)
    await publish_event("speaking", "completed" if result.get("ok") else "failed", result.get("status", ""))
    return result


@app.post("/memory/save")
def memory_save(request: MemoryRequest):
    return save_memory(request.key, request.value)


@app.get("/memory/search")
def memory_search(q: str, limit: int = 10):
    return search_memory(q, limit=limit)


@app.delete("/memory/{key}")
def memory_delete(key: str):
    return delete_memory(key)


@app.post("/permissions/grant")
def permission_grant(request: PermissionRequest):
    return permission_manager.grant(request.capability, request.level, ttl_seconds=request.ttl_seconds)


@app.post("/permissions/revoke/{capability}")
def permission_revoke(capability: str):
    return permission_manager.revoke(capability)


@app.get("/permissions")
def permissions_list():
    return permission_manager.list()


@app.get("/events")
async def events():
    queue = await bus.subscribe()

    async def stream() -> AsyncGenerator[str, None]:
        try:
            while True:
                event = await queue.get()
                yield f"data: {json.dumps(event)}\n\n"
        finally:
            await bus.unsubscribe(queue)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/chat")
async def chat(request: ChatRequest):
    await publish_event("thinking", "started", "Processing command")
    client = get_client()
    try:
        response = await client.responses.create(
            model=os.getenv("OPENAI_MODEL", "gpt-5.6"),
            instructions=(
                "You are FALLEN AI, a capable personal AI assistant. "
                "Be concise, helpful, honest, and safety-conscious."
            ),
            input=request.message,
        )
        await publish_event("thinking", "completed", "Response ready")
        return {"reply": response.output_text}
    except Exception as exc:
        await publish_event("error", "failed", str(exc))
        raise HTTPException(status_code=502, detail=f"AI request failed: {exc}")


async def stream_response(message: str) -> AsyncGenerator[str, None]:
    client = get_client()
    await publish_event("thinking", "started", "Processing command")
    try:
        stream = await client.responses.create(
            model=os.getenv("OPENAI_MODEL", "gpt-5.6"),
            instructions=(
                "You are FALLEN AI, a capable personal AI assistant. "
                "Be concise, helpful, honest, and safety-conscious."
            ),
            input=message,
            stream=True,
        )
        await publish_event("speaking", "started", "Streaming response")
        async for event in stream:
            event_type = getattr(event, "type", "")
            if event_type == "response.output_text.delta":
                delta = getattr(event, "delta", "")
                if delta:
                    yield f"data: {json.dumps({'type': 'delta', 'text': delta})}\n\n"
            elif event_type == "response.completed":
                await publish_event("speaking", "completed", "Response stream complete")
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
    except Exception as exc:
        await publish_event("error", "failed", str(exc))
        yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    return StreamingResponse(
        stream_response(request.message),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
