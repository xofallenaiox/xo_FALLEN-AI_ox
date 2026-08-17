"""Outbound-only Windows agent client."""

from __future__ import annotations

import asyncio
import logging

import httpx

from .config import AgentConfig
from .tools import AgentToolError, execute

logger = logging.getLogger("fallen-agent")


class AgentClient:
    """Poll the cloud over authenticated HTTPS without opening an inbound port."""

    def __init__(self, config: AgentConfig) -> None:
        self.config = config
        self.headers = {
            "Authorization": f"Bearer {config.token}",
            "X-FALLEN-Agent-ID": config.agent_id,
        }

    async def run(self) -> None:
        timeout = httpx.Timeout(self.config.request_timeout)
        limits = httpx.Limits(max_connections=4, max_keepalive_connections=2)
        async with httpx.AsyncClient(
            timeout=timeout,
            headers=self.headers,
            limits=limits,
        ) as client:
            while True:
                try:
                    await self._poll_once(client)
                except asyncio.CancelledError:
                    raise
                except httpx.HTTPStatusError as exc:
                    if exc.response.status_code in {401, 403}:
                        logger.error("Agent authentication failed; stopping agent.")
                        return
                    logger.exception("Agent polling request failed")
                except (httpx.HTTPError, OSError):
                    logger.exception("Agent polling network failure")
                except Exception:
                    logger.exception("Agent polling cycle failed")
                await asyncio.sleep(self.config.poll_interval)

    async def _poll_once(self, client: httpx.AsyncClient) -> None:
        response = await client.post(f"{self.config.cloud_url}/agents/poll")
        response.raise_for_status()
        task = response.json().get("task")
        if not task:
            return

        if not isinstance(task, dict) or not isinstance(task.get("task_id"), str):
            raise RuntimeError("Cloud returned an invalid task payload.")
        tool = task.get("tool")
        arguments = task.get("arguments", {})
        if not isinstance(tool, str) or not isinstance(arguments, dict):
            raise RuntimeError("Cloud returned an invalid task payload.")

        try:
            result = execute(tool, arguments)
            success = True
        except AgentToolError as exc:
            result = {"ok": False, "error": str(exc)}
            success = False
        except Exception:
            logger.exception("Unhandled local tool failure")
            result = {"ok": False, "error": "Local tool execution failed."}
            success = False

        result_response = await client.post(
            f"{self.config.cloud_url}/agents/result",
            json={
                "task_id": task["task_id"],
                "success": success,
                "result": result,
            },
        )
        result_response.raise_for_status()
