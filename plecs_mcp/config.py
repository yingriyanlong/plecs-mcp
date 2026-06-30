"""Runtime configuration for the PLECS MCP server (environment-overridable)."""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    host: str = "localhost"
    port: int = 1080
    timeout: float = 30.0


def load_config() -> "Config":
    """Build config from PLECS_HOST / PLECS_RPC_PORT / PLECS_RPC_TIMEOUT env vars."""
    return Config(
        host=os.environ.get("PLECS_HOST", "localhost"),
        port=int(os.environ.get("PLECS_RPC_PORT", "1080")),
        timeout=float(os.environ.get("PLECS_RPC_TIMEOUT", "30")),
    )
