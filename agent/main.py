"""FALLEN Windows Agent entry point."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from dotenv import load_dotenv

from .client import AgentClient
from .config import AgentConfig


def main() -> None:
    load_dotenv(Path(__file__).resolve().with_name(".env"))
    logging.basicConfig(level="INFO")
    asyncio.run(AgentClient(AgentConfig.from_environment()).run())


if __name__ == "__main__":
    main()
