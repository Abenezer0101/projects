"""Tests. The claims the README makes are pinned, not just described."""

from __future__ import annotations

import math
import random
import statistics
import unittest

from peeking import DAYS, false_positive_rate
from sequential import calibrate, power_against
from stats import BinomialSampler, normal_cdf, two_sided_p, z_score

NAIVE_Z = 1.959963985


class TestNormal(unittest.TestCase):
    def test_cdf_at_zero(self):
        self.assertAlmostEqual(normal_cdf(0.0), 0.5)

    def test_cdf_is_symmetric(self):
        for z in (0.5, 1.0, 1.96, 3.0):
            self.assertAlmostEqual(normal_cdf(z) + normal_cdf(-z), 1.0)

    def test_the_textbook_critical_value(self):
        self.assertAlmostEqual(two_sided_p(NAIVE_Z), 0.05, places=6)

    def test_p_is_one_at_z_zero(self):
        self.assertAlmostEqual(two_sided_p(0.0), 1.0)

    def test_p_shrinks_as_z_grows(self):
        self.assertLess(two_sided_p(3.0), two_sided_p(2.0))


class TestZScore(unittest.TestCase):
    def test_identical_arms_give_zero(self):
        self.assertEqual(z_score(100, 1000, 100, 1000), 0.0)

    def test_sign_follows_the_better_arm(self):
        self.assertGreater(z_score(120, 1000, 100, 1000), 0)
        self.assertLess(z_score(100, 1000, 120, 1000), 0)

    def test_more_data_makes_the_same_gap_more_significant(self):
        small = abs(z_score(12, 100, 10, 100))
        large = abs(z_score(120, 1000, 100, 1000))
        self.assertGreater(large, small)

    def test_empty_arm_does_not_raise(self):
        self.assertEqual(z_score(0, 0, 5, 100), 0.0)

    def test_zero_conversions_everywhere_does_not_raise(self):
        """Day one of a low-rate test. A statistic that divides by zero here
        is a statistic nobody can run."""
        self.assertEqual(z_score(0, 500, 0, 500), 0.0)

    def test_total_conversion_does_not_raise(self):
        self.assertEqual(z_score(500, 500, 500, 500), 0.0)


class TestBinomialSampler(unittest.TestCase):
    def test_cdf_ends_at_one(self):
        self.assertEqual(BinomialSampler(50, 0.3).cdf[-1], 1.0)

    def test_cdf_is_non_decreasing(self):
        cdf = BinomialSampler(60, 0.25).cdf
        self.assertEqual(cdf, sorted(cdf))

    def test_mean_and_variance_match_theory(self):
        n, p = 1000, 0.1
        s = BinomialSampler(n, p)
        rng = random.Random(3)
        xs = [s.draw(rng) for _ in range(20_000)]
        self.assertAlmostEqual(statistics.mean(xs), n * p, delta=0.5)
        self.assertAlmostEqual(statistics.stdev(xs), math.sqrt(n * p * (1 - p)), delta=0.2)

    def test_draws_stay_in_range(self):
        s = BinomialSampler(20, 0.5)
        rng = random.Random(4)
        self.assertTrue(all(0 <= s.draw(rng) <= 20 for _ in range(2000)))

    def test_p_zero_always_draws_zero(self):
        s = BinomialSampler(10, 0.0)
        rng = random.Random(5)
        self.assertEqual({s.draw(rng) for _ in range(100)}, {0})

    def test_same_seed_same_draws(self):
        s = BinomialSampler(100, 0.2)
        a = [s.draw(random.Random(9)) for _ in range(1)]
        b = [s.draw(random.Random(9)) for _ in range(1)]
        self.assertEqual(a, b)


class TestPeekingClaims(unittest.TestCase):
    """The headline numbers. If these drift, the README is wrong."""

    def test_a_single_look_holds_the_nominal_rate(self):
        rate, _ = false_positive_rate([DAYS], trials=8000, seed=21)
        self.assertAlmostEqual(rate, 0.05, delta=0.012)

    def test_daily_peeking_roughly_quadruples_it(self):
        rate, _ = false_positive_rate(list(range(1, DAYS + 1)), trials=8000, seed=21)
        self.assertGreater(rate, 0.18)
        self.assertLess(rate, 0.27)

    def test_more_looks_means_more_false_positives(self):
        one, _ = false_positive_rate([DAYS], trials=6000, seed=22)
        two, _ = false_positive_rate([7, DAYS], trials=6000, seed=22)
        many, _ = false_positive_rate(list(range(1, DAYS + 1)), trials=6000, seed=22)
        self.assertLess(one, two)
        self.assertLess(two, many)

    def test_false_positives_report_a_large_lift_that_is_not_there(self):
        """The part that does the damage: the effect you stop on is inflated,
        because you stopped when noise was most flattering."""
        _, hits = false_positive_rate(list(range(1, DAYS + 1)), trials=6000, seed=23)
        mean_lift = sum(abs(h.observed_lift) for h in hits) / len(hits)
        self.assertGreater(mean_lift, 0.10)   # true lift is exactly 0

    def test_false_positives_stop_early(self):
        _, hits = false_positive_rate(list(range(1, DAYS + 1)), trials=6000, seed=23)
        mean_day = sum(h.stopped_on for h in hits) / len(hits)
        self.assertLess(mean_day, DAYS / 2)


class TestCalibration(unittest.TestCase):
    def test_one_look_recovers_the_analytic_threshold(self):
        """The calibration is told nothing about 1.96; if it reproduces it for
        a single look, the procedure is sound."""
        z = calibrate([DAYS], trials=8000, seed=31)
        self.assertAlmostEqual(z, NAIVE_Z, delta=0.08)

    def test_the_bar_rises_with_more_looks(self):
        one = calibrate([DAYS], trials=6000, seed=32)
        many = calibrate(list(range(1, DAYS + 1)), trials=6000, seed=32)
        self.assertGreater(many, one + 0.3)

    def test_the_calibrated_boundary_holds_on_unseen_seeds(self):
        daily = list(range(1, DAYS + 1))
        z = calibrate(daily, trials=12_000, seed=1)
        rate, _ = false_positive_rate(daily, trials=12_000, seed=12345, threshold_z=z)
        self.assertAlmostEqual(rate, 0.05, delta=0.015)

    def test_the_correction_costs_power(self):
        """A fix that cost nothing would be a fix that did nothing."""
        daily = list(range(1, DAYS + 1))
        z = calibrate(daily, trials=8000, seed=1)
        one_look = power_against(0.10, [DAYS], NAIVE_Z, trials=3000, seed=41)
        corrected = power_against(0.10, daily, z, trials=3000, seed=41)
        self.assertLess(corrected, one_look)
        self.assertGreater(corrected, 0.4)   # still a usable test


if __name__ == "__main__":
    unittest.main()
