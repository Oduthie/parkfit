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
@media (max-width:700px){ .dgrid,.sgrid{grid-template-columns:1fr;} .hero h1{font-size:2.1rem;} }
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

# ---- 2026 view: only parks in use this season, only active hitters --------
scores = scores[scores["park"].isin(CURRENT_PARKS_2026)].copy()
if not extras.empty and "last_year" in extras.columns:
    active_ids = set(extras.loc[extras["last_year"] >= 2025, "batter"])
    scores = scores[scores["batter"].isin(active_ids)]
contributions = contributions[contributions["park"].isin(CURRENT_PARKS_2026)]

# Re-rank and re-spread within the 2026 park set.
scores["park_rank"] = (scores.groupby("batter")["park_fit_delta"]
                       .rank(ascending=False, method="min").astype(int))
_dep = scores.groupby("batter")["park_fit_delta"].agg(lambda s: s.max() - s.min())
scores["park_dependency_score"] = scores["batter"].map(_dep)

# Fit vs Avg (old-site semantics): this park's delta for the player, minus
# the average delta of same-handed scored hitters in that park — the pure
# player-park interaction above/below the typical RHH/LHH.
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
if not extras.empty:
    players = players.merge(extras, on="batter", how="left")
else:
    for c in ["k_pct", "bb_pct", "hr_pct", "home_park", "pa"]:
        players[c] = pd.NA

