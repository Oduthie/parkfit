"""Contact bucketing: spray angle, EV, LA — all vectorized.

Spray is always expressed from the BATTER'S perspective:
    positive = pull side, negative = opposite field.
This is the invariant that lets RHH and LHH share bucket labels.
"""

import numpy as np
import pandas as pd

from .constants import (
    EV_BINS, EV_LABELS,
    LA_BINS, LA_LABELS,
    SPRAY_BINS, SPRAY_LABELS,
)

# Statcast hit-coordinate origin (home plate) in the hc_x/hc_y system.
HC_X_HOME = 125.42
HC_Y_HOME = 198.27


def _f64(series: pd.Series) -> np.ndarray:
    """Coerce any numeric-ish column (incl. nullable Float64) to plain
    float64 numpy with NaN for missing — pandas-3.0-proof."""
    return pd.to_numeric(series, errors="coerce").astype("float64").to_numpy()


def raw_spray_angle(hc_x: pd.Series, hc_y: pd.Series) -> pd.Series:
    """Field spray angle in degrees. 0 = straightaway CF,
    negative = LF side, positive = RF side. Directional bucketing only —
    this is NOT a trajectory or wall model."""
    x = _f64(hc_x) - HC_X_HOME
    y = HC_Y_HOME - _f64(hc_y)
    return pd.Series(np.degrees(np.arctan2(x, y)), index=hc_x.index)


def batter_perspective_spray(raw_angle: pd.Series, stand: pd.Series) -> pd.Series:
    """Flip the sign for RHH so that positive always means pull.

    RHH: pull = LF = negative raw angle  -> negate.
    LHH: pull = RF = positive raw angle  -> keep.
    """
    s = stand.astype(str).str.upper().to_numpy()
    angle = _f64(raw_angle)
    sign = np.where(s == "R", -1.0, np.where(s == "L", 1.0, np.nan))
    return pd.Series(angle * sign, index=raw_angle.index)


def add_contact_buckets(df: pd.DataFrame) -> pd.DataFrame:
    """Attach stand/spray/LA/EV buckets (fine) — coarse is the same minus EV."""
    out = df.copy()

    out["raw_spray_angle"] = raw_spray_angle(out["hc_x"], out["hc_y"])
    out["batter_spray_angle"] = batter_perspective_spray(
        out["raw_spray_angle"], out["stand"]
    )

    out["stand_bucket"] = (
        out["stand"].astype(str).str.upper().map({"R": "RHH", "L": "LHH"})
    )

    out["spray_bucket"] = pd.cut(
        _f64(out["batter_spray_angle"]), bins=SPRAY_BINS,
        labels=SPRAY_LABELS, include_lowest=True,
    ).astype("object")

    out["ev_bucket"] = pd.cut(
        _f64(out["launch_speed"]), bins=EV_BINS,
        labels=EV_LABELS, include_lowest=True,
    ).astype("object")

    out["la_bucket"] = pd.cut(
        _f64(out["launch_angle"]), bins=LA_BINS,
        labels=LA_LABELS, include_lowest=True,
    ).astype("object")

    return out