"""Opt-in structured logging for plecs-mcp.

Logs go to STDERR (stdout is reserved for the MCP stdio protocol) and, if
`PLECS_MCP_LOG_FILE` is set, to that file too. Level via `PLECS_MCP_LOG_LEVEL`
(default WARNING, so it's quiet unless you ask for detail).
"""
from __future__ import annotations

import logging
import os
import sys

_CONFIGURED = False


def configure() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    logger = logging.getLogger("plecs_mcp")
    logger.setLevel(os.environ.get("PLECS_MCP_LOG_LEVEL", "WARNING").upper())
    fmt = logging.Formatter("%(asctime)s %(levelname)s plecs_mcp: %(message)s")
    sh = logging.StreamHandler(sys.stderr)
    sh.setFormatter(fmt)
    logger.addHandler(sh)
    logfile = os.environ.get("PLECS_MCP_LOG_FILE")
    if logfile:
        fh = logging.FileHandler(logfile, encoding="utf-8")
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    logger.propagate = False
    _CONFIGURED = True


def get_logger() -> logging.Logger:
    return logging.getLogger("plecs_mcp")
