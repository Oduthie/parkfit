"""Data ingestion and preparation.

Input: raw Statcast pitch-level pulls (pybaseball.statcast naming) dropped
into data/raw/ as .parquet or .csv. Output: a single prepared batted-ball
table with buckets, park labels, home-batter flags, and observed wOBA.
"""

from pathlib import Path

import numpy as np
import pandas as pd

from .buckets import add_contact_buckets
from .constants import (
    BATTED_BALL_EVENTS,
    EVENT_WOBA_FALLBACK,
    NEUTRAL_SITE_GAME_PKS,
    REQUIRED_RAW_COLUMNS,
    get_park,
)


def load_raw(raw_dir: str | Path) -> pd.DataFrame:
    """Load and concatenate every parquet/csv in data/raw."""
    raw_dir = Path(raw_dir)
    files = sorted(raw_dir.glob("*.parquet")) + sorted(raw_dir.glob("*.csv"))
    if not files:
        raise FileNotFoundError(f"No .parquet or .csv files in {raw_dir}")
    frames = []
    for f in files:
        df = pd.read_parquet(f) if f.suffix == ".parquet" else pd.read_csv(
            f, low_memory=False
        )
        frames.append(df)
        print(f"  loaded {f.name}: {len(df):,} rows")
    out = pd.concat(frames, ignore_index=True)
    missing = [c for c in REQUIRED_RAW_COLUMNS if c not in out.columns]
    if missing:
        raise ValueError(f"Raw data missing required columns: {missing}")
    return out


def filter_batted_balls(df: pd.DataFrame) -> pd.DataFrame:
    """Keep pitch rows that ended in a tracked batted-ball event."""
    out = df.copy()
    if "type" in out.columns:
        out = out[out["type"] == "X"]
    out = out[out["events"].isin(BATTED_BALL_EVENTS)]
    if NEUTRAL_SITE_GAME_PKS:
        out = out[~out["game_pk"].isin(NEUTRAL_SITE_GAME_PKS)]
    return out.reset_index(drop=True)


def add_park_and_home_flag(df: pd.DataFrame) -> pd.DataFrame:
    """Park label from home_team + season (era-aware); home-batter flag
    from inning half — bottom of the inning means the home team is batting,
    so no roster join is needed and midseason trades are handled for free."""
    out = df.copy()
    out["park"] = [
        get_park(t, int(y)) for t, y in zip(out["home_team"], out["game_year"])
    ]
    out["is_home_batter"] = (
        out["inning_topbot"].astype(str).str.upper().str.startswith("BOT")
    )
    return out


def add_observed_woba(df: pd.DataFrame) -> pd.DataFrame:
    """Prefer Statcast's woba_value; fall back to approximate event weights.
    Reports fallback usage so scale drift is visible, not silent."""
    out = df.copy()
    if "woba_value" in out.columns:
        out["observed_woba_value"] = pd.to_numeric(
            out["woba_value"], errors="coerce"
        )
    else:
        out["observed_woba_value"] = np.nan
    fallback = out["events"].map(EVENT_WOBA_FALLBACK)
    n_fallback = int(out["observed_woba_value"].isna().sum())
    out["observed_woba_value"] = out["observed_woba_value"].fillna(fallback)
    print(
        f"  observed wOBA: {len(out) - n_fallback:,} from Statcast, "
        f"{n_fallback:,} from fallback weights "
        f"({n_fallback / max(len(out), 1):.1%})"
    )
    return out


def attach_batter_names(df: pd.DataFrame) -> pd.DataFrame:
    """Raw Statcast `player_name` is the PITCHER on pitch-level rows.
    Resolve batter IDs to names via pybaseball; key everything on `batter`
    (MLBAM id) regardless, and disambiguate duplicate display names with
    the id in parentheses (the Max Muncy rule)."""
    out = df.copy()
    try:
        from pybaseball import playerid_reverse_lookup

        ids = out["batter"].dropna().astype(int).unique()
        lookup = playerid_reverse_lookup(list(ids), key_type="mlbam")
        lookup["batter_name"] = (
            lookup["name_first"].str.title() + " " + lookup["name_last"].str.title()
        )
        name_map = dict(zip(lookup["key_mlbam"], lookup["batter_name"]))
        out["batter_name"] = out["batter"].map(name_map)
    except Exception as exc:  # offline / pybaseball absent
        print(f"  batter-name lookup unavailable ({exc}); using ids as names")
        out["batter_name"] = "ID " + out["batter"].astype(int).astype(str)

    out["batter_name"] = out["batter_name"].fillna(
        "ID " + out["batter"].astype(int).astype(str)
    )
    dupes = (
        out[["batter", "batter_name"]].drop_duplicates()
        .groupby("batter_name")["batter"].nunique()
    )
    ambiguous = set(dupes[dupes > 1].index)
    if ambiguous:
        mask = out["batter_name"].isin(ambiguous)
        out.loc[mask, "batter_name"] = (
            out.loc[mask, "batter_name"]
            + " (" + out.loc[mask, "batter"].astype(int).astype(str) + ")"
        )
        print(f"  disambiguated duplicate names: {sorted(ambiguous)}")
    return out


def prepare_bbe(raw_dir: str | Path) -> pd.DataFrame:
    """Full pipeline: load -> filter -> park/home flags -> wOBA -> buckets -> names."""
    print("Loading raw files...")
    df = load_raw(raw_dir)
    print("Filtering to batted-ball events...")
    df = filter_batted_balls(df)
    print(f"  {len(df):,} batted balls")
    df = add_park_and_home_flag(df)
    df = add_observed_woba(df)
    print("Bucketing contact...")
    df = add_contact_buckets(df)
    print("Resolving batter names...")
    df = attach_batter_names(df)
    return df


def missingness_audit(bbe: pd.DataFrame) -> pd.DataFrame:
    """Spray-bucket NaN rate BY EVENT TYPE. The critical row is home_run:
    Statcast hit coordinates are landing/fielded positions and can be
    missing or unreliable on HRs. If HR spray missingness is material,
    the most park-sensitive event class silently drops out of the model."""
    audit = (
        bbe.assign(spray_missing=bbe["spray_bucket"].isna())
        .groupby("events", observed=True)
        .agg(
            n=("events", "size"),
            spray_missing_rate=("spray_missing", "mean"),
            ev_missing_rate=("launch_speed", lambda s: s.isna().mean()),
            la_missing_rate=("launch_angle", lambda s: s.isna().mean()),
            woba_missing_rate=("observed_woba_value", lambda s: s.isna().mean()),
        )
        .sort_values("n", ascending=False)
        .reset_index()
    )
    hr = audit[audit["events"] == "home_run"]
    if not hr.empty and float(hr["spray_missing_rate"].iloc[0]) > 0.05:
        print(
            "\n*** WARNING: home_run spray missingness = "
            f"{float(hr['spray_missing_rate'].iloc[0]):.1%}. "
            "Impute or document before trusting park deltas. ***"
        )
    return audit
