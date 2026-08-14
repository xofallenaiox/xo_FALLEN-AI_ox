# FALLEN AI

A personal AI assistant built for Windows and the web.

## Current MVP

- FastAPI backend
- OpenAI Responses API integration
- Browser chat interface
- Health/status endpoint
- Environment-based API key configuration

## Run locally

1. Create a Python virtual environment.
2. Install dependencies with `pip install -r requirements.txt`.
3. Set `OPENAI_API_KEY` in a local `.env` file. Never commit the key.
4. Start the API:

```bash
uvicorn backend.main:app --reload
```

5. Open `frontend/index.html` in a browser.

## Roadmap

Voice, persistent memory, web tools, file understanding, Windows automation, authentication, and a desktop interface can be added as separate modules.
