"""Fit hierarchical park deltas on visiting hitters.

Usage:  python scripts/02_fit_bucket_model.py
Input:  data/processed/bbe.parquet
Output: data/model/deltas_fine.parquet, deltas_coarse.parquet,
        deltas_parkhand.parquet, league_fine.parquet
"""

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from parkfit.diagnostics import gb_delta_check  # noqa: E402
from parkfit.model import fit_park_bucket_model  # noqa: E402


def main():
    bbe = pd.read_parquet(ROOT / "data" / "processed" / "bbe.parquet")
    print(f"Fitting on {len(bbe):,} batted balls "
          f"({(~bbe['is_home_batter']).sum():,} from visiting hitters)")

    d_fine, d_coarse, d_ph, league = fit_park_bucket_model(bbe)

    gb_delta_check(d_fine)

    model_dir = ROOT / "data" / "model"
    d_fine.to_parquet(model_dir / "deltas_fine.parquet", index=False)
    d_coarse.to_parquet(model_dir / "deltas_coarse.parquet", index=False)
    d_ph.to_parquet(model_dir / "deltas_parkhand.parquet", index=False)
    league.to_parquet(model_dir / "league_fine.parquet", index=False)
    print(f"\nSaved model tables -> {model_dir}")
    print(f"  fine cells: {len(d_fine):,} | sparse: {d_fine['is_sparse'].mean():.1%}")


if __name__ == "__main__":
    main()
