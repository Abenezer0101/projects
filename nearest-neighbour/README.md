# Nearest neighbour on real geography

Haversine distance, a 3-d tree, and the brute-force scan it has to beat — with
the crossover measured rather than quoted, and a demonstration that the
obvious way to build the tree returns wrong answers.

```
python3 benchmark.py                    # the crossover, uniform and clustered
python3 -m unittest discover -q tests   # 23 tests
```

## A k-d tree on lat/lon is wrong

This is the part worth knowing. A k-d tree prunes with axis-aligned planes, so
it only works if "close in the index" means "close in reality". Latitude and
longitude fail that: longitude wraps at 180, and a degree of longitude is
111 km at the equator and 0 km at the pole.

Six real Pacific places spanning the antimeridian — Suva, Funafuti,
Nuku'alofa, Apia, Mata-Utu, Auckland — and three queries:

| query | true nearest | 3-d tree | lat/lon tree |
| --- | --- | --- | --- |
| 14°S 179.5°E | Mata-Utu (474 km) | Mata-Utu ✓ | **Suva ✗** |
| 16°S 179.0°W | Suva (361 km) | Suva ✓ | **Mata-Utu ✗** |
| 20°S 179.9°E | Suva (257 km) | Suva ✓ | Suva ✓ |

Two of three wrong. (0°, 179.9°E) and (0°, 179.9°W) are 22 km apart on the
globe and 359.8 units apart in the lat/lon plane.

The fix is to leave that plane: map each point to a unit vector in 3-space.
The chord between unit vectors is `2·sin(θ/2)`, strictly increasing in the
great-circle distance, so ranking by chord equals ranking by arc length and
the tree prunes correctly with no seam anywhere. A test walks θ from 0° to
180° and asserts the monotonicity the whole approach rests on.

## Correctness

Haversine checked against standard figures: New York–London 5570.2 km,
Atlanta–Denver 1947.4 km (published ~1949, 0.08% out), pole-to-pole and the
equatorial quarter-turn exact to six places against π·R and π·R/2.

The tree is checked against brute force, which is the only oracle that
matters: all 50 US state capitals' nearest neighbours agree, plus random and
clustered point sets. Montgomery→Atlanta 235 km, Sacramento→Carson City
163 km, Denver→Cheyenne 156 km.

## The crossover

200 queries per row; distance counts are per query.

**Uniform on the sphere**

| n | brute (µs) | tree (µs) | speedup | bf dists | kd dists |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 5 | 1.3 | 2.9 | **0.4×** | 5 | 4.1 |
| 20 | 4.8 | 5.8 | **0.8×** | 20 | 9.9 |
| 50 | 11.3 | 6.1 | 1.9× | 50 | 11.6 |
| 1,000 | 212.7 | 9.8 | 21.7× | 1000 | 17.9 |
| 30,000 | 7352.1 | 19.6 | **375.4×** | 30000 | 26.9 |

The tree **loses** below about 50 points. The distance count explains it:
27 comparisons at n=30,000 is 0.09% of the set, but it carries recursion,
tuple indexing and a pruning test per node, and under about 50 points that
overhead exceeds the scan it replaces.

**Clustered in 12 tight clumps — what populated places actually look like**

| n | brute (µs) | tree (µs) | speedup | kd dists | share of n |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 50 | 11.2 | 9.4 | 1.2× | 18.9 | 38% |
| 1,000 | 218.2 | 93.2 | 2.3× | 155.2 | 16% |
| 30,000 | 7547.8 | 2158.1 | **3.5×** | 2539.6 | **8.5%** |

Same algorithm, same sizes, and the 375× becomes 3.5×. The pruning is what
collapses: on uniform points the tree touches 0.09% of the set, on clumped
points 8.5% — a rising absolute count rather than a logarithmic one. The
textbook promise assumes points that spread out, and geography does not.

## The build is not free

The tables above are per query and ignore construction. Building costs
117,530 µs at n=30,000, which is 16 queries' worth of the savings. Break-even
sits between 8 and 23 queries across every size and distribution measured.
**For a single query, at any size, scanning wins** — and a service that
rebuilds its index per request has bought nothing.

## Two bugs in my own benchmark

Worth recording because both produced plausible-looking tables.

The first version timed one fixed query, repeated 20 times. It reported
n=10,000 as *faster* than n=3,000, which is impossible — a single query can
land in an unusually easy part of the tree. Averaging over all 200 targets
fixed it and the timings became monotone.

The second: `SIZES` started at 100, so "the tree starts paying at n = 100"
was an artifact of where I began looking. Extending down to n=5 found the real
crossover at 50 and the region below it where the tree is 0.4× as fast.

## A note on the data

The capitals are real coordinates and are what the correctness checks use;
`validate()` bounds-checks every one, and a test transposes Atlanta's
longitude sign to confirm the check fires. The benchmark points are generated,
because the crossover is a property of the algorithm and the distribution and
no set of 50 cities is large enough to find it. Uniform sampling takes
latitude through `asin`, not uniformly in degrees — crowding the poles would
have quietly flattered the tree.

Stdlib only.
