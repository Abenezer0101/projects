"""Funnel conversion analysis. Ground truth for the dashboard.
Run: python3 analyze.py [--json]"""
import csv, json, sys, pathlib
from collections import defaultdict

STAGES = ["visitors", "leads", "qualified", "opportunity", "closed_won"]
LABELS = ["Visitors", "Leads", "Qualified", "Opportunity", "Closed Won"]

def load():
    return list(csv.DictReader(open(pathlib.Path(__file__).parent / "data" / "funnel.csv")))

def totals(rows):
    t = {s: 0 for s in STAGES}; t["revenue_usd"] = 0
    for r in rows:
        for k in list(t):
            t[k] += int(r[k])
    return t

def step_rates(t):
    """Conversion from each stage to the next, as percentages."""
    return [round(100 * t[STAGES[i+1]] / t[STAGES[i]], 2) for i in range(len(STAGES)-1)]

def analyze():
    rows = load()
    t = totals(rows)
    rates = step_rates(t)
    steps = [f"{LABELS[i]} → {LABELS[i+1]}" for i in range(len(LABELS)-1)]
    worst = min(range(len(rates)), key=lambda i: rates[i])

    by_channel = {}
    for ch in sorted({r["channel"] for r in rows}):
        ct = totals([r for r in rows if r["channel"] == ch])
        by_channel[ch] = {
            "visitors": ct["visitors"], "closed_won": ct["closed_won"],
            "revenue": ct["revenue_usd"],
            "overall_pct": round(100 * ct["closed_won"] / ct["visitors"], 3),
            "acv": round(ct["revenue_usd"] / ct["closed_won"]) if ct["closed_won"] else 0,
            "steps": step_rates(ct),
        }
    by_month = {}
    for m in sorted({r["month"] for r in rows}):
        mt = totals([r for r in rows if r["month"] == m])
        by_month[m] = {"visitors": mt["visitors"], "closed_won": mt["closed_won"],
                       "revenue": mt["revenue_usd"],
                       "overall_pct": round(100 * mt["closed_won"] / mt["visitors"], 3)}
    return {
        "stages": LABELS, "totals": [t[s] for s in STAGES],
        "revenue": t["revenue_usd"],
        "step_labels": steps, "step_rates": rates,
        "worst_step": steps[worst], "worst_rate": rates[worst],
        "overall_pct": round(100 * t["closed_won"] / t["visitors"], 3),
        "acv": round(t["revenue_usd"] / t["closed_won"]),
        "by_channel": by_channel, "by_month": by_month,
    }

if __name__ == "__main__":
    a = analyze()
    if "--json" in sys.argv:
        print(json.dumps(a)); raise SystemExit
    print("FUNNEL")
    for lbl, v in zip(a["stages"], a["totals"]):
        print(f"  {lbl:14}{v:>9,}")
    print(f"\n  overall visitor→won  {a['overall_pct']}%   revenue ${a['revenue']:,}   ACV ${a['acv']:,}")
    print("\nSTEP CONVERSION")
    for s, r in zip(a["step_labels"], a["step_rates"]):
        print(f"  {s:26}{r:>7.2f}%")
    print(f"\n  weakest step: {a['worst_step']} at {a['worst_rate']}%")
    print("\nBY CHANNEL")
    print(f"  {'channel':<14}{'visitors':>10}{'won':>6}{'overall':>9}{'ACV':>10}{'revenue':>12}")
    for ch, v in sorted(a["by_channel"].items(), key=lambda x: -x[1]["overall_pct"]):
        print(f"  {ch:<14}{v['visitors']:>10,}{v['closed_won']:>6}{v['overall_pct']:>8.3f}%"
              f"{v['acv']:>10,}{v['revenue']:>12,}")
