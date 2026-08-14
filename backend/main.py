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

load_dotenv()

app = FastAPI(title="FALLEN AI", version="0.4.0")
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
def voice_speak(request: SpeakRequest):
    return speak(request.text)


@app.post("/chat")
async def chat(request: ChatRequest):
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
        return {"reply": response.output_text}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AI request failed: {exc}")


async def stream_response(message: str) -> AsyncGenerator[str, None]:
    client = get_client()
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
        async for event in stream:
            event_type = getattr(event, "type", "")
            if event_type == "response.output_text.delta":
                delta = getattr(event, "delta", "")
                if delta:
                    yield f"data: {json.dumps({'type': 'delta', 'text': delta})}\n\n"
            elif event_type == "response.completed":
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
    except Exception as exc:
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
