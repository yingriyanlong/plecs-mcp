from plecs_mcp.config import Config
from plecs_mcp.rpc import client


def test_ping_offline_shape():
    # Point at a closed port; ping must return a dict, not raise.
    r = client.ping(Config(host="127.0.0.1", port=9, timeout=1.0))
    assert {"online", "host", "port", "detail"}.issubset(r)
    assert r["online"] is False
