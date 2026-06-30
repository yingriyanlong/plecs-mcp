"""PLECS MCP server (stdio transport). Milestone M0: connectivity.

Run via the ``plecs-mcp`` console script or ``python -m plecs_mcp.server``.
"""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .config import load_config
from .rpc import client

mcp = FastMCP("plecs-mcp")


@mcp.tool()
def plecs_status() -> dict:
    """Check whether the local PLECS XML-RPC interface is reachable.

    Returns a dict with ``online`` (bool), ``host``, ``port`` and a ``detail``
    string. Call this first to confirm PLECS is running with its RPC port
    enabled before loading models or simulating.
    """
    return client.ping(load_config())


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
