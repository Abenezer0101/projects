"""Render the analysis charts as PNGs.

Colour follows the same rules as the dashboards in this repo: one hue for a
single measure, the validated blue/orange pair for two series, no dual axes,
recessive grid.  Run: python3 plots.py
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd, pathlib
from clean import clean

BLUE, ORANGE = "#2a78d6", "#eb6834"
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#dfe1e5"
HERE = pathlib.Path(__file__).parent
CHARTS = HERE / "charts"; CHARTS.mkdir(exist_ok=True)

plt.rcParams.update({
    "figure.facecolor": "white", "axes.facecolor": "white",
    "font.family": "DejaVu Sans", "font.size": 10,
    "axes.edgecolor": GRID, "axes.labelcolor": MUTED,
    "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.titlecolor": INK, "axes.titlesize": 12, "axes.titleweight": "bold",
    "axes.spines.top": False, "axes.spines.right": False,
})

def style(ax, title, sub=None):
    ax.set_title(title, loc="left", pad=14 if sub else 8)
    if sub:
        ax.text(0, 1.03, sub, transform=ax.transAxes, fontsize=9, color=MUTED)
    ax.grid(axis="y", color=GRID, linewidth=.8)
    ax.set_axisbelow(True)

df, _ = clean()

# 1. Trips by hour — weekday vs weekend. Both are counts, so one axis is honest.
fig, ax = plt.subplots(figsize=(9, 4.2))
wd = df[df.dow < 5].groupby("hour").size().reindex(range(24), fill_value=0)
we = df[df.dow >= 5].groupby("hour").size().reindex(range(24), fill_value=0)
# normalise to trips-per-day so 5 weekdays don't dwarf 2 weekend days
wd = wd / df[df.dow < 5].started_at.dt.date.nunique()
we = we / df[df.dow >= 5].started_at.dt.date.nunique()
ax.plot(wd.index, wd.values, color=BLUE, lw=2, label="Weekday")
ax.plot(we.index, we.values, color=ORANGE, lw=2, label="Weekend")
style(ax, "When people ride", "Average trips per day, by hour — normalised so weekdays and weekends compare")
ax.set_xlabel("Hour of day"); ax.set_ylabel("Trips per day")
ax.set_xticks(range(0, 24, 2))
ax.set_ylim(0, max(wd.max(), we.max()) * 1.25)   # headroom so peak labels clear the subtitle
ax.legend(frameon=False, labelcolor=MUTED)
for h in (8, 17):
    ax.annotate(f"{h}:00", xy=(h, wd[h]), xytext=(0, 9), textcoords="offset points",
                ha="center", fontsize=9, color=BLUE, fontweight="bold")
fig.tight_layout(); fig.savefig(CHARTS / "trips_by_hour.png", dpi=150); plt.close(fig)

# 2. Duration by user type — distribution, not just a mean
fig, ax = plt.subplots(figsize=(9, 4.2))
for name, colour in (("member", BLUE), ("casual", ORANGE)):
    s = df[df.user_type == name].duration_min
    ax.hist(s, bins=range(0, 65, 2), alpha=.72, color=colour,
            label=f"{name} (median {s.median():.1f} min)")
style(ax, "Members ride short; casual riders wander",
      "Trip duration distribution, trips under 65 minutes")
ax.set_xlabel("Duration (minutes)"); ax.set_ylabel("Trips")
ax.legend(frameon=False, labelcolor=MUTED)
fig.tight_layout(); fig.savefig(CHARTS / "duration_by_user.png", dpi=150); plt.close(fig)

# 3. Busiest stations — one measure across categories, so ONE hue
fig, ax = plt.subplots(figsize=(9, 4.4))
top = df.start_station.value_counts().head(10).sort_values()
ax.barh(top.index, top.values, color=BLUE, height=.68)
style(ax, "Busiest departure stations", "Trips started, full period")
ax.grid(axis="x", color=GRID, linewidth=.8); ax.grid(axis="y", visible=False)
ax.set_xlabel("Trips started")
for i, v in enumerate(top.values):
    ax.text(v + max(top.values) * .01, i, f"{v:,}", va="center", fontsize=9, color=MUTED)
fig.tight_layout(); fig.savefig(CHARTS / "top_stations.png", dpi=150); plt.close(fig)

print("wrote:", ", ".join(p.name for p in sorted(CHARTS.glob("*.png"))))
for p in sorted(CHARTS.glob("*.png")):
    print(f"  {p.name:24}{p.stat().st_size/1024:>7.0f} KB")
