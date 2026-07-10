"""One-off: shrink bucket_contributions.parquet for cloud deployment.
Keeps only the rows the app displays: top 12 contributors per player-park,
plus the top 3 non-GB rows (used for the 'primary driver' labels).
"""

from pathlib import Path
import pandas as pd

P = Path("data/output/bucket_contributions.parquet")
df = pd.read_parquet(P)
print(f"before: {len(df):,} rows")

cols = ["batter", "batter_name", "park", "spray_bucket", "la_bucket",
        "ev_bucket", "player_bucket_n", "player_bucket_freq", "delta_used",
        "bucket_contribution", "park_bucket_n", "fallback_level"]
df = df[[c for c in cols if c in df.columns]].copy()

df["abs_c"] = df["bucket_contribution"].abs()
grp = df.groupby(["batter_name", "park"], observed=True)["abs_c"]
df["rank_all"] = grp.rank(ascending=False, method="first")

nongb = df["la_bucket"] != "GB"
df["rank_air"] = (df[nongb].groupby(["batter_name", "park"], observed=True)["abs_c"]
                  .rank(ascending=False, method="first"))

keep = (df["rank_all"] <= 12) | (df["rank_air"] <= 3)
out = df[keep].drop(columns=["abs_c", "rank_all", "rank_air"])
print(f"after:  {len(out):,} rows")

out.to_parquet(P, index=False)
print(f"saved -> {P}")