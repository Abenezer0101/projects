"""Tests. The closed forms are checked against measurement; the README's
numbers and its trade-offs are pinned, including the awkward ones."""

from __future__ import annotations

import math
import statistics
import unittest

import masking
from detectability import (daily_rate, min_rate_for_threshold, per_hour_rates,
                           sigmas_for_outage)
from detectors import (DETECTORS, IQR, MAD_TO_SIGMA, ModifiedZScore,
                       SeasonalMAD, SeasonalPerPhase, SeasonalPoisson, ZScore,
                       mad)
from evaluate import by_kind, inject, score
from series import check_hourly, hourly_counts


class TestSeries(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stamps, cls.values = hourly_counts()

    def test_the_series_is_contiguous_hourly(self):
        check_hourly(self.stamps)
        self.assertEqual(len(self.stamps), len(self.values))

    def test_gaps_are_filled_with_explicit_zeros(self):
        """Absent hours must become zeros, not be closed up -- closing them
        would shift every later point against the 24-hour cycle."""
        self.assertGreater(self.values.count(0.0), 100)

    def test_contiguity_check_catches_a_gap(self):
        import datetime
        with self.assertRaises(ValueError):
            check_hourly([datetime.datetime(2026, 6, 1, 0),
                          datetime.datetime(2026, 6, 1, 2)])

    def test_the_daily_cycle_is_real(self):
        by_hour: dict[int, list[float]] = {}
        for s, v in zip(self.stamps, self.values):
            by_hour.setdefault(s.hour, []).append(v)
        means = {h: statistics.mean(v) for h, v in by_hour.items()}
        self.assertGreater(max(means.values()) / min(means.values()), 10)
        self.assertEqual(max(means, key=means.get), 8)   # the morning rush


class TestMaskingClosedForms(unittest.TestCase):
    def test_single_outlier_ceiling_sample_sd(self):
        for n in (5, 10, 20, 50, 100):
            with self.subTest(n=n):
                self.assertAlmostEqual(masking.achieved_max_z(n, ddof=1),
                                       masking.ceiling_sample_sd(n), places=6)

    def test_single_outlier_ceiling_population_sd(self):
        for n in (5, 10, 20, 50, 100):
            with self.subTest(n=n):
                self.assertAlmostEqual(masking.achieved_max_z(n, ddof=0),
                                       masking.ceiling_population_sd(n), places=6)

    def test_k_outlier_formula_matches_measurement(self):
        for n in (16, 40, 200):
            for k in (1, 2, 3, 5):
                with self.subTest(n=n, k=k):
                    data = [0.0] * (n - k) + [40.0] * k
                    z = abs(data[-1] - statistics.mean(data)) / statistics.stdev(data)
                    self.assertAlmostEqual(z, masking.z_for_k_outliers(n, k), places=9)

    def test_the_formula_is_independent_of_outlier_size(self):
        """The striking part: making the anomaly bigger does not help."""
        for size in (10.0, 1e3, 1e9):
            data = [0.0] * 14 + [size, size]
            z = abs(data[-1] - statistics.mean(data)) / statistics.stdev(data)
            self.assertAlmostEqual(z, masking.z_for_k_outliers(16, 2), places=6)

    def test_a_ten_point_window_cannot_flag_anything_at_three(self):
        self.assertLess(masking.ceiling_sample_sd(10), 3.0)
        self.assertGreater(masking.ceiling_sample_sd(11), 3.0)
        self.assertEqual(masking.min_n_for_threshold(3.0, ddof=1), 11)

    def test_the_masking_window_is_eleven_to_twenty(self):
        window = masking.masking_window(3.0)
        self.assertEqual((window[0], window[-1]), (11, 20))

    def test_two_outliers_mask_each_other_at_sixteen(self):
        m = masking.two_outlier_masking(n=16)
        self.assertGreaterEqual(m["z_with_one"], 3.0)
        self.assertLess(m["z_with_two"], 3.0)


class TestDetectors(unittest.TestCase):
    def test_mad_of_a_constant_series_is_zero(self):
        self.assertEqual(mad([5.0] * 10), 0.0)

    def test_mad_to_sigma_constant(self):
        self.assertAlmostEqual(MAD_TO_SIGMA, 1 / 0.6744897501960817, places=4)

    def test_every_detector_returns_indices_in_range(self):
        _, values = hourly_counts()
        for cls in DETECTORS:
            with self.subTest(cls.__name__):
                flagged = cls().flag(values)
                self.assertTrue(all(0 <= i < len(values) for i in flagged))

    def test_a_constant_series_has_no_anomalies(self):
        for cls in DETECTORS:
            with self.subTest(cls.__name__):
                self.assertEqual(cls().flag([7.0] * 240), set())

    def test_a_single_huge_spike_is_found_by_everyone(self):
        values = [5.0] * 240
        values[100] = 5000.0
        for cls in DETECTORS:
            with self.subTest(cls.__name__):
                self.assertIn(100, cls().flag(values))

    def test_short_input_does_not_raise(self):
        for cls in DETECTORS:
            with self.subTest(cls.__name__):
                cls().flag([1.0])
                cls().flag([])


class TestTheRushHourProblem(unittest.TestCase):
    """The headline: detectors blind to the cycle flag the cycle."""

    RUSH = (7, 8, 9, 16, 17, 18)

    @classmethod
    def setUpClass(cls):
        cls.stamps, cls.values = hourly_counts()

    def rush_share(self, cls) -> float:
        flagged = cls().flag(self.values)
        if not flagged:
            return 0.0
        rush = sum(1 for i in flagged if self.stamps[i].hour in self.RUSH)
        return rush / len(flagged)

    def test_cycle_blind_detectors_mostly_flag_rush_hours(self):
        for cls in (ZScore, ModifiedZScore, IQR):
            with self.subTest(cls.__name__):
                self.assertGreater(self.rush_share(cls), 0.8)

    def test_per_phase_scaling_removes_them_entirely(self):
        self.assertEqual(self.rush_share(SeasonalPerPhase), 0.0)

    def test_a_per_phase_centre_alone_is_not_enough(self):
        """Variance is seasonal too, so centring without rescaling leaves most
        of the problem -- and flags MORE points than the raw z-score."""
        self.assertGreater(self.rush_share(SeasonalMAD), 0.5)
        self.assertGreater(len(SeasonalMAD().flag(self.values)),
                           len(ZScore().flag(self.values)))


class TestEvaluation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stamps, clean = hourly_counts()
        cls.data = inject(clean, cls.stamps)

    def test_injection_is_the_advertised_size(self):
        self.assertEqual(len(self.data.truth), 36)
        self.assertEqual(len(self.data.values), len(self.stamps))

    def test_score_is_zero_for_a_detector_that_flags_nothing(self):
        s = score(set(), self.data.truth, len(self.data.values))
        self.assertEqual((s["precision"], s["recall"], s["f1"]), (0.0, 0.0, 0.0))

    def test_score_is_one_for_an_exact_detector(self):
        s = score(set(self.data.truth), self.data.truth, len(self.data.values))
        self.assertAlmostEqual(s["f1"], 1.0)

    def test_the_z_score_misses_every_contextual_anomaly(self):
        found = by_kind(ZScore().flag(self.data.values), self.data)
        self.assertEqual(found["contextual spike"][0], 0)
        self.assertEqual(found["dropout"][0], 0)
        self.assertEqual(found["global spike"][0], 12)

    def test_the_poisson_detector_has_the_best_f1(self):
        best, best_f1 = None, -1.0
        for cls in DETECTORS:
            s = score(cls().flag(self.data.values), self.data.truth,
                      len(self.data.values))
            if s["f1"] > best_f1:
                best, best_f1 = cls.name, s["f1"]
        self.assertEqual(best, SeasonalPoisson.name)

    def test_f1_ranks_the_z_score_second_despite_missing_two_thirds(self):
        """A caution about F1: perfect precision on the easy third beats
        broad coverage, so the metric prefers a detector that cannot see a
        dropout at all."""
        z = score(ZScore().flag(self.data.values), self.data.truth,
                  len(self.data.values))
        self.assertAlmostEqual(z["precision"], 1.0)
        self.assertLess(z["recall"], 0.4)
        for cls in (ModifiedZScore, IQR, SeasonalMAD, SeasonalPerPhase):
            other = score(cls().flag(self.data.values), self.data.truth,
                          len(self.data.values))
            with self.subTest(cls.__name__):
                self.assertLess(other["f1"], z["f1"])


class TestDetectability(unittest.TestCase):
    def test_outage_sigma_is_the_square_root_of_the_rate(self):
        for rate in (1.0, 4.0, 9.0, 100.0):
            self.assertAlmostEqual(sigmas_for_outage(rate), math.sqrt(rate))

    def test_threshold_requires_rate_above_its_square(self):
        self.assertEqual(min_rate_for_threshold(3.0), 9.0)
        self.assertAlmostEqual(sigmas_for_outage(min_rate_for_threshold(3.0)), 3.0)

    def test_only_one_hour_can_show_a_full_outage(self):
        rates = per_hour_rates()
        visible = [h for h, r in rates.items() if sigmas_for_outage(r) >= 3.0]
        self.assertEqual(visible, [8])

    def test_a_daily_window_makes_the_same_outage_obvious(self):
        self.assertGreater(sigmas_for_outage(daily_rate()), 9.0)

    def test_this_explains_the_dropout_recall(self):
        """The 3-of-12 dropout recall is the limit, not a tuning failure: the
        injected dropouts land on busy hours, and only one busy hour has a
        rate above 9."""
        stamps, clean = hourly_counts()
        data = inject(clean, stamps)
        found = by_kind(SeasonalPoisson().flag(data.values), data)
        self.assertLess(found["dropout"][0], 6)
        self.assertGreater(found["dropout"][0], 0)


if __name__ == "__main__":
    unittest.main()
