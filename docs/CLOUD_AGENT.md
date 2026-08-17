# FALLEN Cloud Brain + Windows Agent

The cloud owns browser authentication, OpenAI credentials, memory/task state,
agent registration, confirmation state, and AI orchestration.

The Windows agent owns local Windows execution. It makes outbound HTTPS
requests and does not listen on an inbound TCP port.

## Bootstrap

Configure the cloud with:

```text
FALLEN_API_TOKEN
FALLEN_AGENT_ENROLLMENT_TOKEN
OPENAI_API_KEY
OPENAI_MODEL
```

On Render, use the generated secret values and set:

```text
FALLEN_ALLOWED_HOSTS=your-service.onrender.com
FALLEN_ALLOWED_ORIGINS=https://your-service.onrender.com
FALLEN_COOKIE_SECURE=true
FALLEN_DATA_DIR=/var/data
```

Register the Windows agent from a trusted administrator machine:

```text
curl -X POST https://YOUR_HOST/agents/register ^
  -H "Content-Type: application/json" ^
  -d "{\"enrollment_token\":\"YOUR_ENROLLMENT_TOKEN\",\"name\":\"my-windows-pc\"}"
```

Store the returned `agent_id` and token only on the Windows computer.

Set:

```text
FALLEN_CLOUD_URL=https://YOUR_HOST
FALLEN_AGENT_ID=returned-agent-id
FALLEN_AGENT_TOKEN=returned-agent-token
```

Then run:

```text
python -m agent.main
```

## Security boundary

OpenAI never receives a shell, PowerShell, or arbitrary-command tool.

The cloud only exposes named, JSON-schema-validated functions. The cloud
creates a task, and the Windows agent validates the tool again against its
local allowlist before execution.

Never add arbitrary `shell`, `powershell`, `cmd`, or `python` execution.

For destructive operations, set `requires_confirmation=True`; the task stays
out of the agent queue until an authenticated user approves it.

## Scaling limitation

The task broker is SQLite-backed and intended for one cloud instance. Before
horizontal scaling, move task locking/queue state to a shared transactional
store.
