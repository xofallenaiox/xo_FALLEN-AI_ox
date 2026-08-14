import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI

load_dotenv()

app = FastAPI(title="FALLEN AI", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str

@app.get("/health")
def health():
    return {"status": "online", "assistant": "FALLEN AI"}

@app.post("/chat")
def chat(request: ChatRequest):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not configured")

    client = OpenAI(api_key=api_key)
    try:
        response = client.responses.create(
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
