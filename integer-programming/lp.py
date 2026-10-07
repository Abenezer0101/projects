"""An exact LP solver by vertex enumeration, in rational arithmetic.

The problems here are small -- a handful of variables -- so there is no need
for a simplex implementation whose correctness would itself need defending.
The optimum of a bounded linear programme sits at a vertex of the feasible
region, and a vertex is where n of the constraints hold with equality. So:
enumerate every subset of n constraints, solve the square system, discard the
infeasible points, and keep the best.

Everything is `fractions.Fraction`. An integrality gap of 0.0001 could be a
real gap or a rounding artifact, and with exact arithmetic that question never
arises -- the bound reported is the bound, not an approximation of it.

Form: minimise c.x subject to A x >= b and x >= 0.
"""

from __future__ import annotations

from fractions import Fraction
from itertools import combinations

Number = Fraction


def _solve_square(rows: list[list[Fraction]], rhs: list[Fraction]) -> list[Fraction] | None:
    """Gaussian elimination with exact fractions. None if singular."""
    n = len(rows)
    matrix = [row[:] + [rhs[i]] for i, row in enumerate(rows)]
    for col in range(n):
        pivot = next((r for r in range(col, n) if matrix[r][col] != 0), None)
        if pivot is None:
            return None
        matrix[col], matrix[pivot] = matrix[pivot], matrix[col]
        scale = matrix[col][col]
        matrix[col] = [v / scale for v in matrix[col]]
        for r in range(n):
            if r != col and matrix[r][col] != 0:
                factor = matrix[r][col]
                matrix[r] = [a - factor * b for a, b in zip(matrix[r], matrix[col])]
    return [matrix[i][n] for i in range(n)]


class LinearProgramme:
    """minimise c.x  s.t.  A x >= b,  x >= 0, optionally with upper bounds."""

    def __init__(self, cost: list, constraints: list[tuple[list, object]],
                 upper: list | None = None):
        self.cost = [Fraction(c) for c in cost]
        self.A = [[Fraction(a) for a in row] for row, _ in constraints]
        self.b = [Fraction(rhs) for _, rhs in constraints]
        self.n = len(self.cost)
        self.upper = [None if u is None else Fraction(u)
                      for u in (upper or [None] * self.n)]

    def _all_rows(self, extra: list[tuple[list[Fraction], Fraction, int]] | None = None):
        """Every constraint as (coefficients, rhs, sense) with sense +1 for >=
        and -1 for <=."""
        rows: list[tuple[list[Fraction], Fraction, int]] = []
        for row, rhs in zip(self.A, self.b):
            rows.append((row, rhs, 1))
        for i in range(self.n):                       # x_i >= 0
            unit = [Fraction(1) if j == i else Fraction(0) for j in range(self.n)]
            rows.append((unit, Fraction(0), 1))
            if self.upper[i] is not None:             # x_i <= u
                rows.append((unit, self.upper[i], -1))
        rows.extend(extra or [])
        return rows

    def solve(self, extra=None) -> tuple[list[Fraction], Fraction] | None:
        """Exact optimum, or None if infeasible. Unbounded raises."""
        rows = self._all_rows(extra)
        best_x, best_cost = None, None
        for picked in combinations(range(len(rows)), self.n):
            point = _solve_square([rows[i][0] for i in picked],
                                  [rows[i][1] for i in picked])
            if point is None:
                continue
            if not all(self._satisfies(point, rows[i]) for i in range(len(rows))):
                continue
            value = sum(c * x for c, x in zip(self.cost, point))
            if best_cost is None or value < best_cost:
                best_x, best_cost = point, value
        if best_cost is None:
            return None
        return best_x, best_cost

    @staticmethod
    def _satisfies(point: list[Fraction],
                   row: tuple[list[Fraction], Fraction, int]) -> bool:
        coeffs, rhs, sense = row
        lhs = sum(a * x for a, x in zip(coeffs, point))
        return lhs >= rhs if sense == 1 else lhs <= rhs
