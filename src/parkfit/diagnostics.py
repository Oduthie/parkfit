"""Diagnostics: profiles, archetypes, player comparison, GB sanity check."""

import pandas as pd

from .constants import FINE_BUCKET_COLS, MIN_PLAYER_BBE


def assign_archetype(row) -> str:
    pull_air = row.get("pull_air_rate", 0)
    oppo_air = row.get("oppo_air_rate", 0)
    hard_hit = row.get("hard_hit_rate", 0)
    avg_ev = row.get("avg_ev", 0)
    if pull_air >= 0.22 and oppo_air <= 0.08:
        return "Pull-Air Dependent"
    if hard_hit >= 0.48 and oppo_air >= 0.08:
        return "All-Fields Impact"
    if avg_ev >= 92 and hard_hit >= 0.45:
        return "High-EV Power"
    if pull_air >= 0.18:
        return "Pull-Side Air"
    if oppo_air >= 0.11:
        return "Oppo/Gap Air"
    return "Balanced Contact"


def build_player_profiles(bbe: pd.DataFrame, min_bbe: int = MIN_PLAYER_BBE):
    df = bbe.copy()
    df["is_air"] = df["launch_angle"] >= 10
    df["is_pull"] = df["spray_bucket"].isin(["Pull", "ExtremePull"])
    df["is_oppo"] = df["spray_bucket"].isin(["Oppo", "ExtremeOppo"])
    df["is_hard"] = df["launch_speed"] >= 95
    df["is_hr_candidate"] = (
        (df["launch_speed"] >= 95) & (df["launch_angle"].between(20, 40))
    )
    df["is_pull_air"] = df["is_pull"] & df["is_air"]
    df["is_oppo_air"] = df["is_oppo"] & df["is_air"]

    profiles = (
        df.groupby(["batter", "batter_name", "stand_bucket"], observed=True)
        .agg(
            bbe=("events", "size"),
            avg_ev=("launch_speed", "mean"),
            avg_la=("launch_angle", "mean"),
            hard_hit_rate=("is_hard", "mean"),
            pull_air_rate=("is_pull_air", "mean"),
            oppo_air_rate=("is_oppo_air", "mean"),
            hr_candidate_rate=("is_hr_candidate", "mean"),
            observed_contact_woba=("observed_woba_value", "mean"),
        )
        .reset_index()
    )
    profiles = profiles[profiles["bbe"] >= min_bbe].copy()
    profiles["archetype"] = profiles.apply(assign_archetype, axis=1)
    return profiles


def compare_players(scores, profiles, player_a: str, player_b: str):
    """The smell test. NOTE: this is a diagnostic, not a tuning target —
    k values are chosen by split-half stability, never by iterating until
    this comparison 'looks right'."""
    a_hit = scores[scores["batter_name"].str.contains(player_a, case=False, na=False)]
    b_hit = scores[scores["batter_name"].str.contains(player_b, case=False, na=False)]
    if a_hit.empty or b_hit.empty:
        print("Could not find one of the players.")
        return None

    a_name, b_name = a_hit["batter_name"].iloc[0], b_hit["batter_name"].iloc[0]
    a = scores[scores["batter_name"] == a_name].sort_values("park")
    b = scores[scores["batter_name"] == b_name].sort_values("park")

    merged = a[["park", "park_fit_delta", "projected_contact_woba", "park_rank"]].merge(
        b[["park", "park_fit_delta", "projected_contact_woba", "park_rank"]],
        on="park", suffixes=("_a", "_b"),
    )
    delta_corr = merged["park_fit_delta_a"].corr(merged["park_fit_delta_b"])
    woba_corr = merged["projected_contact_woba_a"].corr(
        merged["projected_contact_woba_b"]
    )
    top5_a = set(a.nlargest(5, "park_fit_delta")["park"])
    top5_b = set(b.nlargest(5, "park_fit_delta")["park"])

    print("\nPLAYER COMPARISON")
    print("-----------------")
    print("Player A:", a_name, "| Player B:", b_name)
    print("Park Fit Delta correlation:", round(delta_corr, 3))
    print("Projected Contact wOBA correlation:", round(woba_corr, 3))
    print("Top-5 park overlap:", sorted(top5_a & top5_b))
    print(
        "Dependency scores:",
        round(a["park_dependency_score"].iloc[0], 4), "vs",
        round(b["park_dependency_score"].iloc[0], 4),
    )
    prof = profiles[profiles["batter_name"].isin([a_name, b_name])][[
        "batter_name", "bbe", "avg_ev", "avg_la", "hard_hit_rate",
        "pull_air_rate", "oppo_air_rate", "hr_candidate_rate", "archetype",
    ]]
    print("\nProfiles:")
    print(prof.to_string(index=False))
    print("\nPark comparison:")
    print(merged.sort_values("park_fit_delta_a", ascending=False).to_string(index=False))
    return merged


def top_bucket_contributors(contributions, batter_name: str, park: str, n: int = 10):
    sub = contributions[
        (contributions["batter_name"] == batter_name)
        & (contributions["park"] == park)
    ].copy()
    if sub.empty:
        return sub
    sub["abs_contribution"] = sub["bucket_contribution"].abs()
    cols = FINE_BUCKET_COLS + [
        "player_bucket_n", "player_bucket_freq", "delta_used",
        "bucket_contribution", "park_bucket_n", "fallback_level",
    ]
    return sub.sort_values("abs_contribution", ascending=False)[cols].head(n)


def gb_delta_check(deltas_fine: pd.DataFrame):
    """Ground-ball park deltas should be ~0 (defense is a team property,
    not a park property). If they aren't, something is leaking."""
    gb = deltas_fine[deltas_fine["la_bucket"] == "GB"]
    air = deltas_fine[deltas_fine["la_bucket"].isin(["IdealAir", "HighAir"])]
    print("\nGB vs air park-delta dispersion (std of final_delta):")
    print(f"  GB:  {gb['final_delta'].std():.4f}   (want: small)")
    print(f"  Air: {air['final_delta'].std():.4f}  (want: clearly larger)")
    return gb["final_delta"].describe()
