"""Correlation analysis for population vs GDP. Ground truth for the dashboard.
Run: python3 analyze.py [--json]"""
import csv, math, json, sys, pathlib
from collections import defaultdict

def load():
    rows = list(csv.DictReader(open(pathlib.Path(__file__).parent / "data" / "countries.csv")))
    for r in rows:
        r["pop"] = float(r["population_millions"])
        r["gdp"] = float(r["gdp_billions_usd"])
        r["pc"]  = r["gdp"] * 1e9 / (r["pop"] * 1e6)     # GDP per capita, USD
    return rows

def pearson(xs, ys):
    n = len(xs); mx = sum(xs)/n; my = sum(ys)/n
    sxy = sum((x-mx)*(y-my) for x, y in zip(xs, ys))
    sx = math.sqrt(sum((x-mx)**2 for x in xs)); sy = math.sqrt(sum((y-my)**2 for y in ys))
    return sxy/(sx*sy)

def analyze():
    rows = load()
    lg = lambda v: [math.log10(x) for x in v]
    pop = [r["pop"] for r in rows]; gdp = [r["gdp"] for r in rows]; pc = [r["pc"] for r in rows]
    reg = defaultdict(lambda: {"n":0,"pop":0.0,"gdp":0.0})
    for r in rows:
        d = reg[r["region"]]; d["n"] += 1; d["pop"] += r["pop"]; d["gdp"] += r["gdp"]
    return {
        "countries": len(rows),
        "total_pop_millions": round(sum(pop), 1),
        "total_gdp_billions": round(sum(gdp), 1),
        "r_pop_gdp":       round(pearson(pop, gdp), 3),
        "r_pop_gdp_log":   round(pearson(lg(pop), lg(gdp)), 3),
        "r_pop_pc":        round(pearson(pop, pc), 3),
        "r_pop_pc_log":    round(pearson(lg(pop), lg(pc)), 3),
        "richest": max(rows, key=lambda r: r["pc"])["country"],
        "poorest": min(rows, key=lambda r: r["pc"])["country"],
        "spread_x": round(max(pc)/min(pc)),
        "by_region": {k: {"n":v["n"], "pop":round(v["pop"],1), "gdp":round(v["gdp"],1),
                          "pc":round(v["gdp"]*1e9/(v["pop"]*1e6))} for k,v in reg.items()},
    }

if __name__ == "__main__":
    a = analyze()
    if "--json" in sys.argv:
        print(json.dumps(a)); raise SystemExit
    print(f"{a['countries']} countries · {a['total_pop_millions']:,.0f}M people · ${a['total_gdp_billions']:,.0f}B GDP\n")
    print(f"  population vs total GDP       r = {a['r_pop_gdp']:+.3f}   (log-log {a['r_pop_gdp_log']:+.3f})")
    print(f"  population vs GDP per capita  r = {a['r_pop_pc']:+.3f}   (log-log {a['r_pop_pc_log']:+.3f})")
    print(f"\n  per-capita spread: {a['spread_x']}x  ({a['poorest']} -> {a['richest']})")
    print("\n  region            n     pop(M)     GDP($B)   GDP/capita")
    for k, v in sorted(a["by_region"].items(), key=lambda x: -x[1]["gdp"]):
        print(f"  {k:16}{v['n']:>3}  {v['pop']:>9,.0f}  {v['gdp']:>10,.0f}   ${v['pc']:>8,}")
