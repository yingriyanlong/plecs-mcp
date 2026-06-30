"""Waveform shaping + metric extraction (numpy). Returns scalars, not arrays."""
from __future__ import annotations

import numpy as np


def to_signals(time: list, values: list) -> tuple[list, list]:
    """Normalise PLECS simulate() output to time + [signal][sample].

    PLECS may return Values as [signal][sample] or [sample][signal]; we detect
    orientation from the time length and transpose if needed.
    """
    t = list(time)
    if not values:
        return t, []
    arr = np.asarray(values, dtype=float)
    if arr.ndim == 1:
        arr = arr.reshape(1, -1)
    elif arr.ndim == 2 and arr.shape[0] == len(t) and arr.shape[1] != len(t):
        arr = arr.T  # was [sample][signal]
    return t, arr.tolist()


def _ref(steady: float | None, target: float | None) -> float | None:
    return target if target is not None else steady


def _settling_time(t, y, ref, band=0.02):
    if ref is None or ref == 0:
        return None
    tol = abs(ref) * band
    outside = np.where(np.abs(y - ref) > tol)[0]
    if outside.size == 0:
        return float(t[0])
    last = outside[-1]
    return float(t[min(last + 1, len(t) - 1)])


def _rise_time(t, y, ref):
    if ref is None or ref == 0:
        return None
    lo, hi = 0.1 * ref, 0.9 * ref
    i_lo = np.argmax(y >= lo)
    i_hi = np.argmax(y >= hi)
    if i_hi <= i_lo:
        return None
    return float(t[i_hi] - t[i_lo])


def metrics(time, values, names=None, target=None, steady_frac=0.2):
    names = names or ["steady_state", "ripple_pp", "mean", "rms", "min", "max"]
    t = np.asarray(time, dtype=float)
    y = np.asarray(values, dtype=float)
    n = y.size
    i = int(n * (1 - steady_frac))
    ys = y[i:] if n else y
    steady = float(np.mean(ys)) if ys.size else None
    out: dict[str, float | None] = {}
    for m in names:
        if m == "steady_state":
            out[m] = steady
        elif m == "ripple_pp":
            out[m] = float(np.ptp(ys)) if ys.size else None
        elif m == "mean":
            out[m] = float(np.mean(ys)) if ys.size else None
        elif m == "rms":
            out[m] = float(np.sqrt(np.mean(y ** 2))) if n else None
        elif m == "min":
            out[m] = float(np.min(y)) if n else None
        elif m == "max":
            out[m] = float(np.max(y)) if n else None
        elif m == "overshoot":
            ref = _ref(steady, target)
            out[m] = float((np.max(y) - ref) / ref * 100) if ref else None
        elif m == "settling_time":
            out[m] = _settling_time(t, y, _ref(steady, target))
        elif m == "rise_time":
            out[m] = _rise_time(t, y, _ref(steady, target))
        else:
            out[m] = None
    return out


def bode(F, Gr, Gi):
    """Turn a PLECS frequency-response result into magnitude(dB)/phase(deg) plus
    DC gain, gain-crossover frequency and phase margin."""
    import math
    f = np.asarray(F, dtype=float)
    gr = np.asarray(Gr[0] if (Gr and isinstance(Gr[0], list)) else Gr, dtype=float)
    gi = np.asarray(Gi[0] if (Gi and isinstance(Gi[0], list)) else Gi, dtype=float)
    mag_db = 20 * np.log10(np.sqrt(gr ** 2 + gi ** 2))
    phase = np.degrees(np.unwrap(np.arctan2(gi, gr)))
    fc = pm = None
    for i in range(1, len(f)):
        if mag_db[i - 1] > 0 >= mag_db[i]:
            t = (0 - mag_db[i - 1]) / (mag_db[i] - mag_db[i - 1])
            fc = float(10 ** (math.log10(f[i - 1]) + t * (math.log10(f[i]) - math.log10(f[i - 1]))))
            pm = float(180 + (phase[i - 1] + t * (phase[i] - phase[i - 1])))
            break
    return {"f": f.tolist(), "mag_db": mag_db.tolist(), "phase_deg": phase.tolist(),
            "dc_gain_db": float(mag_db[0]), "gain_crossover_hz": fc, "phase_margin_deg": pm}
