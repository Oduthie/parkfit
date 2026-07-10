"""Pull raw Statcast data from Baseball Savant into data/raw/.

Usage:  python scripts/00_pull_statcast.py
        python scripts/00_pull_statcast.py 2023 2025   (custom year range)

Pulls one season at a time in weekly chunks (Savant rejects big date
ranges), keeps only the columns the ParkFit pipeline needs, filters to
regular-season games, and saves one parquet per season. Safe to re-run:
seasons that already have a file are skipped.

Expect this to take a while — 20-40 minutes per season depending on
connection. Let it run.
"""

import sys
import time
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"

# Columns the pipeline needs (keeping only these cuts file size ~80%).
KEEP_COLS = [
    "game_pk", "game_date", "game_year", "game_type",
    "batter", "pitcher", "stand",
    "home_team", "away_team", "inning_topbot",
    "events", "type", "description",
    "launch_speed", "launch_angle", "hc_x", "hc_y",
    "woba_value", "woba_denom",
    "estimated_woba_using_speedangle",
]

# Generous season bounds; game_type filter removes spring/postseason.
SEASON_START = (3, 15)   # March 15
SEASON_END = (10, 5)     # October 5


def week_chunks(start: date, end: date):
    cur = start
    while cur <= end:
        stop = min(cur + timedelta(days=6), end)
        yield cur, stop
        cur = stop + timedelta(days=1)


def pull_season(year: int) -> pd.DataFrame:
    from pybaseball import statcast

    start = date(year, *SEASON_START)
    end = date(year, *SEASON_END)
    frames = []
    for a, b in week_chunks(start, end):
        for attempt in range(3):
            try:
                chunk = statcast(start_dt=a.isoformat(), end_dt=b.isoformat(),
                                 verbose=False)
                break
            except Exception as exc:
                wait = 20 * (attempt + 1)
                print(f"    {a} -> {b} failed ({exc}); retrying in {wait}s")
                time.sleep(wait)
        else:
            print(f"    {a} -> {b} FAILED after 3 tries — skipping this week, "
                  "note it and re-pull later")
            continue
        if chunk is not None and not chunk.empty:
            cols = [c for c in KEEP_COLS if c in chunk.columns]
            frames.append(chunk[cols])
            print(f"    {a} -> {b}: {len(chunk):,} pitches")
        time.sleep(2)  # be polite to Savant

    if not frames:
        return pd.DataFrame()
    season = pd.concat(frames, ignore_index=True)

    # Regular season only.
    if "game_type" in season.columns:
        before = len(season)
        season = season[season["game_type"] == "R"]
        print(f"  regular-season filter: {before:,} -> {len(season):,}")

    if "game_year" not in season.columns or season["game_year"].isna().all():
        season["game_year"] = year
    return season.reset_index(drop=True)


def main():
    start_year = int(sys.argv[1]) if len(sys.argv) > 1 else 2021
    end_year = int(sys.argv[2]) if len(sys.argv) > 2 else 2025

    try:
        from pybaseball import cache
        cache.enable()
    except Exception:
        pass

    RAW.mkdir(parents=True, exist_ok=True)
    for year in range(start_year, end_year + 1):
        out = RAW / f"statcast_{year}.parquet"
        if out.exists():
            print(f"{year}: already exists, skipping ({out.name})")
            continue
        print(f"\n=== Pulling {year} ===")
        season = pull_season(year)
        if season.empty:
            print(f"{year}: nothing pulled — check connection")
            continue
        season.to_parquet(out, index=False)
        print(f"{year}: saved {len(season):,} rows -> {out.name}")

    print("\nDone. Now run: python scripts/01_build_training_data.py")


if __name__ == "__main__":
    main()