# Home rank + realistic upgrade (Coors excluded, like the old trade board).
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
    best_alt = realistic.loc[realistic["projected_contact_woba"].idxmax()]
    home_rows.append({
        "batter": p["batter"],
        "home_rank": int(home["park_rank"].iloc[0]),
        "home_woba": float(home["projected_contact_woba"].iloc[0]),
        "alt_park": best_alt["park"],
        "upgrade": float(best_alt["projected_contact_woba"]
                         - home["projected_contact_woba"].iloc[0]),
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

tab1, tab2, tab3, tab4 = st.tabs(
    ["Player Park Fit", "Compare Hitters", "League Insights", "Methodology"])

# ================= TAB 1 =================
with tab1:
    name = st.selectbox("Choose hitter", sorted(players["batter_name"].dropna().unique()))
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
            if info["upgrade"] >= 0.010:
                badges += (f'<span class="badge b-red">Held back: +{info["upgrade"]:.3f} at '
                           f'{html.escape(str(info["alt_park"]))}</span>')
            elif int(info["home_rank"]) <= 3:
                badges += '<span class="badge b-green">Well placed</span>'
        if info["tier"] == "provisional":
            badges += '<span class="badge b-orange">Provisional sample</span>'
        st.markdown(player_card(name, info, badges), unsafe_allow_html=True)

        st.markdown('<div class="sgrid">'
            + scard("Best Park", best["park"], f'{best["projected_contact_woba"]:.3f} proj wOBA')
            + scard("Worst Park", worst["park"], f'{worst["projected_contact_woba"]:.3f} proj wOBA')
            + scard("Park Spread", f"{spread:.3f}",
                    f'{pct:.0f}th pct — '
                    + ("park-proof" if pct < 30 else "park-sensitive" if pct > 70 else "typical"))
            + scard("Air-Pull%", fmt(info.get("pull_air_rate"), "{:.1%}"),
                    "pulled balls in the air")
            + scard("HR% / K%",
                    f'{fmt(info.get("hr_pct"), "{:.1f}")} / {fmt(info.get("k_pct"), "{:.1f}")}',
                    "per BBE / per PA")
            + '</div>', unsafe_allow_html=True)

        bestfit = pr.loc[pr["fit_vs_avg"].idxmax()]
        home_line = ""
        if has_home:
            if info["upgrade"] >= 0.010:
                home_line = (f' His current home, <b>{html.escape(info["home_park"])}</b>, ranks '
                             f'<b>#{int(info["home_rank"])}</b> for his profile — a real cost: '
                             f'<b>{html.escape(str(info["alt_park"]))}</b> adds '
                             f'<b>{info["upgrade"]:+.3f}</b> wOBA (Coors excluded).')
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
            st.dataframe(show, hide_index=True, use_container_width=True, height=table_h,
                column_config={
                    "Proj wOBA": st.column_config.NumberColumn(format="%.3f"),
                    "Fit vs Avg": st.column_config.NumberColumn(format="%+.4f"),
                    "Park K%": st.column_config.NumberColumn(format="%.1f")})
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

# ================= TAB 2 =================
with tab2:
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

# ================= TAB 3 =================
with tab3:
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
                "Fit Δ": s.iloc[0]["fit_vs_avg"],
                "2nd": s.iloc[1]["park"] if len(s) > 1 else "—",
                "3rd": s.iloc[2]["park"] if len(s) > 2 else "—",
            })
        if fa_rows:
            fa_df = pd.DataFrame(fa_rows).sort_values("Fit Δ", ascending=False)
            st.markdown(
                '<div class="insight">Upcoming 2026-27 free agent hitters, ranked by how '
                'much their <b>best realistic landing spot</b> (Coors excluded) rewards their '
                'contact shape. High-spread names are the ones where the signing park genuinely '
                'changes the player. Edit <b>free_agents_2026.csv</b> to update the class.</div>',
                unsafe_allow_html=True)
            st.dataframe(fa_df, hide_index=True, use_container_width=True,
                column_config={
                    "Spread": st.column_config.NumberColumn(format="%.3f"),
                    "Fit Δ": st.column_config.NumberColumn(format="%+.4f")})
        missing_fa = [fa for fa in fa_names if norm_name(fa) not in name_map]
        if missing_fa:
            st.caption("Not matched (name spelling, or below the batted-ball minimum): "
                       + ", ".join(missing_fa))

    hb = players.dropna(subset=["upgrade", "home_rank"]).copy()
    n_excl = players["home_rank"].isna().sum()

    st.markdown("### The trade board — who's in the wrong park?")
    st.markdown(
        '<div class="insight">Each hitter\'s current home ranked against all parks <b>for his '
        'specific contact profile</b>. Upgrade is measured against his best <b>realistic</b> park '
        '— Coors is excluded, since it tops nearly every list and would reduce the board to '
        'distance-from-Denver. A home ranking in the 20s is fit value a front office can acquire '
        'for free.</div>', unsafe_allow_html=True)
    l, r = st.columns(2)
    with l:
        st.markdown("**Most held back** (worst home-park fits)")
        t = hb.sort_values(["home_rank", "upgrade"], ascending=[False, False]).head(12)[
            ["batter_name", "home_park", "home_rank", "alt_park", "upgrade"]]
        st.dataframe(t.rename(columns={"batter_name": "Hitter", "home_park": "Home",
            "home_rank": "Home Rk", "alt_park": "Best Realistic", "upgrade": "wOBA Gain"}),
            hide_index=True, use_container_width=True,
            column_config={"wOBA Gain": st.column_config.NumberColumn(format="%+.3f"),
                           "Home Rk": st.column_config.NumberColumn(format="%.0f")})
    with r:
        st.markdown("**Best-situated** (home is near-optimal)")
        t = hb.sort_values(["home_rank", "upgrade"]).head(12)[
            ["batter_name", "home_park", "home_rank", "upgrade"]]
        st.dataframe(t.rename(columns={"batter_name": "Hitter", "home_park": "Home",
            "home_rank": "Home Rk", "upgrade": "wOBA Gain"}),
            hide_index=True, use_container_width=True,
            column_config={"wOBA Gain": st.column_config.NumberColumn(format="%+.3f"),
                           "Home Rk": st.column_config.NumberColumn(format="%.0f")})
    if n_excl:
        st.caption(f"{n_excl} hitters excluded from the board (no home park detected — "
                   f"typically too few recent home batted balls).")

    st.markdown("### Park-proof vs park-dependent power")
    power = players[players["hr_pct"].fillna(0) >= 4.5]
    l, r = st.columns(2)
    with l:
        st.markdown("**Park-PROOF power** — production travels anywhere")
        t = power.nsmallest(12, "spread")[["batter_name", "hr_pct", "k_pct", "spread"]]
        st.dataframe(t.rename(columns={"batter_name": "Hitter", "hr_pct": "HR%",
            "k_pct": "K%", "spread": "Spread"}), hide_index=True, use_container_width=True,
            column_config={"Spread": st.column_config.NumberColumn(format="%.3f"),
                           "HR%": st.column_config.NumberColumn(format="%.1f"),
                           "K%": st.column_config.NumberColumn(format="%.1f")})
    with r:
        st.markdown("**Park-DEPENDENT power** — where they play changes what they are")
        t = power.nlargest(12, "spread")[["batter_name", "hr_pct", "k_pct", "spread"]]
        st.dataframe(t.rename(columns={"batter_name": "Hitter", "hr_pct": "HR%",
            "k_pct": "K%", "spread": "Spread"}), hide_index=True, use_container_width=True,
            column_config={"Spread": st.column_config.NumberColumn(format="%.3f"),
                           "HR%": st.column_config.NumberColumn(format="%.1f"),
                           "K%": st.column_config.NumberColumn(format="%.1f")})

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

