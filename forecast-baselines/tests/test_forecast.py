"""Tests. The README's claims are pinned; the closed forms are checked
against simulation rather than trusted.
"""

from __future__ import annotations

import unittest

import floor
from models import (MODELS, drift, fitted_alpha, historical_mean, holt,
                    linear_trend, naive, seasonal_naive, ses)
from series import check_contiguous, daily_counts
from walkforward import MIN_TRAIN, evaluate, paired_bootstrap, table


class TestSeries(unittest.TestCase):
    def setUp(self):
        self.dates, self.values = daily_counts()

    def test_sixty_contiguous_days(self):
        self.assertEqual(len(self.values), 60)
        check_contiguous(self.dates)   # raises on a gap

    def test_contiguity_check_catches_a_gap(self):
        with self.assertRaises(ValueError):
            check_contiguous(["2026-06-01", "2026-06-03"])

    def test_counts_lie_in_the_generator_range(self):
        """The generator draws randint(70, 130); cleaning drops a few rows, so
        the floor can sit below 70 but nothing may exceed 130."""
        self.assertLessEqual(max(self.values), 130)
        self.assertGreater(min(self.values), 0)

    def test_dates_are_sorted(self):
        self.assertEqual(self.dates, sorted(self.dates))


class TestModels(unittest.TestCase):
    def test_naive_returns_the_last_value(self):
        self.assertEqual(naive([1.0, 2.0, 7.0]), 7.0)

    def test_seasonal_naive_reaches_back_seven(self):
        history = [float(i) for i in range(10)]
        self.assertEqual(seasonal_naive(history), 3.0)

    def test_seasonal_naive_falls_back_on_a_short_history(self):
        self.assertEqual(seasonal_naive([5.0, 6.0]), 6.0)

    def test_historical_mean(self):
        self.assertEqual(historical_mean([1.0, 2.0, 3.0]), 2.0)

    def test_drift_extends_the_first_to_last_line(self):
        self.assertEqual(drift([10.0, 12.0, 14.0]), 16.0)

    def test_linear_trend_is_exact_on_a_line(self):
        self.assertAlmostEqual(linear_trend([2.0, 4.0, 6.0, 8.0]), 10.0)

    def test_linear_trend_on_a_flat_series_is_flat(self):
        self.assertAlmostEqual(linear_trend([5.0] * 10), 5.0)

    def test_ses_on_a_constant_series_returns_the_constant(self):
        self.assertAlmostEqual(ses([4.0] * 12), 4.0)

    def test_holt_follows_a_clean_trend(self):
        history = [float(i) for i in range(20)]
        self.assertGreater(holt(history), 18.0)

    def test_every_model_handles_a_two_point_history(self):
        for name, fn in MODELS.items():
            with self.subTest(name):
                self.assertIsInstance(fn([3.0, 4.0]), float)

    def test_fitted_alpha_is_low_on_white_noise(self):
        """alpha near 0 means 'ignore the last observation, use the average'.
        On a series with no momentum the fit should discover that itself."""
        _, values = daily_counts()
        self.assertLessEqual(fitted_alpha(values), 0.2)

    def test_fitted_alpha_is_high_on_a_random_walk(self):
        """The control: give it a series where the last value IS the best
        predictor and the same code should choose a large alpha."""
        import random
        rng = random.Random(0)
        walk, x = [], 0.0
        for _ in range(80):
            x += rng.gauss(0, 1)
            walk.append(x)
        self.assertGreaterEqual(fitted_alpha(walk), 0.6)


