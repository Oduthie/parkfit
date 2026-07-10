"""Score every eligible hitter in every park.

Usage:  python scripts/03_score_players.py
Input:  data/processed/bbe.parquet + data/model/*
Output: data/output/park_scores.parquet, bucket_contributions.parquet,
        player_profiles.parquet
"""

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from parkfit.diagnostics import build_player_profiles  # noqa: E402
from parkfit.score import score_all_players  # noqa: E402


def main():
    bbe = pd.read_parquet(ROOT / "data" / "processed" / "bbe.parquet")
    model_dir = ROOT / "data" / "model"
    d_fine = pd.read_parquet(model_dir / "deltas_fine.parquet")
    d_coarse = pd.read_parquet(model_dir / "deltas_coarse.parquet")
    d_ph = pd.read_parquet(model_dir / "deltas_parkhand.parquet")
    league = pd.read_parquet(model_dir / "league_fine.parquet")

    scores, contributions = score_all_players(bbe, d_fine, d_coarse, d_ph, league)
    profiles = build_player_profiles(bbe)

    out = ROOT / "data" / "output"
    scores.to_parquet(out / "park_scores.parquet", index=False)
    contributions.to_parquet(out / "bucket_contributions.parquet", index=False)
    profiles.to_parquet(out / "player_profiles.parquet", index=False)
    print(f"\nScored {scores['batter'].nunique()} players -> {out}")


if __name__ == "__main__":
    main()
