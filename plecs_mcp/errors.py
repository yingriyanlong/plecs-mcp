"""Error types with actionable messages for MCP tool responses."""
from __future__ import annotations


class PlecsMCPError(Exception):
    """Base error; str() should tell the agent what to do next."""


class PlecsOffline(PlecsMCPError):
    """Raised when the PLECS XML-RPC interface cannot be reached."""
