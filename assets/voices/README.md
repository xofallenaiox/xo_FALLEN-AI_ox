# FALLEN AI Voice

This directory documents the private female voice reference supplied for FALLEN AI.

The source audio should remain outside GitHub unless the owner explicitly chooses to publish it. The runtime should load a local voice/model path from environment configuration rather than embedding audio secrets or personal source material in the repository.

Recommended environment variables:

- `FALLEN_VOICE_MODE=local`
- `FALLEN_VOICE_PATH=<local voice/model path>`

The frontend/backend should use the configured voice for spoken responses and keep the UI in `SPEAKING` state until playback completes.
