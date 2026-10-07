"""Tests. The LP solver is validated by strong duality, the integer search by
brute force, and the gap family against its closed form."""

from __future__ import annotations

import random
import unittest
from fractions import Fraction

from ip import branch_and_bound, brute_force, round_up_relaxation
from lp import LinearProgramme
from problems import (INSTANCE_TYPES, REQUIRED_RAM, REQUIRED_VCPU,
                      complement_cover, instance_sizing, predicted_cover_gap)

# The sizing problem's brute force enumerates 200,880 points. Several tests
# need it, so it is computed once -- a suite slow enough to skip is a suite
# that stops catching things.
_SIZING = instance_sizing()
_BB = branch_and_bound(*_SIZING[:3])
_BF = brute_force(*_SIZING[:3])


class TestLinearProgramme(unittest.TestCase):
    def test_a_worked_instance(self):
        lp = LinearProgramme([2, 3], [([1, 1], 4), ([1, 3], 6)])
        point, value = lp.solve()
        self.assertEqual(value, 9)
        self.assertEqual(point, [Fraction(3), Fraction(1)])

    def test_the_optimum_is_exact_not_floating_point(self):
        lp = LinearProgramme([1, 1], [([3, 0], 1)])
        _, value = lp.solve()
        self.assertIsInstance(value, Fraction)
        self.assertEqual(value, Fraction(1, 3))

    def test_the_solution_is_feasible(self):
        cost, constraints, upper, _ = instance_sizing()
        point, _ = LinearProgramme(cost, constraints, upper).solve()
        for row, rhs in constraints:
            self.assertGreaterEqual(sum(a * x for a, x in zip(row, point)), rhs)
        self.assertTrue(all(v >= 0 for v in point))

    def test_infeasible_returns_none(self):
        lp = LinearProgramme([1], [([1], 5)], upper=[2])
        self.assertIsNone(lp.solve())

    def test_strong_duality_on_random_instances(self):
        """The independent check. The dual is a different LP with different
        data, and its optimum must equal the primal's."""
        rng = random.Random(0)
        checked = 0
        for _ in range(25):
            n, m = rng.choice([2, 3]), rng.choice([2, 3])
            cost = [rng.randint(1, 9) for _ in range(n)]
            A = [[rng.randint(0, 4) for _ in range(n)] for _ in range(m)]
            b = [rng.randint(1, 10) for _ in range(m)]
            if any(all(a == 0 for a in row) for row in A):
                continue
            primal = LinearProgramme(cost, list(zip(A, b))).solve()
            transposed = [[A[i][j] for i in range(m)] for j in range(n)]
            dual = LinearProgramme([-x for x in b],
                                   [([-a for a in row], -cost[j])
                                    for j, row in enumerate(transposed)]).solve()
            if primal is None or dual is None:
                continue
            checked += 1
            with self.subTest(cost=cost):
                self.assertEqual(primal[1], -dual[1])
        self.assertGreater(checked, 12)


class TestBranchAndBound(unittest.TestCase):
    def test_it_agrees_with_brute_force_on_the_sizing_problem(self):
        self.assertEqual(_BB.cost, _BF.cost)
        self.assertEqual(_BB.x, _BF.x)

    def test_it_agrees_with_brute_force_on_random_instances(self):
        rng = random.Random(1)
        for trial in range(12):
            n = rng.choice([2, 3])
            cost = [rng.randint(1, 9) for _ in range(n)]
            constraints = [([rng.randint(0, 4) for _ in range(n)],
                            rng.randint(1, 8))
                           for _ in range(rng.choice([1, 2]))]
            if any(all(a == 0 for a in row) for row, _ in constraints):
                continue
            upper = [4] * n
            with self.subTest(trial=trial):
                self.assertEqual(branch_and_bound(cost, constraints, upper).cost,
                                 brute_force(cost, constraints, upper).cost)

    def test_the_answer_is_integral_and_feasible(self):
        cost, constraints, upper = _SIZING[0], _SIZING[1], _SIZING[2]
        result = _BB
        self.assertTrue(all(isinstance(v, int) for v in result.x))
        for row, rhs in constraints:
            self.assertGreaterEqual(sum(a * x for a, x in zip(row, result.x)), rhs)

    def test_the_lp_bound_never_exceeds_the_integer_optimum(self):
        """Relaxing constraints can only lower the cost. If this ever failed,
        the bound would be unusable and branch and bound unsound."""
        self.assertLessEqual(_BB.lp_bound, _BB.cost)

    def test_the_bound_prunes_most_of_the_search(self):
        self.assertGreater(_BF.nodes / _BB.nodes, 100)
        self.assertGreater(_BB.pruned_by_bound, 0)

    def test_infeasible_problems_return_no_solution(self):
        self.assertIsNone(branch_and_bound([1], [([1], 99)], [2]).x)