# ================= TAB 4 =================
with tab4:
    st.markdown("""
<div class="card">
<h2>Methodology</h2>
<p>The question: <b>which parks historically reward the exact types of contact this hitter
produces?</b> Traditional park factors describe how a park plays for the average hitter; ParkFit
asks how it plays for <i>this</i> one.</p>
<h3>1. Career contact profiles, bucketed</h3>
<p>Every batted ball from 2021 to the present — 619,205 in total — bucketed by handedness,
batter-perspective spray direction (positive = pull, so RHH and LHH are compared correctly),
launch angle, and exit velocity. No wall-geometry simulation: without reliable wind, temperature,
spin, and wall data for every ball, a physics model looks advanced while being wrong. Historical
outcomes by contact shape are the engine. Older park configurations and temporary home parks are
used to fit the model, but rankings are shown only for the 30 parks in use for 2026, and only for
hitters active in the most recent season.</p>
<h3>2. Park effects from visiting hitters only</h3>
<p>Park deltas are fit exclusively on visiting hitters (315,448 balls). Home hitters are a
non-random sample — rosters are constructed and approaches coached to exploit the home park — so
including them would contaminate park estimates with roster construction, and would leak a scored
player's own home performance into his own score.</p>
<h3>3. Residuals, not raw averages</h3>
<p>Each ball's residual is its observed wOBA minus the league mean for its bucket. Park deltas are
averages of residuals, removing hitter-quality and bucket-mix confounding: a park doesn't look
homer-friendly just because good hitters visited it.</p>
<h3>4. Hierarchical shrinkage</h3>
<p>Fine cells (park × hand × spray × LA × EV) are thin exactly where the signal matters most —
extreme pull, high EV, ideal air. Shrinking them toward zero would erase park sensitivity for
pull-dependent hitters. Instead each level shrinks toward its parent: fine → coarse (EV collapsed)
→ park × handedness → prior. The shrinkage constant was tuned by out-of-sample stability (k = 40),
never against named-player comparisons.</p>
<h3>5. Scoring, Fit vs Avg, the trade board, and the FA board</h3>
<p>A player's bucket-frequency fingerprint is dotted with each park's shrunk deltas. <b>Fit vs
Avg</b> subtracts the average same-handed fit in each park, isolating the pure player-park
interaction — these values are honestly small; that is the true measured size of the effect. The
trade board detects each hitter's current home from his most recent home games and measures the
upgrade to his best realistic park, excluding Coors Field. The free agency board applies the same
lens to the upcoming class.</p>
<h3>Validation</h3>
<p><b>Split-half stability:</b> fit separately on even- and odd-numbered games, each player's park
rankings compared across the two independent fits — median Spearman <b>0.491 across 685
hitters</b>, with instability concentrated in low-sample bench players, exactly where uncertainty
should live. <b>Ground-ball check:</b> GB park deltas are half as dispersed as air-ball deltas
(0.032 vs 0.064) — parks differentiate on balls in the air, as physics says they must.
<b>Face validity:</b> the model independently ranks Minute Maid Park top-5 for Isaac Paredes —
recovering the thesis behind an actual MLB trade — while ranking it 23rd for Vladimir
Guerrero Jr.</p>
<h3>Honest limitations</h3>
<p>Contact only: strikeouts and walks are displayed for context, not folded into the projection.
Aging, approach changes, pitcher quality, and lineup context are out of scope. Hit coordinates are
occasionally missing on home runs (0.58% — audited, immaterial). Park eras (fence moves, temporary
homes) use a manual table. A hitter's fingerprint is itself partly shaped by his home park, which
no model of this kind can fully remove. The tool measures <i>fit</i>, not <i>talent</i>.</p>
</div>
""", unsafe_allow_html=True)