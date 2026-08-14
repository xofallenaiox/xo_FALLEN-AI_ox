# FALLEN AI Female Voice Setup

FALLEN keeps the supplied voice sample outside GitHub. The application should use a configurable text-to-speech provider and a female voice selected to match the uploaded reference sample in tone, warmth, pacing, and clarity.

## Runtime flow

1. FALLEN receives a user message by text or microphone.
2. The AI response streams from the backend.
3. When the response is complete, the frontend sends the final text to `/voice/speak`.
4. The Windows voice layer synthesizes the response with the configured female voice.
5. The UI remains in `SPEAKING` state until the local speech request completes.

## Configuration

Keep provider credentials in environment variables or the platform's secret store. Never commit API keys or the private sample audio to GitHub.

Recommended variables:

- `VOICE_PROVIDER`
- `VOICE_ID`
- `VOICE_RATE`
- `VOICE_PITCH`

The current Windows fallback uses PowerShell SAPI. A cloud TTS provider or a local voice engine can be substituted later without changing the UI contract.
