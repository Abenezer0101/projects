# Integer programming: what the relaxation is good for

A cheapest-configuration problem solved three ways — the LP relaxation, the
relaxation rounded up, and the exact integer optimum — with branch and bound
checked against brute force and every number in exact rational arithmetic.

```
python3 solve.py                        # both instances, bounds and gaps
python3 -m unittest discover -q tests   # 20 tests
```

## The problem

Meet 60 vCPU and 200 GB of RAM at least cost, choosing integer counts of five
instance types. No single type satisfies both requirements.

| | cost | configuration |
| --- | ---: | --- |
| LP relaxation | 627.50 | fractional, so not buyable |
| round the LP up | 740.00 | 5 large, 2 cpu-opt |
| **integer optimum** | **635.00** | 1 medium, 5 large, 1 cpu-opt |
| brute force | 635.00 | agrees exactly |

**Integrality gap: 1.20%.** The relaxation is an excellent *bound* — it tells
you nothing cheaper than 627.50 exists, and the truth is 635.

**Cost of rounding: 16.54%.** The relaxation is a terrible *solution*. Solving
the LP and rounding every variable up — the thing people actually do, and it
is always feasible for a covering problem — pays 740 for what 635 buys. The
rounded answer is not even the same shape: it buys two cpu-opt instances where
the optimum buys one and adds a medium.

So the LP earns its place by bounding, not by answering. Which is exactly how
branch and bound uses it.

## The bound is what makes the search tractable

```
branch and bound:  51 nodes explored, 21 subtrees cut by the bound
brute force:       200,880 points visited (3,939x more)
```

Any node whose relaxation already costs more than the best integer solution
found so far can be discarded unexplored. That is not a separate optimisation
on top of the relaxation — it *is* the relaxation, doing the only job it is
good at.

`brute_force` is in the repository as the oracle, not as a method. Branch and
bound and brute force agree on the sizing problem and on random instances.

## A 1.2% gap is not the general case

Reporting only the instance above would invite the conclusion that the
relaxation is basically the answer. So: set cover where each set is the
complement of one singleton.

Element *e* is covered by every set except the one excluding it — *n−1* of the
*n* sets. The LP can therefore put 1/(n−1) on every set and satisfy each
element exactly, for a total of **n/(n−1)**, just over 1. Any *integer* cover
needs **2**, because one set always misses an element (a test checks every
single-set choice and confirms none covers).

| n | LP | integer | gap |
| ---: | ---: | ---: | ---: |
| 3 | 3/2 | 2 | 1.333× |
| 4 | 4/3 | 2 | 1.500× |
| 5 | 5/4 | 2 | 1.600× |

Closed form, so it extends past what the solver can reach:

| n | LP | integer | gap |
| ---: | ---: | ---: | ---: |
| 10 | 1.111111 | 2 | 1.800× |
| 1,000 | 1.001001 | 2 | 1.998× |
| 1,000,000 | 1.000001 | 2 | 2.000× |

The gap approaches 2× and never reaches it. A bound can be arbitrarily close
to half the true cost.

## Exact arithmetic, and why

Every number is a `fractions.Fraction`. An integrality gap of 0.0001 could be
a real gap or a floating-point artifact, and with exact arithmetic that
question never arises — 627.50 is 1255/2, and 3/2 against 2 is a fact rather
than a measurement.

## How the LP is solved, and its limit

By vertex enumeration: the optimum of a bounded linear programme sits where
*n* constraints hold with equality, so enumerate every *n*-subset, solve the
square system by exact Gaussian elimination, discard infeasible points, keep
the best. No simplex, and therefore no simplex correctness to defend.

It is validated by **strong duality**: for 113 random instances the dual — a
different LP, with different data — produced exactly the same optimum, with
no violations.

The limit is real and worth stating. Vertex enumeration is C(rows, n), so the
cover family is only solved up to n=5; n=6 needs C(18,6) = 18,564 systems per
LP call across many branch-and-bound nodes and does not finish. The closed
form covers the rest, and the solver confirms it where it can reach. A method
whose cost is a binomial coefficient is the right choice for five variables
and the wrong one for fifty.

Stdlib only.
