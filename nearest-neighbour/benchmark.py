"""Where the tree starts paying -- measured, not assumed.

Three things decide it, and quoting a single crossover size hides two of them:

  1. the size of the point set
  2. how many queries amortise the one-time build
  3. the distribution -- a k-d tree prunes well on spread-out points and
     badly on clumped ones, and real geography is clumped

So the benchmark varies all three. Points are generated, not real: the
crossover is a property of the algorithms and the distribution, and no set of
50 capitals is large enough to find it. The capitals are what the correctness
check uses; this is what the timing uses.
"""

from __future__ import annotations

import math
import random
import time

from geo import to_unit_vector
from kdtree import SearchStats, brute_force, build, nearest

SIZES = [5, 10, 20, 50, 100, 300, 1_000, 3_000, 10_000, 30_000]


def uniform_sphere(n: int, rng: random.Random) -> list:
    """Uniform on the sphere: latitude by arcsin, not uniformly in degrees.

    Sampling latitude uniformly would crowd the poles and quietly make the
    tree look better than it is.
    """
    out = []
    for i in range(n):
        lon = rng.uniform(-180, 180)
        lat = math.degrees(math.asin(rng.uniform(-1, 1)))
        out.append((to_unit_vector(lat, lon), i))
    return out


def clustered(n: int, rng: random.Random, clusters: int = 12,
              spread_deg: float = 2.0) -> list:
    """Points in a few tight clumps, which is what populated places look like."""
    centres = [(rng.uniform(-60, 60), rng.uniform(-180, 180)) for _ in range(clusters)]
    out = []
    for i in range(n):
        clat, clon = centres[rng.randrange(clusters)]
        lat = max(-89.9, min(89.9, clat + rng.gauss(0, spread_deg)))
        lon = clon + rng.gauss(0, spread_deg)
        out.append((to_unit_vector(lat, lon), i))
    return out


def timed_over(fn, targets: list) -> float:
    """Microseconds per query, averaged over EVERY target.

    Timing one fixed query is what the first version of this file did, and it
    produced n=10,000 looking faster than n=3,000 -- a single query can land
    in an unusually easy or hard spot in the tree. Averaging over all 200
    targets removes that.
    """
    t0 = time.perf_counter()
    for t in targets:
        fn(t)
    return (time.perf_counter() - t0) / len(targets) * 1e6


def measure(make, n: int, queries: int = 200, seed: int = 0) -> dict:
    rng = random.Random(seed)
    items = make(n, rng)
    targets = [p for p, _ in uniform_sphere(queries, random.Random(seed + 1))]

    t0 = time.perf_counter()
    root = build(items)
    build_us = (time.perf_counter() - t0) * 1e6

    bf_stats, kd_stats = SearchStats(), SearchStats()
    for t in targets:
        brute_force(items, t, bf_stats)
        nearest(root, t, kd_stats)

    bf_us = timed_over(lambda t: brute_force(items, t), targets)
    kd_us = timed_over(lambda t: nearest(root, t), targets)
    return {
        "n": n,
        "build_us": build_us,
        "bf_us": bf_us,
        "kd_us": kd_us,
        "bf_calls": bf_stats.distance_calls / queries,
        "kd_calls": kd_stats.distance_calls / queries,
        "pruned": kd_stats.subtrees_pruned / queries,
    }


def report(label: str, make) -> list[dict]:
    print(f"\n{label}")
    print(f"  {'n':>7} {'brute (us)':>11} {'kdtree (us)':>12} {'speedup':>8} "
          f"{'bf dists':>9} {'kd dists':>9} {'build (us)':>11} {'queries to':>11}")
    print(f"  {'':>7} {'':>11} {'':>12} {'':>8} {'':>9} {'':>9} {'':>11} {'break even':>11}")
    rows = []
    for n in SIZES:
        r = measure(make, n)
        speedup = r["bf_us"] / r["kd_us"]
        saved = r["bf_us"] - r["kd_us"]
        breakeven = r["build_us"] / saved if saved > 0 else float("inf")
        r["speedup"], r["breakeven"] = speedup, breakeven
        be = f"{breakeven:.0f}" if math.isfinite(breakeven) else "never"
        print(f"  {n:>7} {r['bf_us']:>11.1f} {r['kd_us']:>12.1f} {speedup:>7.1f}x "
              f"{r['bf_calls']:>9.0f} {r['kd_calls']:>9.1f} {r['build_us']:>11.0f} {be:>11}")
        rows.append(r)
    return rows


def main() -> None:
    print("nearest neighbour: brute-force scan vs 3-d tree")
    print("distance counts are per query, averaged over 200 queries")
    uni = report("uniform on the sphere", uniform_sphere)
    clu = report("clustered in 12 tight clumps (what populated places look like)",
                 clustered)

    print("\nwhere the tree starts paying, per query:")
    for label, rows in (("uniform", uni), ("clustered", clu)):
        first = next((r["n"] for r in rows if r["speedup"] > 1.0), None)
        print(f"  {label:10} faster from n = {first}")
    print("\nand including the one-time build cost, the tree only pays once you")
    print("make more queries than the 'break even' column -- for a single query")
    print("on any size, scanning wins.")


if __name__ == "__main__":
    main()
