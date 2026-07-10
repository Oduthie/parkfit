"""Validation.

The shrinkage constant k_fine is chosen HERE, by out-of-sample stability,
before anyone looks at a named-player comparison. That ordering is what
makes the Vlad/Paredes diagnostic evidence instead of a tuning target.
"""

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from .model import fit_park_bucket_model
from .score import score_all_players


def _fit_and_score(bbe, min_bbe, **fit_kwargs):
    d_fine, d_coarse, d_ph, league = fit_park_bucket_model(bbe, **fit_kwargs)
    scores, _ = score_all_players(
        bbe, d_fine, d_coarse, d_ph, league,
        min_bbe=min_bbe, keep_contributions=False,
    )
    return scores


def split_half_validation(bbe: pd.DataFrame, min_bbe: int = 80,
                          min_parks: int = 10, **fit_kwargs):
    """Fit on even game_pk, fit on odd game_pk, compare each player's park
    rankings across the two independent fits (Spearman). Stable rankings
    mean the park-fit signal is real, not sample noise."""
    df = bbe.dropna(subset=["game_pk"]).copy()
    even = df[df["game_pk"].astype(int) % 2 == 0]
    odd = df[df["game_pk"].astype(int) % 2 == 1]

    even_scores = _fit_and_score(even, min_bbe, **fit_kwargs)
    odd_scores = _fit_and_score(odd, min_bbe, **fit_kwargs)

    players = sorted(set(even_scores["batter"]) & set(odd_scores["batter"]))
    rows = []
    for batter in players:
        a = even_scores.loc[even_scores["batter"] == batter, ["park", "park_fit_delta"]]
        b = odd_scores.loc[odd_scores["batter"] == batter, ["park", "park_fit_delta"]]
        m = a.merge(b, on="park", suffixes=("_even", "_odd"))
        if len(m) >= min_parks:
            rho, p = spearmanr(m["park_fit_delta_even"], m["park_fit_delta_odd"])
            rows.append({
                "batter": batter,
                "batter_name": even_scores.loc[
                    even_scores["batter"] == batter, "batter_name"
                ].iloc[0],
                "spearman_rho": rho, "p_value": p, "parks": len(m),
            })
    out = pd.DataFrame(rows).dropna()
    print(f"Players tested: {len(out)}")
    if out.empty:
        print(f"No players with >= {min_parks} common parks across halves — "
              "lower min_parks or min_bbe.")
        return out
    print(f"Median Spearman rho: {out['spearman_rho'].median():.3f}")
    return out.sort_values("spearman_rho", ascending=False)


def tune_k_fine(bbe: pd.DataFrame, k_grid=(20, 40, 60, 100, 150, 250),
                min_bbe: int = 80):
    """Pick k_fine by maximizing median split-half stability. Larger k also
    shrinks the dependency signal toward zero, so among near-tied stability
    values, prefer the smallest k (report both stability and the spread of
    dependency scores)."""
    results = []
    for k in k_grid:
        print(f"\n--- k_fine = {k} ---")
        val = split_half_validation(bbe, min_bbe=min_bbe, k_fine=float(k))
        results.append({
            "k_fine": k,
            "median_rho": val["spearman_rho"].median() if not val.empty else np.nan,
            "p25_rho": val["spearman_rho"].quantile(0.25) if not val.empty else np.nan,
            "players": len(val),
        })
    summary = pd.DataFrame(results)
    print("\nK TUNING SUMMARY")
    print(summary.to_string(index=False))
    return summary


def season_holdout(bbe: pd.DataFrame, train_years, test_year, min_bbe: int = 80):
    """Directional stability of park deltas across seasons: fit on
    train_years and test_year separately, correlate final_delta cell-wise
    and player park rankings."""
    train = bbe[bbe["game_year"].isin(train_years)]
    test = bbe[bbe["game_year"] == test_year]

    tr_fine, *_ = fit_park_bucket_model(train)
    te_fine, *_ = fit_park_bucket_model(test)
    key = ["park", "stand_bucket", "spray_bucket", "la_bucket", "ev_bucket"]
    m = tr_fine[key + ["final_delta"]].merge(
        te_fine[key + ["final_delta"]], on=key, suffixes=("_train", "_test")
    )
    rho, _ = spearmanr(m["final_delta_train"], m["final_delta_test"])
    print(f"Cell-wise delta Spearman (train {train_years} vs {test_year}): {rho:.3f}")
    return m


def park_switch_validation(scores: pd.DataFrame, switches: pd.DataFrame):
    """`switches`: hand-built table with columns
        batter, from_park, to_park, actual_contact_woba_change
    Compares model-predicted fit change against the observed change.
    Expect a weak-to-moderate positive relationship at best — aging, role,
    approach, and injury all move the observed number. Say so in the writeup."""
    rows = []
    for _, r in switches.iterrows():
        s = scores[scores["batter"] == r["batter"]]
        f = s.loc[s["park"] == r["from_park"], "park_fit_delta"]
        t = s.loc[s["park"] == r["to_park"], "park_fit_delta"]
        if f.empty or t.empty:
            continue
        rows.append({
            "batter": r["batter"],
            "predicted_change": float(t.iloc[0]) - float(f.iloc[0]),
            "actual_change": r["actual_contact_woba_change"],
        })
    out = pd.DataFrame(rows)
    if len(out) >= 5:
        rho, p = spearmanr(out["predicted_change"], out["actual_change"])
        print(f"Park-switch Spearman: {rho:.3f} (p={p:.3f}, n={len(out)})")
    return out