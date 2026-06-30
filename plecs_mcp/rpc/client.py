"""Thin, dependency-free wrapper around the PLECS XML-RPC interface.

PLECS exposes an XML-RPC-over-HTTP server (default port 1080) with methods
under the ``plecs.`` namespace (``plecs.load``, ``plecs.simulate``,
``plecs.set``, ``plecs.get``, ``plecs.close``, ...). This module wraps it and
normalises errors so the MCP tools return actionable messages instead of raw
socket faults.

Verified against live PLECS 4.7 on Windows (RPC port 1080).
"""
from __future__ import annotations

import socket
import xmlrpc.client
from typing import Any, Optional

from ..config import Config, load_config


def _proxy(cfg: Optional[Config] = None) -> xmlrpc.client.ServerProxy:
    cfg = cfg or load_config()
    socket.setdefaulttimeout(cfg.timeout)
    return xmlrpc.client.ServerProxy(f"http://{cfg.host}:{cfg.port}", allow_none=True)


def ping(cfg: Optional[Config] = None) -> dict[str, Any]:
    """Report PLECS RPC reachability without needing a loaded model.

    A reachable PLECS answers XML-RPC even for a bad request (it returns a
    Fault). We treat any XML-RPC-level response (ok OR Fault) as ``online`` and
    only socket/connection errors as ``offline``.
    """
    cfg = cfg or load_config()
    try:
        _proxy(cfg).plecs.get("__mcp_ping__")
        return {"online": True, "host": cfg.host, "port": cfg.port, "detail": "ok"}
    except xmlrpc.client.Fault as f:
        return {
            "online": True, "host": cfg.host, "port": cfg.port,
            "detail": f"xmlrpc fault (expected for ping): {f.faultString[:80]}",
        }
    except OSError as e:
        return {
            "online": False, "host": cfg.host, "port": cfg.port,
            "detail": (
                f"not reachable: {e}. Ensure PLECS is running and "
                f"Preferences > General > RPC interface port is enabled on {cfg.port}."
            ),
        }


def load(path: str, cfg: Optional[Config] = None):
    """Load a .plecs model by absolute path (plecs.load).

    PLECS does NOT refresh a model that is already open, so we close any model
    of the same name first to guarantee the on-disk version is (re)loaded.
    """
    import os
    p = _proxy(cfg)
    name = os.path.splitext(os.path.basename(path))[0]
    try:
        p.plecs.close(name)
    except Exception:
        pass
    return p.plecs.load(path)


def close(name: str, cfg: Optional[Config] = None):
    """Close an open model by name (plecs.close)."""
    return _proxy(cfg).plecs.close(name)


def simulate(name: str, opts: Optional[dict] = None, cfg: Optional[Config] = None):
    """Run a simulation (plecs.simulate); returns {'Time': [...], 'Values': [...]}."""
    p = _proxy(cfg)
    return p.plecs.simulate(name, opts) if opts else p.plecs.simulate(name)


def set_param(component: str, parameter: str, value, cfg: Optional[Config] = None):
    """Set a component parameter (plecs.set)."""
    return _proxy(cfg).plecs.set(component, parameter, str(value))


def get_param(component: str, parameter: str, cfg: Optional[Config] = None):
    """Get a component parameter (plecs.get)."""
    return _proxy(cfg).plecs.get(component, parameter)
