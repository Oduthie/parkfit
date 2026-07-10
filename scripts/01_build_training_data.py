"""Build the prepared batted-ball table from raw Statcast pulls, plus the
player extras the site needs: K% / BB% / HR% per hitter, empirical park K%,
each hitter's current home park, and his most recent season (for the
active-players filter).

Usage:  python scripts/01_build_training_data.py
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from parkfit.buckets import add_contact_buckets  # noqa: E402
from parkfit.data import (  # noqa: E402
    add_observed_woba,
    add_park_and_home_flag,
    attach_batter_names,
    filter_batted_balls,
    load_raw,
    missingness_audit,
)

K_EVENTS = {"strikeout", "strikeout_double_play"}
BB_EVENTS = {"walk"}


def build_pa_rates(raw: pd.DataFrame) -> pd.DataFrame:
    """Per-batter K% and BB% from ALL plate appearances in the raw pull
    (rows where `events` is set mark the end of a PA)."""
    pa = raw.dropna(subset=["events"]).copy()
    pa["is_k"] = pa["events"].isin(K_EVENTS)
    pa["is_bb"] = pa["events"].isin(BB_EVENTS)
    out = (
        pa.groupby("batter", observed=True)
        .agg(pa=("events", "size"), k_pct=("is_k", "mean"), bb_pct=("is_bb", "mean"))
        .reset_index()
    )
    out["k_pct"] *= 100
    out["bb_pct"] *= 100
    return out


def build_park_k(raw: pd.DataFrame) -> pd.DataFrame:
    """Empirical K% by park (descriptive display only — the model itself
    remains contact-only)."""
    pa = raw.dropna(subset=["events"]).copy()
    pa = add_park_and_home_flag(pa)
    pa["is_k"] = pa["events"].isin(K_EVENTS)
    out = (
        pa.groupby("park", observed=True)
        .agg(park_k_pct=("is_k", "mean"), park_pa=("is_k", "size"))
        .reset_index()
    )
    out["park_k_pct"] *= 100
    return out


def build_home_parks(bbe: pd.DataFrame, recent_n: int = 60) -> pd.DataFrame:
    """Current home park per batter: the modal park of his most recent
    home-game batted balls. Handles midseason trades for free."""
    home = bbe[bbe["is_home_batter"]].copy()
    if "game_date" in home.columns:
        home = home.sort_values("game_date")
    rows = []
    for batter, sub in home.groupby("batter", observed=True):
        recent = sub.tail(recent_n)
        if recent.empty:
            continue
        rows.append({"batter": batter, "home_park": recent["park"].mode().iloc[0]})
    return pd.DataFrame(rows)


def build_last_year(raw: pd.DataFrame) -> pd.DataFrame:
    """Most recent season each batter appeared in — powers the 'active
    players only' filter in the app."""
    return (raw.dropna(subset=["batter"])
            .groupby("batter", observed=True)
            .agg(last_year=("game_year", "max"))
            .reset_index())


def build_hr_rates(bbe: pd.DataFrame) -> pd.DataFrame:
    out = (
        bbe.assign(is_hr=bbe["events"].eq("home_run"))
        .groupby("batter", observed=True)
        .agg(hr_pct=("is_hr", "mean"))
        .reset_index()
    )
    out["hr_pct"] *= 100
    return out


def main():
    print("Loading raw files...")
    raw = load_raw(ROOT / "data" / "raw")

    print("Building PA rates (K%, BB%) and park K environments...")
    pa_rates = build_pa_rates(raw)
    park_k = build_park_k(raw)

    print("Filtering to batted-ball events...")
    bbe = filter_batted_balls(raw)
    print(f"  {len(bbe):,} batted balls")
    bbe = add_park_and_home_flag(bbe)
    bbe = add_observed_woba(bbe)
    print("Bucketing contact...")
    bbe = add_contact_buckets(bbe)
    print("Resolving batter names...")
    bbe = attach_batter_names(bbe)

    print("Detecting home parks...")
    home_parks = build_home_parks(bbe)
    hr_rates = build_hr_rates(bbe)

    extras = pa_rates.merge(hr_rates, on="batter", how="outer") \
                     .merge(home_parks, on="batter", how="left") \
                     .merge(build_last_year(raw), on="batter", how="left")

    print("\nMISSINGNESS AUDIT (check home_run spray_missing_rate first):")
    audit = missingness_audit(bbe)
    print(audit.to_string(index=False))

    (ROOT / "data" / "processed").mkdir(parents=True, exist_ok=True)
    (ROOT / "data" / "output").mkdir(parents=True, exist_ok=True)
    audit.to_csv(ROOT / "data" / "processed" / "missingness_audit.csv", index=False)
    bbe.to_parquet(ROOT / "data" / "processed" / "bbe.parquet", index=False)
    extras.to_parquet(ROOT / "data" / "output" / "player_extras.parquet", index=False)
    park_k.to_parquet(ROOT / "data" / "output" / "park_k.parquet", index=False)
    print(f"\nSaved {len(bbe):,} batted balls, extras for {len(extras):,} batters, "
          f"K% for {len(park_k)} parks")


if __name__ == "__main__":
    main()