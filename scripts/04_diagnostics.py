"""Run the smell tests. Only run AFTER k_fine is locked in by 05_validation.

Usage:  python scripts/04_diagnostics.py "Guerrero" "Paredes"
"""

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from parkfit.diagnostics import compare_players, top_bucket_contributors  # noqa: E402


def main():
    player_a = sys.argv[1] if len(sys.argv) > 1 else "Guerrero"
    player_b = sys.argv[2] if len(sys.argv) > 2 else "Paredes"

    out = ROOT / "data" / "output"
    scores = pd.read_parquet(out / "park_scores.parquet")
    profiles = pd.read_parquet(out / "player_profiles.parquet")
    contributions = pd.read_parquet(out / "bucket_contributions.parquet")

    compare_players(scores, profiles, player_a, player_b)

    # Why does player B fit his best park?
    b = scores[scores["batter_name"].str.contains(player_b, case=False, na=False)]
    if not b.empty:
        name = b["batter_name"].iloc[0]
        best_park = b.sort_values("park_fit_delta", ascending=False)["park"].iloc[0]
        print(f"\nTop bucket contributors: {name} @ {best_park}")
        print(top_bucket_contributors(contributions, name, best_park)
              .to_string(index=False))


if __name__ == "__main__":
    main()
