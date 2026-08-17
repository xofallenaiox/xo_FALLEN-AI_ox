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


## Hardened local startup

```powershell
.\scripts\bootstrap_windows.ps1
# Set OPENAI_API_KEY in .env
.\scripts\start-local.ps1
```

Open `http://127.0.0.1:8000/`. The backend serves the HUD directly; a separate frontend server is not required.

## Production configuration

Render should run:

```text
python -m uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```

Required secrets are `OPENAI_API_KEY`, `FALLEN_API_TOKEN`,
`FALLEN_SESSION_SECRET`, and `FALLEN_AGENT_ENROLLMENT_TOKEN`.
Set `FALLEN_ALLOWED_HOSTS` to the exact Render hostname and
`FALLEN_ALLOWED_ORIGINS` to its `https://` origin.

Never commit `.env`, agent credentials, or API keys.


### Windows Agent enrollment

After the Render service is healthy:

```powershell
.\scripts\register-agent.ps1
python -m agent.main
```

The registration script stores only the agent credentials in `agent\.env`; the Cloud Brain `.env` is not reused by the agent.


## Production deployment

The hardened build is intended to run as a same-origin FastAPI service on Render. Use
`scripts/publish-production.ps1` to publish the current source to the `production-hardening`
branch of the configured repository. Never commit `.env` or agent credentials.
