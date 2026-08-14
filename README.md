# FALLEN AI

A personal AI assistant and control center built for Windows and the web.

## Current platform

- FastAPI backend
- OpenAI Responses API integration with streaming responses
- Live futuristic HUD with reactive AI core
- Browser speech recognition
- Windows voice/TTS integration
- Real CPU, memory, GPU, and network telemetry
- Event bus for live AI/tool/device state updates
- Persistent local memory
- Capability and permission manager
- Tool registry with confirmation gates
- Safe Windows tools
- Local network discovery
- Authorized device registry and network sync
- Router/vendor adapter framework

## Security model

FALLEN is designed for the user's own or explicitly authorized environment.

- API keys and device credentials stay outside source control.
- Network/device actions use authenticated, documented interfaces.
- Devices are discovered as unauthorized by default until explicitly approved.
- Destructive, privileged, privacy-sensitive, or irreversible actions require confirmation.
- Tool execution is audited through the event system.

## Run locally

1. Create a Python virtual environment.
2. Install dependencies with `pip install -r requirements.txt`.
3. Set `OPENAI_API_KEY` in a local `.env` file. Never commit the key.
4. Optionally configure `OPENAI_MODEL` in `.env`.
5. Start the API:

```bash
uvicorn backend.main:app --reload
```

6. Open `frontend/index.html` in a browser.

## Architecture

```text
FALLEN AI
├── AI / streaming responses
├── Voice
├── Memory
├── Permissions
├── Event Bus
├── Tool Registry
├── Windows tools
├── Network discovery
├── Device registry
├── Router/vendor adapters
└── Live HUD
```

## Roadmap

Next stages include authenticated router management, vendor/device adapters, broader Windows controls, Android/media/smart-device integrations, desktop packaging, richer voice output, and a unified device/network control center.
