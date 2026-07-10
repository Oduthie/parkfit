"""The empirical park-bucket model.

Design decisions (see docs/MODEL_CARD.md for the full rationale):

1. VISITING HITTERS ONLY. Home hitters are a non-random sample — rosters are
   built and approaches coached to exploit the home park — so including them
   contaminates park deltas with roster construction, and leaks the scored
   player's own home performance back into his score. Visiting hitters are
   approximately league-average by construction.

2. RESIDUAL FORMULATION. Each ball's residual = observed wOBA minus the
   league mean for its FINE bucket. Park effects are then averages of
   residuals, which removes bucket-mix confounding at every level of the
   hierarchy (a park doesn't look HR-friendly just because good hitters
   visit it, or because its visitors happen to pull the ball more).

3. HIERARCHICAL SHRINKAGE. Fine cells are thin exactly where the signal
   matters most (ExtremePull / high-EV / IdealAir), so shrinking them
   toward ZERO would rebuild the Vlad ≈ Paredes problem. Instead each
   level shrinks toward its parent:

       fine (park×hand×spray×LA×EV)
         -> coarse (park×hand×spray×LA)
           -> park×hand
             -> prior (0, or a supplied park factor)

   using standard partial pooling:
       shrunk = (n * cell_mean + k * parent) / (n + k)
"""

import numpy as np
import pandas as pd

from .constants import (
    COARSE_BUCKET_COLS,
    FINE_BUCKET_COLS,
    K_COARSE,
    K_FINE,
    K_PARK,
    MIN_LEAGUE_BUCKET_N,
)


def _pooled(cell_mean, cell_n, parent, k):
    return (cell_n * cell_mean + k * parent) / (cell_n + k)


def fit_park_bucket_model(
    bbe: pd.DataFrame,
    k_fine: float = K_FINE,
    k_coarse: float = K_COARSE,
    k_park: float = K_PARK,
    visiting_only: bool = True,
    zero_out_gb: bool = False,
    park_priors: dict | None = None,
):
    """Fit hierarchical park deltas.

    Returns
    -------
    deltas_fine : one row per park × fine bucket, with `final_delta` plus
        the intermediate levels for transparency.
    deltas_coarse : park × coarse bucket fallback table for scoring.
    deltas_parkhand : park × handedness fallback table.
    league_fine : league mean wOBA per fine bucket (the neutral baseline).
    """
    required = FINE_BUCKET_COLS + ["park", "observed_woba_value", "is_home_batter"]
    missing = [c for c in required if c not in bbe.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    df = bbe.dropna(subset=FINE_BUCKET_COLS + ["park", "observed_woba_value"]).copy()

    # --- League baseline: fit on ALL hitters (it's a neutral average and
    # benefits from the full sample). Park deltas: visiting hitters only.
    league_fine = (
        df.groupby(FINE_BUCKET_COLS, observed=True)
        .agg(
            league_bucket_woba=("observed_woba_value", "mean"),
            league_bucket_n=("observed_woba_value", "size"),
        )
        .reset_index()
    )
    league_fine["league_reliable"] = (
        league_fine["league_bucket_n"] >= MIN_LEAGUE_BUCKET_N
    )

    fit_df = df[~df["is_home_batter"]].copy() if visiting_only else df
    fit_df = fit_df.merge(league_fine, on=FINE_BUCKET_COLS, how="left")
    fit_df["resid"] = fit_df["observed_woba_value"] - fit_df["league_bucket_woba"]

    # --- Level 1: park × handedness, shrunk toward the prior.
    l1 = (
        fit_df.groupby(["park", "stand_bucket"], observed=True)
        .agg(l1_mean=("resid", "mean"), l1_n=("resid", "size"))
        .reset_index()
    )
    priors = park_priors or {}
    l1["prior"] = l1["park"].map(priors).fillna(0.0)
    l1["delta_l1"] = _pooled(l1["l1_mean"], l1["l1_n"], l1["prior"], k_park)

    # --- Level 2: park × coarse bucket, shrunk toward level 1.
    l2 = (
        fit_df.groupby(["park"] + COARSE_BUCKET_COLS, observed=True)
        .agg(l2_mean=("resid", "mean"), l2_n=("resid", "size"))
        .reset_index()
        .merge(l1[["park", "stand_bucket", "delta_l1"]],
               on=["park", "stand_bucket"], how="left")
    )
    l2["delta_l2"] = _pooled(l2["l2_mean"], l2["l2_n"], l2["delta_l1"], k_coarse)

    # --- Level 3: park × fine bucket, shrunk toward level 2.
    l3 = (
        fit_df.groupby(["park"] + FINE_BUCKET_COLS, observed=True)
        .agg(
            park_bucket_woba=("observed_woba_value", "mean"),
            l3_mean=("resid", "mean"),
            park_bucket_n=("resid", "size"),
        )
        .reset_index()
        .merge(l2[["park"] + COARSE_BUCKET_COLS + ["delta_l2"]],
               on=["park"] + COARSE_BUCKET_COLS, how="left")
        .merge(league_fine, on=FINE_BUCKET_COLS, how="left")
    )
    l3["final_delta"] = _pooled(
        l3["l3_mean"], l3["park_bucket_n"], l3["delta_l2"], k_fine
    )
    # If the league baseline itself is thin, damp the whole cell.
    l3.loc[~l3["league_reliable"].fillna(False), "final_delta"] *= (
        l3["league_bucket_n"] / MIN_LEAGUE_BUCKET_N
    ).clip(upper=1.0)
    l3["is_sparse"] = l3["park_bucket_n"] < MIN_LEAGUE_BUCKET_N

    # Ground balls: outcome variance there is mostly defense (a team
    # property), not park. Optionally zero them out; either way, run
    # diagnostics.gb_delta_check to show they are ~0.
    if zero_out_gb:
        l3.loc[l3["la_bucket"] == "GB", "final_delta"] = 0.0
        l2.loc[l2["la_bucket"] == "GB", "delta_l2"] = 0.0

    deltas_fine = l3
    deltas_coarse = l2[["park"] + COARSE_BUCKET_COLS + ["delta_l2", "l2_n"]]
    deltas_parkhand = l1[["park", "stand_bucket", "delta_l1", "l1_n"]]
    return deltas_fine, deltas_coarse, deltas_parkhand, league_fine
