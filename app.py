"""ParkFit — player-specific park fit from empirical contact-shape outcomes.

Run:  streamlit run app.py
Requires scripts 01-03 (data/output/*.parquet). Optional: park_dimensions_clean.csv
in this folder or the parent folder enables the field-outline cards.
"""

import html
import unicodedata
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Park Fit Analyzer", page_icon="⚾", layout="wide")

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "data" / "output"

DIMS_CANDIDATES = [ROOT / "park_dimensions_clean.csv",
                   ROOT.parent / "park_dimensions_clean.csv"]
DIM_ALIASES = {"Minute Maid Park": "Daikin Park",
               "Oakland Coliseum": "Oakland Coliseum"}

# The 30 parks in use for the 2026 season. Older eras / temporary homes are
# still used to FIT the model, but only these are shown and ranked. Edit if
# anything changes (e.g. Rays venue).
CURRENT_PARKS_2026 = {
    "Chase Field", "Truist Park", "Camden Yards (2025+ LF)", "Fenway Park",
    "Wrigley Field", "Guaranteed Rate Field", "Great American Ball Park",
    "Progressive Field", "Coors Field", "Comerica Park", "Minute Maid Park",
    "Kauffman Stadium", "Angel Stadium", "Dodger Stadium", "loanDepot park",
    "American Family Field", "Target Field", "Citi Field", "Yankee Stadium",
    "Sutter Health Park", "Citizens Bank Park", "PNC Park", "Petco Park",
    "T-Mobile Park", "Oracle Park", "Busch Stadium", "Tropicana Field",
    "Globe Life Field", "Rogers Centre", "Nationals Park",
}

# Detected home parks from 2025 data may be retired era labels; map them to
# the park that team plays in for 2026.
HOME_REMAP = {
    "Steinbrenner Field (2025)": "Tropicana Field",
    "Camden Yards (deep LF)": "Camden Yards (2025+ LF)",
    "Camden Yards (pre-2022 LF)": "Camden Yards (2025+ LF)",
    "Oakland Coliseum": "Sutter Health Park",
}

FA_FILE_CANDIDATES = [ROOT / "free_agents_2026.csv",
                      ROOT.parent / "free_agents_2026.csv"]


def norm_name(s):
    s = (unicodedata.normalize("NFKD", str(s))
         .encode("ascii", "ignore").decode().lower().replace(".", "").strip())
    s = " ".join(s.split())
    for suf in (" jr", " sr", " ii", " iii"):
        if s.endswith(suf):
            s = s[: -len(suf)]
    return s.strip()

TEAM_META = {
 "American Family Field":("Brewers",158,"#12284B","#FFC52F"),
 "Angel Stadium":("Angels",108,"#BA0021","#003263"),
 "Busch Stadium":("Cardinals",138,"#C41E3A","#0C2340"),
 "Camden Yards":("Orioles",110,"#DF4601","#000000"),
 "Chase Field":("D-backs",109,"#A71930","#E3D4AD"),
 "Citi Field":("Mets",121,"#002D72","#FF5910"),
 "Citizens Bank Park":("Phillies",143,"#E81828","#002D72"),
 "Comerica Park":("Tigers",116,"#0C2340","#FA4616"),
 "Coors Field":("Rockies",115,"#33006F","#C4CED4"),
 "Daikin Park":("Astros",117,"#002D62","#EB6E1F"),
 "Minute Maid Park":("Astros",117,"#002D62","#EB6E1F"),
 "Dodger Stadium":("Dodgers",119,"#005A9C","#EF3E42"),
 "Fenway Park":("Red Sox",111,"#BD3039","#0C2340"),
 "Globe Life Field":("Rangers",140,"#003278","#C0111F"),
 "Great American Ball Park":("Reds",113,"#C6011F","#000000"),
 "Guaranteed Rate Field":("White Sox",145,"#27251F","#C4CED4"),
 "Kauffman Stadium":("Royals",118,"#004687","#BD9B60"),
 "loanDepot Park":("Marlins",146,"#00A3E0","#EF3340"),
 "loanDepot park":("Marlins",146,"#00A3E0","#EF3340"),
 "Nationals Park":("Nationals",120,"#AB0003","#14225A"),
 "Oracle Park":("Giants",137,"#FD5A1E","#27251F"),
 "Petco Park":("Padres",135,"#2F241D","#FFC425"),
 "PNC Park":("Pirates",134,"#27251F","#FDB827"),
 "Progressive Field":("Guardians",114,"#E50022","#00385D"),
 "Rogers Centre":("Blue Jays",141,"#134A8E","#E8291C"),
 "Oakland Coliseum":("Athletics",133,"#003831","#EFB21E"),
 "Sutter Health Park":("Athletics",133,"#003831","#EFB21E"),
 "Target Field":("Twins",142,"#002B5C","#D31145"),
 "T-Mobile Park":("Mariners",136,"#0C2C56","#005C5C"),
 "Tropicana Field":("Rays",139,"#092C5C","#8FBCE6"),
 "Steinbrenner Field":("Rays",139,"#092C5C","#8FBCE6"),
 "Truist Park":("Braves",144,"#CE1141","#13274F"),
 "Wrigley Field":("Cubs",112,"#0E3386","#CC3433"),
 "Yankee Stadium":("Yankees",147,"#0C2340","#C4CED4"),
}

