"""Validation. Run this BEFORE looking at any named-player diagnostic —
k_fine is chosen here, by split-half stability, so the Vlad/Paredes
comparison stays evidence rather than becoming a tuning target.

Usage:
  python scripts/05_validation.py tune       # k_fine grid search
  python scripts/05_validation.py splithalf  # stability at current k
  python scripts/05_validation.py holdout 2021 2022 2023 -- 2024
"""

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from parkfit.validation import (  # noqa: E402
    season_holdout,
    split_half_validation,
    tune_k_fine,
)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "splithalf"
    bbe = pd.read_parquet(ROOT / "data" / "processed" / "bbe.parquet")

    if mode == "tune":
        summary = tune_k_fine(bbe)
        summary.to_csv(ROOT / "data" / "output" / "k_tuning.csv", index=False)
    elif mode == "holdout":
        args = sys.argv[2:]
        split = args.index("--")
        train_years = [int(y) for y in args[:split]]
        test_year = int(args[split + 1])
        season_holdout(bbe, train_years, test_year)
    else:
        val = split_half_validation(bbe)
        val.to_csv(ROOT / "data" / "output" / "split_half.csv", index=False)
        print("\nLowest-stability players (interpret their scores cautiously):")
        print(val.tail(10).to_string(index=False))


if __name__ == "__main__":
    main()
