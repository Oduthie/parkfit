"""Score player contact fingerprints against fitted park deltas.

A player's fingerprint is built from ALL of his batted balls (home and
road) — it describes what he produces. The park deltas were fit on
visiting hitters only — they describe what parks do. Keeping those two
samples separate is what prevents circularity.

Missing park×fine-bucket combinations fall back hierarchically
(fine -> coarse -> park×hand), never to an arbitrary zero.
"""

import numpy as np
import pandas as pd

from .constants import (
    COARSE_BUCKET_COLS,
    FINE_BUCKET_COLS,
    MIN_PLAYER_BBE,
    MIN_PLAYER_BBE_FULL,
)


def build_player_fingerprint(player_bbe: pd.DataFrame) -> pd.DataFrame:
    counts = (
        player_bbe.dropna(subset=FINE_BUCKET_COLS)
        .groupby(FINE_BUCKET_COLS, observed=True)
        .agg(player_bucket_n=("events", "size"))
        .reset_index()
    )
    counts["player_bucket_freq"] = (
        counts["player_bucket_n"] / counts["player_bucket_n"].sum()
    )
    return counts


def score_one_player(
    player_bbe: pd.DataFrame,
    deltas_fine: pd.DataFrame,
    deltas_coarse: pd.DataFrame,
    deltas_parkhand: pd.DataFrame,
    league_fine: pd.DataFrame,
):
    if player_bbe.empty:
        return pd.DataFrame(), pd.DataFrame()

    batter = player_bbe["batter"].iloc[0]
    name = player_bbe["batter_name"].iloc[0]
    stand_bucket = player_bbe["stand_bucket"].mode().iloc[0]

    fp = build_player_fingerprint(player_bbe)
    if fp.empty:
        return pd.DataFrame(), pd.DataFrame()

    # Neutral contact wOBA: fingerprint × league bucket means.
    fpl = fp.merge(
        league_fine[FINE_BUCKET_COLS + ["league_bucket_woba"]],
        on=FINE_BUCKET_COLS, how="left",
    )
    fpl["league_bucket_woba"] = fpl["league_bucket_woba"].fillna(
        league_fine["league_bucket_woba"].mean()
    )
    neutral = float((fpl["player_bucket_freq"] * fpl["league_bucket_woba"]).sum())

    park_rows, contrib_rows = [], []
    for park in sorted(deltas_fine["park"].unique()):
        fine_p = deltas_fine[deltas_fine["park"] == park]
        merged = fp.merge(
            fine_p[FINE_BUCKET_COLS + ["final_delta", "park_bucket_n"]],
            on=FINE_BUCKET_COLS, how="left",
        )
        # Hierarchical fallback for unseen cells.
        coarse_p = deltas_coarse[deltas_coarse["park"] == park]
        merged = merged.merge(
            coarse_p[COARSE_BUCKET_COLS + ["delta_l2"]],
            on=COARSE_BUCKET_COLS, how="left",
        )
        ph = deltas_parkhand[
            (deltas_parkhand["park"] == park)
            & (deltas_parkhand["stand_bucket"] == stand_bucket)
        ]
        ph_delta = float(ph["delta_l1"].iloc[0]) if not ph.empty else 0.0
        merged["delta_used"] = (
            merged["final_delta"]
            .fillna(merged["delta_l2"])
            .fillna(ph_delta)
        )
        merged["fallback_level"] = np.where(
            merged["final_delta"].notna(), "fine",
            np.where(merged["delta_l2"].notna(), "coarse", "park-hand"),
        )
        merged["park_bucket_n"] = merged["park_bucket_n"].fillna(0)
        merged["bucket_contribution"] = (
            merged["player_bucket_freq"] * merged["delta_used"]
        )

        fit_delta = float(merged["bucket_contribution"].sum())
        coverage = float(
            merged.loc[merged["fallback_level"] == "fine", "player_bucket_freq"].sum()
        )
        park_rows.append({
            "batter": batter,
            "batter_name": name,
            "stand_bucket": stand_bucket,
            "park": park,
            "neutral_contact_woba": neutral,
            "park_fit_delta": fit_delta,
            "projected_contact_woba": neutral + fit_delta,
            "model_coverage": coverage,
            "player_bbe": len(player_bbe),
        })
        merged["batter"] = batter
        merged["batter_name"] = name
        merged["park"] = park
        contrib_rows.append(merged)

    park_scores = pd.DataFrame(park_rows)
    park_scores["park_dependency_score"] = (
        park_scores["park_fit_delta"].max() - park_scores["park_fit_delta"].min()
    )
    park_scores["park_rank"] = (
        park_scores["park_fit_delta"].rank(ascending=False, method="min").astype(int)
    )
    park_scores = park_scores.sort_values("park_rank").reset_index(drop=True)
    contributions = pd.concat(contrib_rows, ignore_index=True)
    return park_scores, contributions


def score_all_players(
    bbe: pd.DataFrame,
    deltas_fine: pd.DataFrame,
    deltas_coarse: pd.DataFrame,
    deltas_parkhand: pd.DataFrame,
    league_fine: pd.DataFrame,
    min_bbe: int = MIN_PLAYER_BBE,
    keep_contributions: bool = True,
):
    """Score every batter with >= min_bbe batted balls. Keyed on MLBAM id."""
    counts = bbe.groupby("batter", observed=True).size()
    eligible = counts[counts >= min_bbe].index

    all_scores, all_contribs = [], []
    for i, batter in enumerate(eligible, 1):
        pbbe = bbe[bbe["batter"] == batter]
        scores, contribs = score_one_player(
            pbbe, deltas_fine, deltas_coarse, deltas_parkhand, league_fine
        )
        if scores.empty:
            continue
        all_scores.append(scores)
        if keep_contributions:
            all_contribs.append(contribs)
        if i % 50 == 0:
            print(f"  scored {i}/{len(eligible)} players")

    scores = pd.concat(all_scores, ignore_index=True)
    scores["confidence_tier"] = np.where(
        scores["player_bbe"] >= MIN_PLAYER_BBE_FULL, "full", "provisional"
    )
    contributions = (
        pd.concat(all_contribs, ignore_index=True)
        if all_contribs else pd.DataFrame()
    )
    return scores, contributions
