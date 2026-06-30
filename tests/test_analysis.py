from plecs_mcp.results.analysis import bode


def test_bode_basic():
    # |G| = 10, 1, 0.1 at f = 1, 10, 100 -> 20, 0, -20 dB; crossover at 10 Hz.
    b = bode([1, 10, 100], [[10.0, 1.0, 0.1]], [[0.0, 0.0, 0.0]])
    assert round(b["dc_gain_db"], 3) == 20.0
    assert abs(b["mag_db"][1]) < 1e-6
    assert abs(b["gain_crossover_hz"] - 10.0) < 1e-6
    assert abs(b["phase_margin_deg"] - 180.0) < 1e-6
    assert isinstance(b["gain_crossover_hz"], float)
