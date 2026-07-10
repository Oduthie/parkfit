"""Constants for the ParkFit empirical bucket model.

Everything configurable lives here so the model card can point to one file.
"""

# ---------------------------------------------------------------------------
# Contact buckets
# ---------------------------------------------------------------------------

EV_BINS = [-999, 80, 90, 95, 100, 105, 999]
EV_LABELS = ["<80", "80-90", "90-95", "95-100", "100-105", "105+"]

LA_BINS = [-999, 0, 10, 20, 30, 40, 999]
LA_LABELS = ["GB", "Low", "Line", "IdealAir", "HighAir", "Popup"]

SPRAY_BINS = [-999, -25, -10, 10, 25, 999]
SPRAY_LABELS = ["ExtremeOppo", "Oppo", "Center", "Pull", "ExtremePull"]

# Fine bucket = full resolution. Coarse bucket drops EV (the thinnest
# dimension) and is the parent level for hierarchical shrinkage.
FINE_BUCKET_COLS = ["stand_bucket", "spray_bucket", "la_bucket", "ev_bucket"]
COARSE_BUCKET_COLS = ["stand_bucket", "spray_bucket", "la_bucket"]
HAND_COLS = ["stand_bucket"]

# ---------------------------------------------------------------------------
# Shrinkage defaults (k = pseudo-observations pulling toward the parent level)
# Tune K_FINE with scripts/05_validation.py before trusting these.
# ---------------------------------------------------------------------------

K_FINE = 40.0      # fine cell -> coarse cell
K_COARSE = 150.0   # coarse cell -> park x handedness
K_PARK = 300.0     # park x handedness -> prior (0 or supplied park factor)

MIN_LEAGUE_BUCKET_N = 50   # below this, distrust the league baseline itself
MIN_PLAYER_BBE = 150       # minimum career batted balls to be scored
MIN_PLAYER_BBE_FULL = 400  # "full confidence" tier, flagged in output

# ---------------------------------------------------------------------------
# Statcast home_team abbreviation -> park, with era handling.
# Era splits only for genuinely material changes; over-splitting fragments
# samples. Verify years against a current source before final runs.
# ---------------------------------------------------------------------------

TEAM_TO_PARK = {
    "AZ": "Chase Field",
    "ATL": "Truist Park",
    "BAL": "Camden Yards",
    "BOS": "Fenway Park",
    "CHC": "Wrigley Field",
    "CWS": "Guaranteed Rate Field",
    "CIN": "Great American Ball Park",
    "CLE": "Progressive Field",
    "COL": "Coors Field",
    "DET": "Comerica Park",
    "HOU": "Minute Maid Park",
    "KC": "Kauffman Stadium",
    "LAA": "Angel Stadium",
    "LAD": "Dodger Stadium",
    "MIA": "loanDepot park",
    "MIL": "American Family Field",
    "MIN": "Target Field",
    "NYM": "Citi Field",
    "NYY": "Yankee Stadium",
    "ATH": "Sutter Health Park",
    "PHI": "Citizens Bank Park",
    "PIT": "PNC Park",
    "SD": "Petco Park",
    "SEA": "T-Mobile Park",
    "SF": "Oracle Park",
    "STL": "Busch Stadium",
    "TB": "Tropicana Field",
    "TEX": "Globe Life Field",
    "TOR": "Rogers Centre",
    "WSH": "Nationals Park",
}

# (start_year, end_year, park_label) — first matching range wins.
PARK_ERAS = {
    "BAL": [
        (1992, 2021, "Camden Yards (pre-2022 LF)"),
        (2022, 2024, "Camden Yards (deep LF)"),
        (2025, 9999, "Camden Yards (2025+ LF)"),
    ],
    "TB": [
        (1998, 2024, "Tropicana Field"),
        (2025, 2025, "Steinbrenner Field (2025)"),
        (2026, 9999, "Tropicana Field"),
    ],
    "OAK": [
        (1968, 2024, "Oakland Coliseum"),
    ],
    "ATH": [
        (2025, 9999, "Sutter Health Park"),
    ],
}


def get_park(home_team: str, game_year: int) -> str:
    """Resolve a Statcast home_team code + season to a park-era label."""
    eras = PARK_ERAS.get(home_team)
    if eras:
        for start, end, label in eras:
            if start <= game_year <= end:
                return label
    return TEAM_TO_PARK.get(home_team, f"UNKNOWN ({home_team})")


# game_pks played at neutral sites (London, Mexico City, Seoul, Rickwood,
# Williamsport, etc.). Statcast rows carry the nominal home_team, so these
# must be excluded by hand. Populate from a schedule audit.
NEUTRAL_SITE_GAME_PKS: set[int] = set()

# ---------------------------------------------------------------------------
# Observed wOBA
# ---------------------------------------------------------------------------

# Fallback only — prefer Statcast's own woba_value column. These weights are
# approximate and drift slightly by season; the audit script reports how many
# rows actually use the fallback.
EVENT_WOBA_FALLBACK = {
    "field_out": 0.0,
    "force_out": 0.0,
    "grounded_into_double_play": 0.0,
    "fielders_choice_out": 0.0,
    "fielders_choice": 0.0,
    "double_play": 0.0,
    "triple_play": 0.0,
    "sac_fly": 0.0,
    "sac_bunt": 0.0,
    "single": 0.88,
    "double": 1.25,
    "triple": 1.58,
    "home_run": 2.00,
    "field_error": 0.90,
}

BATTED_BALL_EVENTS = set(EVENT_WOBA_FALLBACK.keys())

# Columns expected in raw Statcast pulls (pybaseball.statcast naming).
REQUIRED_RAW_COLUMNS = [
    "game_pk", "game_year", "batter", "stand",
    "home_team", "inning_topbot", "events", "type",
    "launch_speed", "launch_angle", "hc_x", "hc_y",
]
