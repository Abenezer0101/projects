"""Clean the raw bike-share export and report exactly what changed.

Design rule: every row removed is counted and attributed. A cleaning script
that silently drops 8% of the data is indistinguishable from a broken one.

Run: python3 clean.py
"""
import pandas as pd, numpy as np, pathlib, json, sys

HERE = pathlib.Path(__file__).parent
RAW  = HERE / "data" / "trips_raw.csv"
OUT  = HERE / "data" / "trips_clean.csv"

# A ride shorter than this is a docking error; longer is an undocked bike.
MIN_MINUTES, MAX_MINUTES = 1.0, 24 * 60

def parse_dates(s):
    """The export mixes three date formats. Try each, keep whatever parses."""
    out = pd.Series(pd.NaT, index=s.index, dtype="datetime64[ns]")
    for fmt in ("%Y-%m-%d %H:%M:%S", "%m/%d/%Y %H:%M", "%d-%b-%Y %H:%M"):
        missing = out.isna()
        if not missing.any():
            break
        out[missing] = pd.to_datetime(s[missing], format=fmt, errors="coerce")
    return out

def clean():
    df = pd.read_csv(RAW, dtype=str)
    audit = [("rows read", len(df), "")]
    start_n = len(df)

    # 1. exact duplicate ride IDs
    before = len(df)
    df = df.drop_duplicates(subset="ride_id", keep="first")
    audit.append(("duplicate ride_id removed", before - len(df), "same ride exported twice"))

    # 2. station names: trim, collapse spaces, title-case, expand abbreviations
    for col in ("start_station", "end_station"):
        df[col] = (df[col].fillna("").str.strip().str.replace(r"\s+", " ", regex=True)
                     .str.title()
                     .str.replace(r"\bSt\.(?=\s|$)", "Street", regex=True)
                     .str.replace(r"\bPk\b", "Park", regex=True))
        # .title() lower-cases acronyms: MARTA -> Marta. Restore them.
        for acronym in ("MARTA",):
            df[col] = df[col].str.replace(rf"\b{acronym.title()}\b", acronym, regex=True)
    raw_names = pd.read_csv(RAW, dtype=str)["start_station"].dropna().nunique()
    audit.append(("station name variants collapsed", raw_names - df["start_station"].nunique(),
                  f"{raw_names} raw spellings -> {df['start_station'].nunique()} stations"))

    # 3. dates
    df["started_at"] = parse_dates(df["started_at"])
    df["ended_at"]   = parse_dates(df["ended_at"])
    before = len(df)
    df = df.dropna(subset=["started_at", "ended_at"])
    audit.append(("unparseable timestamps dropped", before - len(df), "three formats attempted"))

    # 4. duration and its two failure modes
    df["duration_min"] = (df["ended_at"] - df["started_at"]).dt.total_seconds() / 60
    before = len(df)
    neg = (df["duration_min"] < 0).sum()
    df = df[df["duration_min"] >= 0]
    audit.append(("negative durations dropped", neg, "end before start — clock skew"))

    before = len(df)
    short = (df["duration_min"] < MIN_MINUTES).sum()
    df = df[df["duration_min"] >= MIN_MINUTES]
    audit.append(("sub-minute trips dropped", short, "docking errors / rebalancing"))

    before = len(df)
    long_ = (df["duration_min"] > MAX_MINUTES).sum()
    df = df[df["duration_min"] <= MAX_MINUTES]
    audit.append(("trips over 24h dropped", long_, "bike never redocked"))

    # 5. missing values — filled, not dropped: the trip still happened
    miss_station = (df["end_station"] == "").sum()
    df.loc[df["end_station"] == "", "end_station"] = "Unknown"
    audit.append(("missing end stations labelled", miss_station, "kept as 'Unknown'"))

    miss_user = (df["user_type"].fillna("") == "").sum()
    df["user_type"] = df["user_type"].replace("", np.nan).fillna("unknown")
    audit.append(("missing user types labelled", miss_user, "kept as 'unknown'"))

    df["hour"] = df["started_at"].dt.hour
    df["dow"]  = df["started_at"].dt.dayofweek

    audit.append(("rows kept", len(df), f"{100*len(df)/start_n:.1f}% of input"))
    df.to_csv(OUT, index=False)
    return df, audit

def findings(df):
    m = df[df.user_type == "member"]["duration_min"]
    c = df[df.user_type == "casual"]["duration_min"]
    weekday = df[df.dow < 5]; weekend = df[df.dow >= 5]
    peak = df[df.dow < 5].groupby("hour").size()
    return {
        "trips": len(df),
        "median_all": round(df.duration_min.median(), 1),
        "median_member": round(m.median(), 1),
        "median_casual": round(c.median(), 1),
        "casual_vs_member_x": round(c.median() / m.median(), 2),
        "mean_all": round(df.duration_min.mean(), 1),
        "weekday_share": round(100 * len(weekday) / len(df), 1),
        "peak_hours": [int(h) for h in peak.nlargest(2).index],
        "member_share": round(100 * (df.user_type == "member").mean(), 1),
        "busiest_station": df.start_station.value_counts().idxmax(),
    }

if __name__ == "__main__":
    df, audit = clean()
    print(f"{'step':<34}{'rows':>7}   note")
    print("-" * 78)
    for step, n, note in audit:
        print(f"{step:<34}{n:>7,}   {note}")
    f = findings(df)
    print("\nFINDINGS")
    print(f"  median trip            {f['median_all']} min   (mean {f['mean_all']} — skewed by long tail)")
    print(f"  member median          {f['median_member']} min")
    print(f"  casual median          {f['median_casual']} min  = {f['casual_vs_member_x']}x members")
    print(f"  members                {f['member_share']}% of trips")
    print(f"  weekday share          {f['weekday_share']}%")
    print(f"  weekday peak hours     {f['peak_hours'][0]}:00 and {f['peak_hours'][1]}:00")
    print(f"  busiest start station  {f['busiest_station']}")
    if "--json" in sys.argv:
        print(json.dumps({"audit": audit, "findings": f}))
