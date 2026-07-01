from plecs_mcp import server


def test_simulate_inline_metrics(monkeypatch):
    server._STATE["current_model"] = "m"
    monkeypatch.setattr(server.client, "simulate",
                        lambda name, opts=None: {"Time": list(range(10)), "Values": [[12.0] * 10]})
    r = server.plecs_simulate(metrics=["steady_state", "ripple_pp"])
    assert r["ok"] and "metrics" in r
    assert abs(r["metrics"]["steady_state"] - 12.0) < 1e-9

    r2 = server.plecs_simulate()  # no metrics -> unchanged behaviour
    assert "metrics" not in r2