class TestRoundingUpIsNotOptimal(unittest.TestCase):
    def test_rounding_the_relaxation_costs_real_money(self):
        rounded = round_up_relaxation(*_SIZING[:3])
        self.assertGreater(rounded.cost, _BB.cost)

    def test_rounding_up_stays_feasible(self):
        """For a covering problem raising a variable can only help, so the
        rounded point is always feasible -- just not always good."""
        cost, constraints, upper, _ = instance_sizing()
        rounded = round_up_relaxation(cost, constraints, upper)
        for row, rhs in constraints:
            self.assertGreaterEqual(sum(a * x for a, x in zip(row, rounded.x)), rhs)


class TestTheGapFamily(unittest.TestCase):
    def test_closed_form_matches_the_solver(self):
        for n in (3, 4, 5):
            cost, constraints, upper, _ = complement_cover(n)
            bb = branch_and_bound(cost, constraints, upper)
            predicted_lp, predicted_ip = predicted_cover_gap(n)
            with self.subTest(n=n):
                self.assertEqual(bb.lp_bound, predicted_lp)
                self.assertEqual(bb.cost, predicted_ip)

    def test_brute_force_confirms_the_integer_answer(self):
        for n in (3, 4, 5):
            cost, constraints, upper, _ = complement_cover(n)
            with self.subTest(n=n):
                self.assertEqual(brute_force(cost, constraints, upper).cost, 2)

    def test_the_gap_grows_with_n(self):
        gaps = []
        for n in (3, 4, 5):
            lp, ip = predicted_cover_gap(n)
            gaps.append(ip / lp)
        self.assertEqual(gaps, sorted(gaps))

    def test_the_gap_approaches_two_but_never_reaches_it(self):
        for n in (10, 1000, 10 ** 6):
            lp, ip = predicted_cover_gap(n)
            ratio = ip / lp
            with self.subTest(n=n):
                self.assertLess(ratio, 2)
        self.assertGreater(predicted_cover_gap(10 ** 6)[1]
                           / predicted_cover_gap(10 ** 6)[0], Fraction(199, 100))

    def test_one_set_is_never_enough(self):
        """The reason the integer answer is 2: every set misses an element."""
        for n in (3, 5, 8):
            cost, constraints, upper, _ = complement_cover(n)
            for single in range(n):
                point = [1 if i == single else 0 for i in range(n)]
                covered = all(sum(a * x for a, x in zip(row, point)) >= rhs
                              for row, rhs in constraints)
                with self.subTest(n=n, set=single):
                    self.assertFalse(covered)


class TestProblemData(unittest.TestCase):
    def test_the_demand_is_not_met_by_any_single_type(self):
        for _name, vcpu, ram, _price in INSTANCE_TYPES:
            self.assertTrue(vcpu < REQUIRED_VCPU or ram < REQUIRED_RAM)

    def test_the_box_is_large_enough_to_contain_a_solution(self):
        self.assertIsNotNone(_BF.cost)


if __name__ == "__main__":
    unittest.main()
