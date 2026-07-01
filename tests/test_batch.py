from plecs_mcp import server


def test_simulate_batch_aggregates(monkeypatch):
    server._STATE["current_model"] = "m"

    def fake_sim(name, opts=None):
        d = (opts or {}).get("ModelVars", {}).get("D", 0.5)
        return {"Time": list(range(10)), "Values": [[24 * d] * 10]}

    monkeypatch.setattr(server.client, "simulate", fake_sim)
    r = server.plecs_simulate_batch([{"D": 0.3}, {"D": 0.5}])
    assert r["ok"] and r["n"] == 2
    assert abs(r["runs"][0]["metrics"]["steady_state"] - 7.2) < 1e-6
    assert abs(r["runs"][1]["metrics"]["steady_state"] - 12.0) < 1e-6


def test_simulate_batch_no_model(monkeypatch):
    server._STATE["current_model"] = None
    r = server.plecs_simulate_batch([{"D": 0.5}])
    assert r["ok"] is False
