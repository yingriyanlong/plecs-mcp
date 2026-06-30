from plecs_mcp.config import load_config


def test_defaults(monkeypatch):
    for k in ("PLECS_HOST", "PLECS_RPC_PORT", "PLECS_RPC_TIMEOUT"):
        monkeypatch.delenv(k, raising=False)
    c = load_config()
    assert c.host == "localhost"
    assert c.port == 1080
    assert c.timeout == 30.0


def test_env_override(monkeypatch):
    monkeypatch.setenv("PLECS_RPC_PORT", "32400")
    assert load_config().port == 32400