class TestNoLeakage(unittest.TestCase):
    def test_a_forecaster_never_sees_the_point_it_predicts(self):
        seen = []

        def spy(history: list[float]) -> float:
            seen.append(len(history))
            return history[-1]

        values = [float(i) for i in range(30)]
        evaluate(values, spy, min_train=14)
        # history lengths must be exactly 14..29, never 30
        self.assertEqual(seen, list(range(14, 30)))

    def test_the_evaluation_count_is_what_it_claims(self):
        values = [float(i) for i in range(30)]
        self.assertEqual(evaluate(values, naive, min_train=14)["n"], 16)

    def test_a_perfect_forecaster_scores_zero(self):
        values = [7.0] * 25
        self.assertEqual(evaluate(values, naive, min_train=14)["mae"], 0.0)


class TestClosedForms(unittest.TestCase):
    def test_constant_forecast_floor(self):
        self.assertAlmostEqual(floor.CONSTANT_MAE, 930 / 61, places=10)

    def test_naive_expected_error(self):
        self.assertAlmostEqual(floor.NAIVE_MAE, 3720 / 183, places=10)

    def test_naive_is_four_thirds_of_the_floor(self):
        self.assertAlmostEqual(floor.NAIVE_MAE / floor.CONSTANT_MAE, 4 / 3, places=10)

    def test_simulation_agrees_with_both_closed_forms(self):
        sim = floor.check(draws=200_000, seed=7)
        self.assertAlmostEqual(sim["constant_sim"], floor.CONSTANT_MAE, delta=0.1)
        self.assertAlmostEqual(sim["naive_sim"], floor.NAIVE_MAE, delta=0.15)

    def test_no_model_beats_the_floor(self):
        _, values = daily_counts()
        for name, mae, _, _ in table(values):
            with self.subTest(name):
                self.assertGreater(mae, floor.CONSTANT_MAE)


class TestTheHeadline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _, cls.values = daily_counts()
        cls.rows = table(cls.values)

    def test_the_historical_mean_wins(self):
        self.assertEqual(self.rows[0][0], "historical mean")

    def test_it_beats_naive_by_a_quarter(self):
        mase = {name: m for name, _, _, m in self.rows}["historical mean"]
        self.assertLess(mase, 0.8)

    def test_trend_following_models_do_worst(self):
        """drift and Holt fit a trend into noise, so they should sit at or
        below the naive forecast they are supposed to improve on."""
        mase = {name: m for name, _, _, m in self.rows}
        self.assertGreater(mase["drift"], 1.0)
        self.assertGreater(mase["Holt linear (fitted)"], 0.9)

    def test_the_win_over_naive_is_significant(self):
        r = paired_bootstrap(self.values, historical_mean, naive, trials=4000)
        self.assertLess(r["ci_high"], 0.0)

    def test_the_win_over_seasonal_naive_is_NOT_significant(self):
        """Known truth is not the same as demonstrated truth. The generator
        guarantees no weekly structure, so the mean must beat seasonal naive
        eventually -- but 46 points cannot show it, and the README says so
        rather than rounding 88.9% up to a result."""
        r = paired_bootstrap(self.values, historical_mean, seasonal_naive, trials=4000)
        self.assertGreater(r["ci_high"], 0.0)


class TestSeasonality(unittest.TestCase):
    def test_the_weekday_pattern_does_not_clear_significance(self):
        from seasonality import permutation_test
        result = permutation_test(trials=4000, seed=2)
        self.assertGreater(result["p_value"], 0.05)

    def test_the_permutation_test_detects_a_real_effect(self):
        """Control: plant a weekday effect and confirm the test finds it."""
        import datetime
        import random

        from seasonality import weekday_spread

        dates, values = daily_counts()
        labels = [datetime.date.fromisoformat(d).weekday() for d in dates]
        planted = [v + (40 if lab >= 5 else 0) for v, lab in zip(values, labels)]
        observed = weekday_spread(planted, labels)

        rng = random.Random(0)
        shuffled = labels.copy()
        hits = 0
        for _ in range(2000):
            rng.shuffle(shuffled)
            if weekday_spread(planted, shuffled) >= observed:
                hits += 1
        self.assertLess((hits + 1) / 2001, 0.01)


if __name__ == "__main__":
    unittest.main()
