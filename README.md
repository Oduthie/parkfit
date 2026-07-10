# ParkFit — empirical player-park fit

Player-specific park fit from historical Statcast contact-shape outcomes.
See `docs/MODEL_CARD.md` for design decisions and limitations.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Data

Drop raw Statcast pulls (pybaseball column naming) into `data/raw/` as
`.parquet` or `.csv`. Multiple files are concatenated. Required columns:
`game_pk, game_year, batter, stand, home_team, inning_topbot, events, type,
launch_speed, launch_angle, hc_x, hc_y` (plus `woba_value` strongly preferred).

## Run order

```bash
python scripts/01_build_training_data.py   # prep + missingness audit
python scripts/02_fit_bucket_model.py      # fit park deltas (visiting-only)
python scripts/05_validation.py tune       # choose k_fine BY STABILITY
# -> set K_FINE in src/parkfit/constants.py, then re-run 02
python scripts/03_score_players.py         # score all hitters
python scripts/05_validation.py splithalf  # final stability report
python scripts/04_diagnostics.py "Guerrero" "Paredes"  # smell tests LAST
streamlit run app.py
```

The ordering matters: shrinkage is tuned by out-of-sample stability
**before** any named-player comparison is examined, so the Vlad/Paredes
diagnostic remains evidence rather than a tuning target.

## Layout

```
app.py                      Streamlit app (mtime-keyed cache)
docs/MODEL_CARD.md          design rationale + limitations
scripts/01..05              pipeline stages
src/parkfit/
  constants.py              buckets, park eras, shrinkage k's
  buckets.py                spray/EV/LA bucketing (batter-perspective spray)
  data.py                   load, filter, park map, home flag, wOBA, names
  model.py                  hierarchical visiting-only park deltas
  score.py                  fingerprints + park scores + fallbacks
  diagnostics.py            profiles, archetypes, comparisons, GB check
  validation.py             split-half, k tuning, holdout, park-switch
```
