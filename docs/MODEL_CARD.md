# ParkFit Model Card

## What this is

ParkFit estimates how much each MLB park helps or hurts a specific hitter's contact profile. Traditional park factors describe how a park plays for the average hitter; ParkFit asks which parks historically reward the exact types of contact — handedness, batter-perspective spray direction, exit velocity, launch angle — that this hitter actually produces.

## What this is not

This is a **contact-only decision-support tool**, not a full offensive projection. It does not include strikeouts, walks, injuries, aging, approach changes, pitcher quality, baserunning, or lineup context. It deliberately does not attempt exact ball-flight simulation against wall geometry, because we do not have reliable wall dimensions, wind, temperature, roof status, spin, or drag for every ball — a model that pretends to have them looks advanced while being wrong.

## How it works

1. Every batted ball is bucketed by handedness × batter-perspective spray × launch angle × exit velocity.
2. Each ball's **residual** is its observed wOBA minus the league mean for its bucket. Working in residuals removes bucket-mix and hitter-quality confounding.
3. Park deltas are averages of residuals, fit on **visiting hitters only**. Home hitters are excluded because rosters are constructed and approaches coached to exploit the home park, which would contaminate the park estimate with roster construction — and would leak a scored player's own home performance into his score.
4. Deltas are estimated **hierarchically**: fine cells shrink toward coarser cells (same park, EV collapsed), which shrink toward the park × handedness effect, which shrinks toward a prior. Thin cells borrow strength from their parents instead of being dragged to zero — important because the thinnest cells (extreme pull, high EV, ideal air) are exactly where park sensitivity lives.
5. A player's score in a park is his bucket frequency distribution dotted with that park's shrunk deltas.

## Key outputs

- **Neutral Contact wOBA** — fingerprint × league bucket values.
- **Park Fit Delta** — the player-specific park adjustment.
- **Projected Contact wOBA** — neutral + delta.
- **Park Dependency Score** — best-park delta minus worst-park delta; identifies hitters whose value is most park-sensitive.
- **Model Coverage** — share of the player's contact matched at fine resolution (rest resolved at coarse / park-hand levels).

## Validation

- Split-half stability: park rankings from independent halves of the data (even/odd game IDs) are compared per player via Spearman correlation. The shrinkage constant is tuned to maximize this out-of-sample stability — never tuned against named-player comparisons.
- Season holdout: directional stability of park deltas across seasons.
- Park-switch check: predicted vs. observed contact change for hitters who changed home parks (interpreted loosely; many confounds).
- Ground-ball sanity check: GB park deltas should be ≈ 0 because infield outcomes reflect defense (a team property), not park.

## Known limitations

- Statcast hit coordinates can be missing/unreliable on home runs; missingness is audited by event type and reported.
- Park eras (fence moves, temporary home parks) are handled with a manual era table that must be kept current.
- Neutral-site games carry the nominal home team and must be excluded by game ID.
- A player's fingerprint is itself partly shaped by his home park (hitters adapt), which the model cannot remove.
- Within-bucket skill is discarded, so neutral contact wOBA compresses the extremes of hitter quality; the tool is for *fit*, not *talent*.
- Fallback wOBA event weights are approximate; the vast majority of values come from Statcast's own `woba_value`.
