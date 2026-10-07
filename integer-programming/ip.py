"""Branch and bound over the LP relaxation, with brute force as the oracle.

The two are not independent implementations of the same idea -- branch and
bound USES the relaxation. That is the point worth seeing: the LP bound is not
a curiosity to be reported alongside the integer answer, it is the thing that
makes finding the integer answer tractable. Every node whose relaxation
already costs more than the best integer solution found so far can be
discarded without exploring it.

`brute_force` enumerates every integer point in the box. It is exponential and
exists only to prove the search is correct.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from fractions import Fraction
from itertools import product

from lp import LinearProgramme


@dataclass
class Solution:
    x: list[int] | None
    cost: Fraction | None
    nodes: int = 0
    pruned_by_bound: int = 0
    lp_bound: Fraction | None = None


def _is_integral(point: list[Fraction]) -> bool:
    return all(v.denominator == 1 for v in point)


def branch_and_bound(cost: list, constraints: list, upper: list) -> Solution:
    lp = LinearProgramme(cost, constraints, upper)
    root = lp.solve()
    result = Solution(None, None)
    if root is None:
        return result
    result.lp_bound = root[1]

    best_x: list[int] | None = None
    best_cost: Fraction | None = None
    # each entry is a list of extra rows: (coefficients, rhs, sense)
    stack: list[list] = [[]]

    while stack:
        extra = stack.pop()
        result.nodes += 1
        node = lp.solve(extra)
        if node is None:
            continue
        point, value = node
        if best_cost is not None and value >= best_cost:
            result.pruned_by_bound += 1
            continue
        if _is_integral(point):
            best_x = [int(v) for v in point]
            best_cost = value
            continue
        # branch on the first fractional variable
        i = next(j for j, v in enumerate(point) if v.denominator != 1)
        unit = [Fraction(1) if j == i else Fraction(0) for j in range(len(cost))]
        floor_v = Fraction(math.floor(point[i]))
        stack.append(extra + [(unit, floor_v, -1)])        # x_i <= floor
        stack.append(extra + [(unit, floor_v + 1, 1)])     # x_i >= floor + 1

    result.x, result.cost = best_x, best_cost
    return result


def brute_force(cost: list, constraints: list, upper: list) -> Solution:
    """Every integer point in the box. The oracle, not a method."""
    ranges = [range(int(u) + 1) for u in upper]
    best_x, best_cost = None, None
    count = 0
    for point in product(*ranges):
        count += 1
        if not all(sum(a * x for a, x in zip(row, point)) >= rhs
                   for row, rhs in constraints):
            continue
        value = sum(Fraction(c) * x for c, x in zip(cost, point))
        if best_cost is None or value < best_cost:
            best_x, best_cost = list(point), value
    return Solution(best_x, best_cost, nodes=count)


def round_up_relaxation(cost: list, constraints: list, upper: list) -> Solution:
    """The thing people actually do: solve the LP, round every variable up.

    Always feasible for a covering problem (raising any variable can only help
    a >= constraint) and not always optimal -- the gap is measured rather than
    assumed.
    """
    root = LinearProgramme(cost, constraints, upper).solve()
    if root is None:
        return Solution(None, None)
    point = [math.ceil(v) for v in root[0]]
    value = sum(Fraction(c) * x for c, x in zip(cost, point))
    return Solution(point, value, lp_bound=root[1])