st.markdown("""
<style>
.stApp { background: linear-gradient(135deg,#f8fafc 0%,#e8eef6 100%); }
.block-container { padding-top:1.6rem; max-width:1500px; }
.hero { background:linear-gradient(135deg,#081b37 0%,#14537d 100%); color:#fff;
 padding:2rem 2.3rem; border-radius:24px; margin-bottom:1.4rem;
 box-shadow:0 16px 40px rgba(15,23,42,.22); }
.hero h1 { color:#fff; font-size:2.9rem; font-weight:900; margin:0; letter-spacing:-.03em; }
.hero p { color:#dbeafe; max-width:980px; line-height:1.6; margin-top:.7rem; }
.pill { display:inline-block; padding:.4rem .8rem; border-radius:999px; margin:.4rem .35rem 0 0;
 background:rgba(255,255,255,.14); color:#eff6ff; font-size:.85rem; font-weight:800;
 border:1px solid rgba(255,255,255,.16); }
.card { background:rgba(255,255,255,.95); border-radius:22px; padding:1.4rem 1.6rem;
 box-shadow:0 12px 32px rgba(15,23,42,.09); border:1px solid rgba(148,163,184,.22);
 margin-bottom:1.2rem; }
.pheader { display:flex; align-items:center; gap:1.2rem; }
.hswrap { width:118px; height:118px; border-radius:50%; padding:4px; flex:0 0 auto;
 background:linear-gradient(135deg,#2563eb,#38bdf8,#f97316); }
.hs { width:110px; height:110px; border-radius:50%; object-fit:cover; background:#e2e8f0;
 display:block; border:4px solid #fff; }
.pname { font-size:2rem; font-weight:900; color:#081832; letter-spacing:-.03em; }
.psub { color:#64748b; font-weight:700; margin-top:.3rem; }
.badge { display:inline-block; padding:.38rem .75rem; border-radius:999px; font-size:.85rem;
 font-weight:800; margin:.6rem .35rem 0 0; }
.b-blue{background:#dbeafe;color:#1d4ed8;} .b-green{background:#dcfce7;color:#166534;}
.b-orange{background:#ffedd5;color:#9a3412;} .b-purple{background:#ede9fe;color:#6d28d9;}
.b-red{background:#fee2e2;color:#b91c1c;}
.sgrid { display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:.9rem; margin-bottom:1rem; }
.scard { background:rgba(255,255,255,.96); border-radius:18px; padding:1rem 1.1rem;
 border:1px solid rgba(148,163,184,.2); box-shadow:0 8px 22px rgba(15,23,42,.07); }
.slabel { color:#475569; font-weight:800; font-size:.9rem; }
.svalue { color:#07162d; font-size:1.7rem; font-weight:900; letter-spacing:-.03em;
 overflow-wrap:anywhere; line-height:1.1; margin-top:.3rem; }
.ssmall { color:#64748b; font-size:.8rem; font-weight:700; margin-top:.3rem; }
.insight { background:rgba(255,255,255,.96); border-left:6px solid #2563eb;
 padding:1rem 1.2rem; border-radius:14px; margin:1rem 0 1.3rem 0; color:#334155;
 line-height:1.65; box-shadow:0 6px 20px rgba(15,23,42,.06); }
.dgrid { display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:.9rem; margin:1rem 0; }
.dcard { background:#fff; border-radius:18px; padding:.9rem; border:1px solid rgba(148,163,184,.22); }
.drank { display:inline-flex; align-items:center; justify-content:center; color:#fff;
 background:#2563eb; font-size:.75rem; font-weight:900; min-width:38px; height:38px;
 border-radius:999px; }
.dtitle { color:#081832; font-weight:900; margin:.4rem 0; line-height:1.15; }
.dpills { display:grid; grid-template-columns:repeat(3,1fr); gap:.4rem; margin-top:.5rem; }
.dpill { background:#f8fafc; border:1px solid rgba(148,163,184,.3); border-radius:12px;
 padding:.4rem .2rem; text-align:center; }
.dpl { color:#64748b; font-size:.65rem; font-weight:900; }
.dpv { color:#07162d; font-size:1rem; font-weight:900; }
.dnote { color:#64748b; font-size:.76rem; font-weight:700; margin-top:.4rem; line-height:1.35; }
.tlogo { width:24px; height:24px; object-fit:contain; }
.dtop { display:flex; justify-content:space-between; align-items:center; }
@media (max-width:1100px){ .dgrid,.sgrid{grid-template-columns:repeat(2,1fr);} }
@media (max-width:700px){
 .dgrid,.sgrid{grid-template-columns:1fr;}
 .block-container{padding-left:.9rem;padding-right:.9rem;}
 .hero{padding:1.3rem 1.2rem;border-radius:18px;}
 .hero h1{font-size:1.9rem;}
 .hero p{font-size:.95rem;line-height:1.5;}
 .pill{font-size:.72rem;padding:.3rem .6rem;}
 .card{padding:1rem 1.1rem;border-radius:16px;}
 .pheader{gap:.9rem;}
 .hswrap{width:84px;height:84px;padding:3px;}
 .hs{width:78px;height:78px;border-width:3px;}
 .pname{font-size:1.45rem;}
 .psub{font-size:.85rem;}
 .badge{font-size:.72rem;padding:.3rem .55rem;}
 .svalue{font-size:1.3rem;}
 .insight{font-size:.92rem;padding:.85rem 1rem;}
 .dtitle{font-size:.95rem;}
}
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
@st.cache_data
def _load_all(stamp):
    scores = pd.read_parquet(OUT / "park_scores.parquet")
    profiles = pd.read_parquet(OUT / "player_profiles.parquet")
    contributions = pd.read_parquet(OUT / "bucket_contributions.parquet")
    extras = (pd.read_parquet(OUT / "player_extras.parquet")
              if (OUT / "player_extras.parquet").exists() else pd.DataFrame())
    park_k = (pd.read_parquet(OUT / "park_k.parquet")
              if (OUT / "park_k.parquet").exists() else pd.DataFrame())
    dims = {}
    for cand in DIMS_CANDIDATES:
        if cand.exists():
            dm = pd.read_csv(cand)
            dims = dm.set_index("park_name")[["lf_line", "cf", "rf_line"]].to_dict("index")
            break
    return scores, profiles, contributions, extras, park_k, dims


def load_all():
    needed = ["park_scores.parquet", "player_profiles.parquet",
              "bucket_contributions.parquet"]
    missing = [n for n in needed if not (OUT / n).exists()]
    if missing:
        st.error(f"Missing: {', '.join(missing)} — run scripts 01-03 first.")
        st.stop()
    opt = ["player_extras.parquet", "park_k.parquet"]
    stamp = (tuple((OUT / n).stat().st_mtime for n in needed)
             + tuple((OUT / n).stat().st_mtime if (OUT / n).exists() else 0.0
                     for n in opt))
    return _load_all(stamp)


scores, profiles, contributions, extras, park_k_df, dims_raw = load_all()

# ---- 2026 view: only parks in use this season, only recent hitters --------
scores = scores[scores["park"].isin(CURRENT_PARKS_2026)].copy()
if not extras.empty and "last_year" in extras.columns:
    active_ids = set(extras.loc[extras["last_year"] >= 2024, "batter"])
    scores = scores[scores["batter"].isin(active_ids)]
contributions = contributions[contributions["park"].isin(CURRENT_PARKS_2026)]

# Re-rank and re-spread within the 2026 park set.
scores["park_rank"] = (scores.groupby("batter")["park_fit_delta"]
                       .rank(ascending=False, method="min").astype(int))
_dep = scores.groupby("batter")["park_fit_delta"].agg(lambda s: s.max() - s.min())
scores["park_dependency_score"] = scores["batter"].map(_dep)

# Fit vs Avg: this park's delta for the player, minus the average delta of
# same-handed scored hitters in that park — the pure player-park interaction.
hand_avg = (scores.groupby(["park", "stand_bucket"], observed=True)["park_fit_delta"]
            .transform("mean"))
scores = scores.assign(fit_vs_avg=(scores["park_fit_delta"] - hand_avg).round(4))

park_k_map = (dict(zip(park_k_df["park"], park_k_df["park_k_pct"]))
              if not park_k_df.empty else {})

players = (
    scores.groupby(["batter", "batter_name", "stand_bucket"], observed=True)
    .agg(spread=("park_dependency_score", "first"),
         neutral=("neutral_contact_woba", "first"),
         n_balls=("player_bbe", "first"),
         tier=("confidence_tier", "first"))
    .reset_index()
    .merge(profiles.drop(columns=["stand_bucket"], errors="ignore"),
           on=["batter", "batter_name"], how="left")
)
# Switch-hitters produce two profile rows (one per side); keep one per batter
# so every downstream table shows each player exactly once.
players = players.drop_duplicates(subset=["batter"]).reset_index(drop=True)
if not extras.empty:
    players = players.merge(extras, on="batter", how="left")
else:
    for c in ["k_pct", "bb_pct", "hr_pct", "home_park", "pa"]:
        players[c] = pd.NA

# Home rank + best landing spot (Coors excluded), measured in shape fit.
home_rows = []
for _, p in players.dropna(subset=["home_park"]).iterrows():
    s = scores[scores["batter"] == p["batter"]]
    hp = HOME_REMAP.get(p["home_park"], p["home_park"])
    players.loc[players["batter"] == p["batter"], "home_park"] = hp
    home = s[s["park"] == hp]
    if home.empty:
        continue
    realistic = s[(s["park"] != "Coors Field") & (s["park"] != p["home_park"])]
    if realistic.empty:
        continue
    best_alt = realistic.loc[realistic["fit_vs_avg"].idxmax()]
    home_rows.append({
        "batter": p["batter"],
        "home_rank": int(home["park_rank"].iloc[0]),
        "home_woba": float(home["projected_contact_woba"].iloc[0]),
        "alt_park": best_alt["park"],
        "upgrade": float(best_alt["fit_vs_avg"] - home["fit_vs_avg"].iloc[0]),
    })
home_df = pd.DataFrame(home_rows)
if not home_df.empty:
    players = players.merge(home_df, on="batter", how="left")
else:
    for c in ["home_rank", "home_woba", "alt_park", "upgrade"]:
        players[c] = pd.NA


def base_park(park):
    return str(park).split(" (")[0].strip()


def team_meta(park):
    return TEAM_META.get(park) or TEAM_META.get(base_park(park)) \
        or ("", 0, "#2563eb", "#94a3b8")


def park_dims(park):
    bp = base_park(park)
    return dims_raw.get(park) or dims_raw.get(bp) or dims_raw.get(DIM_ALIASES.get(bp, ""))


def headshot(bid):
    return ("https://img.mlbstatic.com/mlb-photos/image/upload/"
            "w_300,d_people:generic:headshot:silo:current.png,q_auto:best/"
            f"v1/people/{int(bid)}/headshot/67/current")


def logo(tid):
    return f"https://www.mlbstatic.com/team-logos/{int(tid)}.svg"


def fmt(v, spec, dash="—"):
    return spec.format(v) if pd.notna(v) else dash


def player_card(name, info, badges=""):
    bits = [str(info["stand_bucket"]), f'{int(info["n_balls"]):,} career batted balls']
    if pd.notna(info.get("k_pct")):
        bits.append(f'K% {info["k_pct"]:.1f}')
    if pd.notna(info.get("bb_pct")):
        bits.append(f'BB% {info["bb_pct"]:.1f}')
    if pd.notna(info.get("archetype")):
        bits.append(str(info["archetype"]))
    if pd.notna(info.get("home_park")):
        bits.append(f'home: {info["home_park"]}')
    return (f'<div class="card"><div class="pheader">'
            f'<div class="hswrap"><img class="hs" src="{headshot(info["batter"])}"></div>'
            f'<div><div class="pname">{html.escape(str(name))}</div>'
            f'<div class="psub">{html.escape(" · ".join(bits))}</div>'
            f'{badges}</div></div></div>')


def scard(label, value, small=""):
    s = f'<div class="ssmall">{html.escape(str(small))}</div>' if small else ""
    return (f'<div class="scard"><div class="slabel">{html.escape(str(label))}</div>'
            f'<div class="svalue">{html.escape(str(value))}</div>{s}</div>')


def field_svg(lf, cf, rf, primary, secondary):
    def y(d):
        return 57 - ((d - 300) / (430 - 300)) * 27
    return (f'<svg viewBox="0 0 260 130" style="width:100%;height:110px;display:block">'
            f'<path d="M130 122 L30 55 Q130 18 230 55 L130 122 Z" fill="#d1fae5" stroke="#cbd5e1"/>'
            f'<path d="M34 {y(lf):.0f} C80 {y(cf)-16:.0f},180 {y(cf)-16:.0f},226 {y(rf):.0f}" '
            f'fill="none" stroke="{primary}" stroke-width="8" stroke-linecap="round"/>'
            f'<path d="M34 {y(lf)+6:.0f} C80 {y(cf)-10:.0f},180 {y(cf)-10:.0f},226 {y(rf)+6:.0f}" '
            f'fill="none" stroke="{secondary}" stroke-width="3.5" stroke-linecap="round"/>'
            f'<path d="M130 122 L30 55 M130 122 L230 55" stroke="#d97706" stroke-width="2" opacity=".6"/>'
            f'<path d="M130 120 L102 94 L130 70 L158 94 Z" fill="#fef3c7" stroke="#f97316"/></svg>')


def park_card(park, rank, woba, driver, kpct):
    meta = team_meta(park)
    d = park_dims(park)
    pills = ""
    svg = ""
    if d:
        lf, cf, rf = int(d["lf_line"]), int(d["cf"]), int(d["rf_line"])
        svg = field_svg(lf, cf, rf, meta[2], meta[3])
        pills = ('<div class="dpills">' + "".join(
            f'<div class="dpill"><div class="dpl">{lab}</div><div class="dpv">{v}</div></div>'
            for lab, v in [("LF", lf), ("CF", cf), ("RF", rf)]) + '</div>')
    lg = f'<img class="tlogo" src="{logo(meta[1])}">' if meta[1] else ""
    kbit = f" · park K% {kpct:.1f}" if pd.notna(kpct) else ""
    return (f'<div class="dcard"><div class="dtop"><span class="drank">#{int(rank)}</span>{lg}</div>'
            f'<div class="dtitle">{html.escape(park)}</div>{svg}{pills}'
            f'<div class="dnote">{woba:.3f} proj wOBA{kbit} · {html.escape(driver)}</div></div>')


def build_drivers(sub):
    s = sub.copy()
    air = s[s["la_bucket"] != "GB"]
    if not air.empty:
        s = air
    s["abs_c"] = s["bucket_contribution"].abs()
    idx = s.groupby("park")["abs_c"].idxmax()
    out = {}
    for _, r in s.loc[idx].iterrows():
        arrow = "▲" if r["bucket_contribution"] > 0 else "▼"
        out[r["park"]] = f'{arrow} {r["spray_bucket"]} {r["la_bucket"]} {r["ev_bucket"]}'
    return out


def rank_chart(df, h):
    d = df.copy()
    d["display"] = d["park_rank"].astype(str) + ". " + d["park"]
    return (alt.Chart(d).mark_bar(cornerRadiusTopRight=7, cornerRadiusBottomRight=7)
        .encode(x=alt.X("projected_contact_woba:Q", title="Projected wOBA",
                        scale=alt.Scale(zero=False)),
                y=alt.Y("display:N", sort=d["display"].tolist(), title=None),
                color=alt.Color("projected_contact_woba:Q",
                    scale=alt.Scale(range=["#bae6fd", "#2563eb", "#0b1f3a"]), legend=None),
                tooltip=[alt.Tooltip("park:N", title="Park"),
                         alt.Tooltip("projected_contact_woba:Q", format=".3f"),
                         alt.Tooltip("fit_vs_avg:Q", title="Fit vs avg", format="+.4f"),
                         alt.Tooltip("driver:N", title="Driver")])
        .properties(height=h))


# ---------------------------------------------------------------------------
st.markdown("""
<div class="hero">
 <h1>Park Fit Analyzer</h1>
 <p>Career batted-ball profiles (2021–present) for every active MLB hitter, scored across the 30
 parks in use for 2026. Every ball is bucketed by handedness, batter-perspective spray, exit
 velocity, and launch angle, then matched against how each park has historically rewarded that
 exact contact — fit on visiting hitters only, with hierarchical shrinkage, validated by
 split-half stability. Contact quality only; strikeout environments are shown for context.</p>
 <div><span class="pill">Career profiles</span><span class="pill">Empirical contact buckets</span>
 <span class="pill">Split-half validated</span><span class="pill">Trade fit</span>
 <span class="pill">2026-27 FA board</span><span class="pill">Explains why</span></div>
</div>
""", unsafe_allow_html=True)

PAGES = ["Player Park Fit", "Compare Hitters", "League Insights", "Game", "Methodology"]
if "nav" not in st.session_state:
    st.session_state.nav = PAGES[0]
if "jump_n" not in st.session_state:
    st.session_state.jump_n = 0
_page = st.radio("Navigate", PAGES, horizontal=True,
                 index=PAGES.index(st.session_state.nav),
                 label_visibility="collapsed")
if _page != st.session_state.nav:
    st.session_state.nav = _page
page = st.session_state.nav


def row_jump(event, df, field, state_key, target_page):
    """Click a table row -> jump to the relevant page with it preloaded."""
    try:
        rows = event.selection.rows
    except Exception:
        rows = []
    if rows:
        st.session_state[state_key] = df.iloc[rows[0]][field]
        st.session_state.nav = target_page
        st.session_state.jump_n += 1
        st.rerun()

# ================= PAGE 1 =================
if page == "Player Park Fit":
    _plist = sorted(players["batter_name"].dropna().unique())
    if "sel_player" not in st.session_state or st.session_state.sel_player not in _plist:
        st.session_state.sel_player = _plist[0]
    name = st.selectbox("Choose hitter", _plist,
                        index=_plist.index(st.session_state.sel_player))
    st.session_state.sel_player = name
    if name:
        info = players[players["batter_name"] == name].iloc[0]
        pr = scores[scores["batter_name"] == name].sort_values("park_rank").copy()
        sub = contributions[contributions["batter_name"] == name]
        pr["driver"] = pr["park"].map(build_drivers(sub)).fillna("—")
        pr["park_k_pct"] = pr["park"].map(park_k_map)
        table_h = len(pr) * 35 + 40

        best, worst = pr.iloc[0], pr.iloc[-1]
        spread = info["spread"]
        pct = (players["spread"] < spread).mean() * 100
        has_home = pd.notna(info.get("home_park")) and pd.notna(info.get("home_rank"))

        badges = (f'<span class="badge b-blue">Best: {html.escape(best["park"])}</span>'
                  f'<span class="badge b-orange">Worst: {html.escape(worst["park"])}</span>')
        if has_home:
            badges += (f'<span class="badge b-purple">Home: {html.escape(info["home_park"])} '
                       f'(#{int(info["home_rank"])} for him)</span>')
            if info["upgrade"] >= 0.006:
                badges += (f'<span class="badge b-red">Held back: +{info["upgrade"]:.3f} '
                           f'shape fit at {html.escape(str(info["alt_park"]))}</span>')
            elif int(info["home_rank"]) <= 3:
                badges += '<span class="badge b-green">Well placed</span>'
        if info["tier"] == "provisional":
            badges += '<span class="badge b-orange">Provisional sample</span>'
        st.markdown(player_card(name, info, badges), unsafe_allow_html=True)

        bestfit = pr.loc[pr["fit_vs_avg"].idxmax()]
        st.markdown('<div class="sgrid">'
            + scard("Best Park (raw)", best["park"],
                    f'{best["projected_contact_woba"]:.3f} proj wOBA — hitter parks '
                    'top this for everyone')
            + scard("Best Shape Fit", bestfit["park"],
                    f'{bestfit["fit_vs_avg"]:+.4f} vs avg {info["stand_bucket"]} — '
                    'HIS edge, park quality removed')
            + scard("Worst Park", worst["park"], f'{worst["projected_contact_woba"]:.3f} proj wOBA')
            + scard("Park Spread", f"{spread:.3f}",
                    f'{pct:.0f}th pct — '
                    + ("park-proof" if pct < 30 else "park-sensitive" if pct > 70 else "typical"))
            + scard("HR% / K%",
                    f'{fmt(info.get("hr_pct"), "{:.1f}")} / {fmt(info.get("k_pct"), "{:.1f}")}',
                    "per BBE / per PA")
            + '</div>', unsafe_allow_html=True)

        home_line = ""
        if has_home:
            if info["upgrade"] >= 0.006:
                home_line = (f' His current home, <b>{html.escape(info["home_park"])}</b>, ranks '
                             f'<b>#{int(info["home_rank"])}</b> for his profile — the park his '
                             f'shape gains most at is <b>{html.escape(str(info["alt_park"]))}</b> '
                             f'(<b>{info["upgrade"]:+.3f}</b> shape fit, Coors excluded).')
            else:
                home_line = (f' His current home, <b>{html.escape(info["home_park"])}</b>, ranks '
                             f'<b>#{int(info["home_rank"])}</b> — close to optimal.')
        st.markdown(
            f'<div class="insight"><b>Read:</b> {html.escape(name)} projects best at '
            f'<b>{html.escape(best["park"])}</b> ({best["projected_contact_woba"]:.3f}, '
            f'{html.escape(best["driver"])}) and worst at <b>{html.escape(worst["park"])}</b> '
            f'({worst["projected_contact_woba"]:.3f}, {html.escape(worst["driver"])}). The park '
            f'that suits his <i>shape</i> most vs the average {info["stand_bucket"]} is '
            f'<b>{html.escape(bestfit["park"])}</b> (fit {bestfit["fit_vs_avg"]:+.4f}).'
            f'{home_line}</div>',
            unsafe_allow_html=True)

        l, r = st.columns([1.15, 1])
        with l:
            st.markdown("### Full Ranking")
            cols = ["park_rank", "park", "projected_contact_woba", "fit_vs_avg"]
            if park_k_map:
                cols.append("park_k_pct")
            cols.append("driver")
            show = pr[cols].rename(
                columns={"park_rank": "Rank", "park": "Park",
                         "projected_contact_woba": "Proj wOBA", "fit_vs_avg": "Fit vs Avg",
                         "park_k_pct": "Park K%", "driver": "Primary driver"})
            ev = st.dataframe(show, hide_index=True, use_container_width=True,
                height=table_h, on_select="rerun", selection_mode="single-row",
                key=f"tbl_rank_{st.session_state.jump_n}",
                column_config={
                    "Proj wOBA": st.column_config.NumberColumn(format="%.3f"),
                    "Fit vs Avg": st.column_config.NumberColumn(format="%+.4f"),
                    "Park K%": st.column_config.NumberColumn(format="%.1f")})
            row_jump(ev, show, "Park", "lens_park_sel", "League Insights")
            st.caption("Click any park row to open it in the Park Lens.")
        with r:
            st.markdown("### Projection Chart")
            st.altair_chart(rank_chart(pr, table_h), use_container_width=True)

        st.markdown("### Top 5 Fits")
        cards = "".join(park_card(x["park"], x["park_rank"], x["projected_contact_woba"],
                                  x["driver"], x["park_k_pct"])
                        for _, x in pr.head(5).iterrows())
        st.markdown(f'<div class="dgrid">{cards}</div>', unsafe_allow_html=True)

        st.markdown("### Why this park?")
        park_pick = st.selectbox("Park", list(pr["park"]))
        wsub = sub[sub["park"] == park_pick].copy()
        if wsub.empty:
            st.info("No contribution rows for this park.")
        else:
            wsub["abs_c"] = wsub["bucket_contribution"].abs()
            top = wsub.sort_values("abs_c", ascending=False).head(10).copy()
            top["Contact bucket"] = (top["spray_bucket"] + " | " + top["la_bucket"]
                                     + " | " + top["ev_bucket"] + " mph")
            st.dataframe(
                top[["Contact bucket", "player_bucket_freq", "delta_used",
                     "bucket_contribution", "park_bucket_n", "fallback_level"]].rename(
                    columns={"player_bucket_freq": "Player freq",
                             "delta_used": "Park Δ (shrunk)",
                             "bucket_contribution": "Contribution",
                             "park_bucket_n": "Park sample",
                             "fallback_level": "Resolution"}),
                hide_index=True, use_container_width=True,
                column_config={
                    "Player freq": st.column_config.NumberColumn(format="percent"),
                    "Park Δ (shrunk)": st.column_config.NumberColumn(format="%+.4f"),
                    "Contribution": st.column_config.NumberColumn(format="%+.5f"),
                    "Park sample": st.column_config.NumberColumn(format="%.0f")})
            st.caption("Contribution = how often he creates that contact × how much this park "
                       "rewards it vs league average.")

# ================= PAGE 2 =================
if page == "Compare Hitters":
    names = sorted(players["batter_name"].dropna().unique())
    c1, c2 = st.columns(2)
    with c1:
        pa = st.selectbox("Hitter A", names, key="ca")
    with c2:
        pb = st.selectbox("Hitter B", names, key="cb", index=1 if len(names) > 1 else 0)
    if pa and pb and pa != pb:
        ia = players[players["batter_name"] == pa].iloc[0]
        ib = players[players["batter_name"] == pb].iloc[0]
        ca, cb = st.columns(2)
        for col, nm, inf in [(ca, pa, ia), (cb, pb, ib)]:
            with col:
                b = (f'<span class="badge b-blue">Air-Pull {fmt(inf.get("pull_air_rate"), "{:.1%}")}</span>'
                     f'<span class="badge b-green">HR {fmt(inf.get("hr_pct"), "{:.1f}")}%</span>'
                     f'<span class="badge b-orange">K {fmt(inf.get("k_pct"), "{:.1f}")}%</span>'
                     f'<span class="badge b-purple">Spread {inf["spread"]:.3f}</span>')
                st.markdown(player_card(nm, inf, b), unsafe_allow_html=True)
        a = scores[scores["batter_name"] == pa][["park", "park_rank", "projected_contact_woba"]] \
            .rename(columns={"park_rank": f"{pa} Rank", "projected_contact_woba": f"{pa} wOBA"})
        b = scores[scores["batter_name"] == pb][["park", "park_rank", "projected_contact_woba"]] \
            .rename(columns={"park_rank": f"{pb} Rank", "projected_contact_woba": f"{pb} wOBA"})
        comp = a.merge(b, on="park")
        comp["Difference"] = comp[f"{pa} wOBA"] - comp[f"{pb} wOBA"]
        # Relative fit strips the level gap between the two hitters, leaving
        # which parks favor A's SHAPE vs B's shape.
        comp["Relative Fit"] = (comp["Difference"] - comp["Difference"].mean()).round(4)
        comp = comp.sort_values("Relative Fit", ascending=False)
        table_h = 420
        fa, fb = comp.iloc[0], comp.iloc[-1]
        st.markdown(
            f'<div class="insight"><b>Where their shapes split</b> (overall talent gap removed): '
            f'<b>{html.escape(fa["park"])}</b> favors {html.escape(pa)} most '
            f'({fa["Relative Fit"]:+.3f}); <b>{html.escape(fb["park"])}</b> favors '
            f'{html.escape(pb)} most ({fb["Relative Fit"]:+.3f}). Same parks — the split is '
            f'their batted-ball profiles.</div>',
            unsafe_allow_html=True)
        l, r = st.columns([1.05, 1])
        with l:
            comp_show = comp[["park", f"{pa} wOBA", f"{pb} wOBA", "Relative Fit"]]
            st.dataframe(comp_show.rename(columns={"park": "Park"}), hide_index=True,
                use_container_width=True, height=table_h,
                column_config={
                    f"{pa} wOBA": st.column_config.NumberColumn(format="%.3f"),
                    f"{pb} wOBA": st.column_config.NumberColumn(format="%.3f"),
                    "Difference": st.column_config.NumberColumn(format="%+.3f"),
                    "Relative Fit": st.column_config.NumberColumn(format="%+.3f")})
        with r:
            ch = (alt.Chart(comp).mark_bar(cornerRadiusTopRight=7, cornerRadiusBottomRight=7)
                .encode(x=alt.X("Relative Fit:Q", title=f"{pa} relative fit advantage"),
                        y=alt.Y("park:N", sort="-x", title=None),
                        color=alt.condition(alt.datum["Relative Fit"] > 0,
                                            alt.value("#2563eb"), alt.value("#f97316")),
                        tooltip=["park", alt.Tooltip("Relative Fit:Q", format="+.3f"),
                                 alt.Tooltip("Difference:Q", format="+.3f")])
                .properties(height=table_h))
            st.altair_chart(ch, use_container_width=True)
    elif pa == pb:
        st.info("Choose two different hitters.")

# ================= PAGE 3 =================
if page == "League Insights":
    st.markdown(
        '<div class="insight"><b>Quick glossary.</b> <b>Raw Fit Δ</b> — how much a park boosts '
        'or hurts this hitter\'s contact overall; hitter-friendly parks score high for everyone. '
        '<b>Shape Edge</b> — how much MORE this hitter gains at a park than the average '
        'same-handed hitter would; this is the park matching HIS specific swing, and it\'s the '
        'number these boards run on. <b>Spread</b> — the gap between his best and worst park; '
        'high-spread hitters are the ones where the address genuinely changes the player.</div>',
        unsafe_allow_html=True)

    # ---- 2026-27 Free Agency board -----------------------------------
    fa_names = []
    for cand in FA_FILE_CANDIDATES:
        if cand.exists():
            fa_names = [ln.strip() for ln in cand.read_text().splitlines()
                        if ln.strip() and not ln.lower().startswith("name")]
            break
    st.markdown("### 2026-27 Free Agency board — where should the market's bats land?")
    if not fa_names:
        st.info("Add free_agents_2026.csv (one hitter name per line) next to app.py "
                "to power this board.")
    else:
        name_map = {norm_name(n): n for n in players["batter_name"]}
        fa_rows = []
        for fa in fa_names:
            match = name_map.get(norm_name(fa))
            if not match:
                continue
            p = players[players["batter_name"] == match].iloc[0]
            s = (scores[(scores["batter"] == p["batter"])
                        & (scores["park"] != "Coors Field")]
                 .sort_values("fit_vs_avg", ascending=False))
            if s.empty:
                continue
            fa_rows.append({
                "Hitter": match, "Bats": p["stand_bucket"],
                "Archetype": p.get("archetype", "—"),
                "Spread": p["spread"],
                "Best Fit": s.iloc[0]["park"],
                "Shape Edge": s.iloc[0]["fit_vs_avg"],
                "2nd": s.iloc[1]["park"] if len(s) > 1 else "—",
                "3rd": s.iloc[2]["park"] if len(s) > 2 else "—",
            })
        if fa_rows:
            fa_df = pd.DataFrame(fa_rows).sort_values("Shape Edge", ascending=False)
            st.markdown(
                '<div class="insight">Upcoming 2026-27 free agent hitters, ranked by how '
                'much their <b>best realistic landing spot</b> (Coors excluded) rewards their '
                'contact shape. High-spread names are the ones where the signing park genuinely '
                'changes the player. Edit <b>free_agents_2026.csv</b> to update the class.</div>',
                unsafe_allow_html=True)
            ev = st.dataframe(fa_df, hide_index=True, use_container_width=True,
                on_select="rerun", selection_mode="single-row",
                key=f"tbl_fa_{st.session_state.jump_n}",
                column_config={
                    "Spread": st.column_config.NumberColumn(format="%.3f"),
                    "Shape Edge": st.column_config.NumberColumn(format="%+.4f")})
            row_jump(ev, fa_df, "Hitter", "sel_player", "Player Park Fit")
            st.caption("Click any hitter to open his Park Fit page.")
        missing_fa = [fa for fa in fa_names if norm_name(fa) not in name_map]
        if missing_fa:
            st.caption("Not matched (name spelling, or below the batted-ball minimum): "
                       + ", ".join(missing_fa))

    # ---- The Park Lens: who gains the most at each park? --------------
    st.markdown("### The Park Lens — who gains the most at each park?")
    st.markdown(
        '<div class="insight">Coors, Cincinnati, and Fenway top the <b>raw</b> rankings for '
        'nearly every hitter — that\'s park quality, shared by all. This view strips it out: '
        '<b>Shape Edge</b> is each hitter\'s edge at this park <b>beyond the average '
        'same-handed hitter</b>, so the names below are the ones whose specific contact shape '
        'this park rewards most (and least). These are the honest sizes of the shape effect — '
        'small numbers, real signal.</div>', unsafe_allow_html=True)
    _parks = sorted(CURRENT_PARKS_2026)
    if ("lens_park_sel" not in st.session_state
            or st.session_state.lens_park_sel not in _parks):
        st.session_state.lens_park_sel = _parks[0]
    lens_park = st.selectbox("Park", _parks,
                             index=_parks.index(st.session_state.lens_park_sel))
    st.session_state.lens_park_sel = lens_park
    lp = (scores[scores["park"] == lens_park]
          .merge(players[["batter", "archetype", "tier"]].drop_duplicates("batter"),
                 on="batter", how="left"))
    lp = lp[lp["tier"] == "full"].drop_duplicates(subset=["batter"])
    lens_cols = ["batter_name", "stand_bucket", "archetype", "fit_vs_avg",
                 "park_fit_delta", "park_rank"]
    lens_rename = {"batter_name": "Hitter", "stand_bucket": "Bats",
                   "archetype": "Archetype", "fit_vs_avg": "Shape Edge",
                   "park_fit_delta": "Raw Fit Δ", "park_rank": "His Rank"}
    lens_cfg = {"Shape Edge": st.column_config.NumberColumn(format="%+.4f"),
                "Raw Fit Δ": st.column_config.NumberColumn(format="%+.4f"),
                "His Rank": st.column_config.NumberColumn(format="%.0f")}
    l, r = st.columns(2)
    with l:
        st.markdown(f"**Gains the most at {lens_park}**")
        _t = lp.nlargest(12, "fit_vs_avg")[lens_cols].rename(columns=lens_rename)
        ev = st.dataframe(_t, hide_index=True, use_container_width=True,
                          on_select="rerun", selection_mode="single-row",
                          key=f"tbl_lens_a_{st.session_state.jump_n}",
                          column_config=lens_cfg)
        row_jump(ev, _t, "Hitter", "sel_player", "Player Park Fit")
    with r:
        st.markdown(f"**Hurt the most at {lens_park}**")
        _t = lp.nsmallest(12, "fit_vs_avg")[lens_cols].rename(columns=lens_rename)
        ev = st.dataframe(_t, hide_index=True, use_container_width=True,
                          on_select="rerun", selection_mode="single-row",
                          key=f"tbl_lens_b_{st.session_state.jump_n}",
                          column_config=lens_cfg)
        row_jump(ev, _t, "Hitter", "sel_player", "Player Park Fit")
    st.caption("Click any hitter to open his Park Fit page.")

    hb = players.dropna(subset=["upgrade", "home_rank"]).copy()
    n_excl = players["home_rank"].isna().sum()

    st.markdown("### The trade board — who's in the wrong park?")
    st.markdown(
        '<div class="insight">Each hitter\'s current home ranked against all parks <b>for his '
        'specific contact profile</b>. The gain is measured in <b>shape fit</b> — how much more '
        'his exact contact mix earns at his best landing spot (Coors excluded) than at home, with '
        'overall park quality removed (so the answer isn\'t just "trade everyone to '
        'Cincinnati"). Coors is excluded. A home ranking in the 20s is fit value a front office '
        'can acquire for free.</div>', unsafe_allow_html=True)
    l, r = st.columns(2)
    with l:
        st.markdown("**Most held back** (worst home-park fits)")
        _t = hb.sort_values(["home_rank", "upgrade"], ascending=[False, False]).head(12)[
            ["batter_name", "home_park", "home_rank", "alt_park", "upgrade"]].rename(
            columns={"batter_name": "Hitter", "home_park": "Home",
                     "home_rank": "Home Rk", "alt_park": "Best Landing Spot",
                     "upgrade": "Shape Gain"})
        ev = st.dataframe(_t, hide_index=True, use_container_width=True,
            on_select="rerun", selection_mode="single-row",
            key=f"tbl_tb_a_{st.session_state.jump_n}",
            column_config={"Shape Gain": st.column_config.NumberColumn(format="%+.3f"),
                           "Home Rk": st.column_config.NumberColumn(format="%.0f")})
        row_jump(ev, _t, "Hitter", "sel_player", "Player Park Fit")
    with r:
        st.markdown("**Best-situated** (home is near-optimal)")
        _t = hb.sort_values(["home_rank", "upgrade"]).head(12)[
            ["batter_name", "home_park", "home_rank", "upgrade"]].rename(
            columns={"batter_name": "Hitter", "home_park": "Home",
                     "home_rank": "Home Rk", "upgrade": "Shape Gain"})
        ev = st.dataframe(_t, hide_index=True, use_container_width=True,
            on_select="rerun", selection_mode="single-row",
            key=f"tbl_tb_b_{st.session_state.jump_n}",
            column_config={"Shape Gain": st.column_config.NumberColumn(format="%+.3f"),
                           "Home Rk": st.column_config.NumberColumn(format="%.0f")})
        row_jump(ev, _t, "Hitter", "sel_player", "Player Park Fit")
    st.caption("Click any hitter to open his Park Fit page.")
    if n_excl:
        st.caption(f"{n_excl} hitters excluded from the board (no home park detected — "
                   f"typically too few recent home batted balls).")

    st.markdown("### The league at a glance")
    sc_df = players.dropna(subset=["hr_pct", "spread"])
    sc = (alt.Chart(sc_df)
        .mark_circle(size=90, opacity=.65)
        .encode(x=alt.X("hr_pct:Q", title="HR% per batted ball"),
                y=alt.Y("spread:Q", title="Park spread (best − worst fit delta)"),
                color=alt.Color("k_pct:Q", title="K%", scale=alt.Scale(scheme="magma")),
                tooltip=["batter_name", alt.Tooltip("hr_pct:Q", format=".1f"),
                         alt.Tooltip("k_pct:Q", format=".1f"),
                         alt.Tooltip("spread:Q", format=".3f")])
        .properties(height=420))
    st.altair_chart(sc, use_container_width=True)
    st.caption("Bottom-right = park-proof power. High-K hitters (bright) also face a second "
               "channel of park variation: strikeout environments (shown, not modeled).")

# ================= PAGE 4: GAME =================
if page == "Game":
    import random

    st.markdown("### Higher or Lower: Park Edition")

    @st.cache_data
    def _load_game_deltas(stamp):
        d2 = pd.read_parquet(ROOT / "data" / "model" / "deltas_coarse.parquet")
        try:
            ph2 = pd.read_parquet(ROOT / "data" / "model" / "deltas_parkhand.parquet")
        except Exception:
            ph2 = pd.DataFrame()
        return d2, ph2

    _mp = ROOT / "data" / "model" / "deltas_coarse.parquet"
    if not _mp.exists():
        st.info("The game needs data/model/deltas_coarse.parquet (created by "
                "scripts/02_fit_bucket_model.py).")
    else:
        d2, ph2 = _load_game_deltas((_mp.stat().st_mtime,))

        game_pool_df = (players[players["tier"] == "full"]
                        .sort_values("n_balls", ascending=False).head(250))
        pool_by_hand = {
            "RHH": game_pool_df[game_pool_df["stand_bucket"] == "RHH"]["batter"].tolist(),
            "LHH": game_pool_df[game_pool_df["stand_bucket"] == "LHH"]["batter"].tolist(),
        }
        game_pool = game_pool_df["batter"].tolist()
        delta_lookup = scores.set_index(["batter", "park"])["park_fit_delta"]

        MODES = {
            "Casual": dict(min_gap=0.004, max_gap=99, same_hand=False,
                           show_stats=True, show_blurb=True),
            "Scout": dict(min_gap=0.0022, max_gap=0.010, same_hand=True,
                          show_stats=False, show_blurb=True),
            "Front Office": dict(min_gap=0.0012, max_gap=0.006, same_hand=True,
                                 show_stats=False, show_blurb=False),
        }

        def park_hero(park):
            meta = team_meta(park)
            d = park_dims(park)
            svg = ""
            pills = ""
            if d:
                lf, cf, rf = int(d["lf_line"]), int(d["cf"]), int(d["rf_line"])
                svg = field_svg(lf, cf, rf, "#ffffff", meta[3])
                pills = ('<div class="dpills" style="max-width:320px;margin:.6rem auto 0">'
                         + "".join(
                    f'<div class="dpill" style="background:rgba(255,255,255,.14);'
                    f'border-color:rgba(255,255,255,.25)">'
                    f'<div class="dpl" style="color:#e2e8f0">{lab}</div>'
                    f'<div class="dpv" style="color:#fff">{v}</div></div>'
                    for lab, v in [("LF", lf), ("CF", cf), ("RF", rf)]) + '</div>')
            lg = (f'<img src="{logo(meta[1])}" style="width:52px;height:52px;'
                  f'object-fit:contain;filter:drop-shadow(0 2px 6px rgba(0,0,0,.4))">'
                  if meta[1] else "")
            return (f'<div style="background:linear-gradient(135deg,{meta[2]} 0%,#0b1f3a 130%);'
                    f'border-radius:20px;padding:1.3rem 1.4rem;margin:.6rem 0 1rem 0;'
                    f'box-shadow:0 14px 34px rgba(15,23,42,.28);text-align:center;color:#fff">'
                    f'<div style="display:flex;align-items:center;justify-content:center;'
                    f'gap:.8rem">{lg}<div style="font-size:1.6rem;font-weight:900;'
                    f'letter-spacing:-.02em">{html.escape(park)}</div></div>'
                    f'<div style="max-width:340px;margin:0 auto">{svg}</div>{pills}</div>')

        def _phrase(r):
            spray = {"ExtremePull": "extreme pull-side", "Pull": "pull-side",
                     "Center": "center-field", "Oppo": "opposite-field",
                     "ExtremeOppo": "extreme oppo"}.get(r["spray_bucket"], r["spray_bucket"])
            la = {"Low": "low liners", "Line": "line drives", "IdealAir": "ideal-air flies",
                  "HighAir": "high flies"}.get(r["la_bucket"], r["la_bucket"])
            return f'{r["stand_bucket"]} {spray} {la}'

        def park_blurb(park, with_numbers=True):
            sub = d2[(d2["park"] == park)
                     & (~d2["la_bucket"].isin(["GB", "Popup"]))]
            for _n in (80, 40, 15):
                if (sub["l2_n"] >= _n).sum() >= 4:
                    sub = sub[sub["l2_n"] >= _n]
                    break
            tops = sub.nlargest(2, "delta_l2")
            bots = sub.nsmallest(2, "delta_l2")
            if with_numbers:
                rewards = " · ".join(f'{_phrase(r)} ({r["delta_l2"]:+.3f})'
                                     for _, r in tops.iterrows())
                punishes = " · ".join(f'{_phrase(r)} ({r["delta_l2"]:+.3f})'
                                      for _, r in bots.iterrows())
            else:
                rewards = " · ".join(_phrase(r) for _, r in tops.iterrows())
                punishes = " · ".join(_phrase(r) for _, r in bots.iterrows())
            return (f'<div class="insight"><b>How it plays:</b> rewards {rewards or "—"}. '
                    f'Punishes {punishes or "—"}.'
                    '<br><span style="color:#64748b;font-size:.85rem">From historical '
                    'outcomes vs league average for each contact type, visiting hitters '
                    'only.</span></div>')

        def new_round(park_choice, mode):
            cfg = MODES[mode]
            park = (random.choice(sorted(CURRENT_PARKS_2026))
                    if park_choice == "🎲 Random park" else park_choice)
            pair = None
            for _ in range(120):
                if cfg["same_hand"]:
                    hand = random.choice(["RHH", "LHH"])
                    if len(pool_by_hand[hand]) < 2:
                        continue
                    a, b = random.sample(pool_by_hand[hand], 2)
                else:
                    a, b = random.sample(game_pool, 2)
                try:
                    da = float(delta_lookup.loc[(a, park)])
                    db = float(delta_lookup.loc[(b, park)])
                except KeyError:
                    continue
                gap = abs(da - db)
                if cfg["min_gap"] <= gap <= cfg["max_gap"]:
                    pair = (a, b, da, db)
                    break
            if pair is None:
                return None
            a, b, da, db = pair
            return {"park": park, "a": a, "b": b, "da": da, "db": db,
                    "revealed": False, "picked": None, "mode": mode}

        if "game_streak" not in st.session_state:
            st.session_state.game_streak = 0
            st.session_state.game_best = 0
            st.session_state.game_round_id = 0
            st.session_state.game = None

        cc1, cc2 = st.columns([1.4, 1])
        with cc1:
            park_options = ["🎲 Random park"] + sorted(CURRENT_PARKS_2026)
            park_choice = st.selectbox("Park", park_options, key="game_park_choice")
        with cc2:
            mode = st.selectbox("Difficulty", list(MODES.keys()), key="game_mode",
                help="Casual: full scouting info, clear gaps. Scout: same-handed "
                     "hitters, no stat lines. Front Office: park intel hidden until "
                     "after your call, razor-thin gaps.")

        g = st.session_state.game
        needs_new = (
            g is None
            or g.get("mode") != mode
            or (park_choice != "🎲 Random park" and g["park"] != park_choice
                and not g["revealed"])
        )
        if needs_new:
            st.session_state.game = new_round(park_choice, mode)
            st.session_state.game_round_id += 1
            g = st.session_state.game

        if g is None:
            st.warning("Couldn't build a matchup for that park/difficulty — try another.")
        else:
            cfg = MODES[g["mode"]]
            s1, s2 = st.columns(2)
            s1.metric("Streak 🔥", st.session_state.game_streak)
            s2.metric("Best", st.session_state.game_best)

            st.markdown(park_hero(g["park"]), unsafe_allow_html=True)
            if cfg["show_blurb"] or g["revealed"]:
                st.markdown(park_blurb(g["park"], with_numbers=g["revealed"]),
                            unsafe_allow_html=True)
            else:
                st.markdown('<div class="insight">🕶️ <b>Front Office mode:</b> no park '
                            'intel until you commit. You should know your parks.</div>',
                            unsafe_allow_html=True)

            pa_row = players[players["batter"] == g["a"]].iloc[0]
            pb_row = players[players["batter"] == g["b"]].iloc[0]

            def game_card(row, show_stats):
                if show_stats:
                    sub_line = (f'{row["stand_bucket"]} · '
                                f'{fmt(row.get("archetype"), "{}")} · '
                                f'EV {fmt(row.get("avg_ev"), "{:.1f}")} · '
                                f'Pull Air {fmt(row.get("pull_air_rate"), "{:.1%}")}')
                else:
                    sub_line = f'{row["stand_bucket"]}'
                return (f'<div class="card" style="margin-bottom:.6rem;text-align:center">'
                        f'<div class="hswrap" style="width:96px;height:96px;padding:3px;'
                        f'margin:0 auto"><img class="hs" style="width:90px;height:90px" '
                        f'src="{headshot(row["batter"])}"></div>'
                        f'<div class="pname" style="font-size:1.3rem;margin-top:.5rem">'
                        f'{html.escape(str(row["batter_name"]))}</div>'
                        f'<div class="psub">{sub_line}</div></div>')

            st.markdown(f"#### Whose contact shape fits **{g['park']}** better?")
            colA, colB = st.columns(2)
            with colA:
                st.markdown(game_card(pa_row, cfg["show_stats"]), unsafe_allow_html=True)
                if not g["revealed"]:
                    if st.button(f"{pa_row['batter_name']}",
                                 key=f"pickA_{st.session_state.game_round_id}",
                                 use_container_width=True):
                        g["picked"] = "a"
                        g["revealed"] = True
                        if g["da"] > g["db"]:
                            st.session_state.game_streak += 1
                        else:
                            st.session_state.game_streak = 0
                        st.session_state.game_best = max(
                            st.session_state.game_best, st.session_state.game_streak)
                        st.rerun()
            with colB:
                st.markdown(game_card(pb_row, cfg["show_stats"]), unsafe_allow_html=True)
                if not g["revealed"]:
                    if st.button(f"{pb_row['batter_name']}",
                                 key=f"pickB_{st.session_state.game_round_id}",
                                 use_container_width=True):
                        g["picked"] = "b"
                        g["revealed"] = True
                        if g["db"] > g["da"]:
                            st.session_state.game_streak += 1
                        else:
                            st.session_state.game_streak = 0
                        st.session_state.game_best = max(
                            st.session_state.game_best, st.session_state.game_streak)
                        st.rerun()

            if g["revealed"]:
                winner_is_a = g["da"] > g["db"]
                picked_winner = (g["picked"] == "a") == winner_is_a
                win_row = pa_row if winner_is_a else pb_row
                if picked_winner:
                    st.success(f"✅ Correct — **{win_row['batter_name']}** fits "
                               f"{g['park']} better.")
                else:
                    st.error(f"❌ Not this time — **{win_row['batter_name']}** fits "
                             f"{g['park']} better.")

                def why(batter_id):
                    subc = contributions[(contributions["batter"] == batter_id)
                                         & (contributions["park"] == g["park"])].copy()
                    if subc.empty:
                        return "—"
                    air = subc[subc["la_bucket"] != "GB"]
                    if not air.empty:
                        subc = air
                    r = subc.loc[subc["bucket_contribution"].abs().idxmax()]
                    arrow = "▲" if r["bucket_contribution"] > 0 else "▼"
                    return (f'{arrow} {r["spray_bucket"]} {r["la_bucket"]} '
                            f'{r["ev_bucket"]} mph ({r["bucket_contribution"]:+.4f})')

                r1, r2 = st.columns(2)
                r1.metric(pa_row["batter_name"], f'{g["da"]:+.4f}',
                          help="Park Fit Δ at this park")
                r1.caption(why(g["a"]))
                r2.metric(pb_row["batter_name"], f'{g["db"]:+.4f}',
                          help="Park Fit Δ at this park")
                r2.caption(why(g["b"]))

                if st.button("Next matchup ⚾", type="primary",
                             key=f"next_{st.session_state.game_round_id}",
                             use_container_width=True):
                    st.session_state.game = new_round(park_choice, mode)
                    st.session_state.game_round_id += 1
                    st.rerun()

# ================= PAGE 5 =================
if page == "Methodology":
    st.markdown("""
<div class="card">
<h2>Methodology</h2>
<p>Every park factor you've ever seen answers the same question: how does this ballpark play for
the average hitter? ParkFit asks a different one how does it play for <i>this</i> hitter? No
hitter is average. Isaac Paredes and Vladimir Guerrero Jr. are both right-handed power bats, and
they need completely different ballparks, because one lives on pulled fly balls and the other
scorches line drives everywhere. A model that can't tell them apart isn't measuring fit.</p>
<h3>Start with the contact itself</h3>
<p>The engine is simple to state: every batted ball since 2021 more than 619,000 of them gets
sorted into a bucket by who hit it (lefty or righty), where it went off the bat (pull side through
opposite field, always from the hitter's perspective), how hard it was hit, and at what angle.
Then, for every park, we ask history: how did this exact type of contact do here, compared to the
same contact everywhere else? No wall-geometry simulation, no wind models we don't have reliable
enough data for every ball to do that honestly, and a model that pretends to is just wrong with
extra steps. Historical outcomes are the engine.</p>
<h3>Only visiting hitters count toward park effects</h3>
<p>Home hitters are a trap. Teams build rosters and coach swings to exploit their own park
Yankee Stadium's numbers are full of lefties acquired specifically to pull balls at that short
porch. Include them and you're measuring roster construction, not the park. So park effects here
come from visiting hitters only: a rotating, roughly league-average sample that has no idea which
park it's about to play in.</p>
<h3>Small samples borrow, they don't shout</h3>
<p>The catch with fine-grained buckets is that the cells that matter most extreme pull, high
exit velocity, ideal launch are exactly the thinnest ones. Trust them raw and you get noise;
zero them out and every pull hitter looks like every other hitter, which is the problem we
started with. So each cell borrows strength from its parents: a thin park-specific cell leans on
the same park's broader pattern, which leans on the park's overall effect. How much to trust the
thin cells wasn't a judgment call it was chosen by splitting the data in half and picking the
setting where both halves agreed most.</p>
<h3>Raw fit vs shape edge</h3>
<p>One thing jumps out fast: Coors, Great American, and Fenway top the raw rankings for nearly
everyone, because a great hitter's park is great for all hitters. That's real, but it's not the
interesting part. <b>Shape Edge</b> strips it out it asks how much more this hitter's contact
mix earns at a park than the average same-handed hitter's would. That's the number behind the
Best Shape Fit card, the Park Lens, the trade board, and the free agency board. The values look
small. That's honest: park fit is a real edge, not a superpower, and pretending otherwise would
be the fastest way to lose a sharp reader.</p>
<h3>How we know it works</h3>
<p>Three checks. First, stability: fit the model on half the data, fit it again on the other
half, and see whether both halves rank parks the same way for each hitter median agreement of
0.49 across 685 hitters, with the shakiest results belonging to low-sample bench players, which
is exactly where uncertainty should live. Second, physics: ground balls shouldn't care much about
parks (infields are basically identical), and in the fitted model they don't ground-ball park
effects are half as dispersed as air-ball effects. Third, the eye test: without being told about
a single wall, the model rediscovered Yankee Stadium's short porch, the Crawford Boxes, and
Fenway's suppression of left-handed pull power and ranked Minute Maid a top-5 park for Paredes,
the exact thesis behind a real MLB trade, while ranking it 23rd for Guerrero.</p>
<h3>What it doesn't do</h3>
<p>This is a contact-only tool. Strikeouts and walks are shown for context but never folded into
the projections; aging, approach changes, pitcher quality, and lineup context are all out of
scope. A few technical honesty notes: hit coordinates are occasionally missing on home runs
(0.58% — audited, immaterial); park configurations that changed recently, like Camden Yards and
Sacramento, carry wider uncertainty than long-tenured parks; and a hitter's own profile is partly
shaped by the park he calls home, which no model of this kind can fully remove. ParkFit measures
<i>fit</i>, not <i>talent</i> where a swing plays best, not how good it is.</p>
</div>
""", unsafe_allow_html=True)

st.markdown(
    '<div style="text-align:center;color:#94a3b8;font-weight:700;font-size:.85rem;'
    'padding:1.6rem 0 .6rem 0">Created by Oliver Duthie · ParkFit · '
    'Statcast data 2021–present</div>', unsafe_allow_html=True)