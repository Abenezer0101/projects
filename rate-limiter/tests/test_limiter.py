"""Tests. The first class is the point: it fails on the naive limiter."""

from __future__ import annotations

import unittest

from audit import replay, worst_window
from limiter import FixedWindow, SlidingCounter, SlidingLog, TokenBucket, build

LIMIT = 100
WINDOW = 60.0


def boundary_attack(n: int = 200, spacing: float = 1e-4) -> list[float]:
    """n requests just before a window boundary, n just after."""
    return [600.0 - 1.0 + i * spacing for i in range(n)] + \
           [600.0 + i * spacing for i in range(n)]


class TestTheInvariant(unittest.TestCase):
    """'100 per 60 seconds' should mean no 60-second stretch anywhere holds 101.

    Written as one assertion applied to every limiter. Two of them fail it,
    and the tests below say so by name rather than lowering the bar.
    """

    def assert_holds(self, limiter, arrivals, tolerance: int = 0):
        admitted = replay(limiter, arrivals)
        worst, at = worst_window(admitted, WINDOW)
        self.assertLessEqual(
            worst,
            LIMIT + tolerance,
            f"{limiter.name} let {worst} through in the 60s from t={at:.3f}",
        )

    def test_sliding_log_holds_it_exactly(self):
        self.assert_holds(SlidingLog(LIMIT, WINDOW), boundary_attack())

    def test_fixed_window_violates_it(self):
        """The defect, pinned. This is why the project exists."""
        lim = FixedWindow(LIMIT, WINDOW, window_start=540.0)
        with self.assertRaises(AssertionError):
            self.assert_holds(lim, boundary_attack())

    def test_fixed_window_violates_it_by_exactly_double(self):
        lim = FixedWindow(LIMIT, WINDOW, window_start=540.0)
        worst, _ = worst_window(replay(lim, boundary_attack()), WINDOW)
        self.assertEqual(worst, 2 * LIMIT)

    def test_sliding_counter_leaks_one(self):
        """The weighted estimate decays continuously, so one request slips
        through microseconds after the boundary. One, not a hundred."""
        lim = SlidingCounter(LIMIT, WINDOW, window_start=540.0)
        worst, _ = worst_window(replay(lim, boundary_attack()), WINDOW)
        self.assertEqual(worst, LIMIT + 1)

    def test_token_bucket_permits_a_full_extra_window(self):
        """Not a bug: a bucket bounds the average, not the rolling maximum.
        Drain it, wait a window while it refills, drain it again."""
        arrivals = [0.0 + i * 1e-4 for i in range(200)] + \
                   [59.5 + i * 1e-4 for i in range(200)]
        lim = TokenBucket(LIMIT, WINDOW, last=0.0)
        worst, _ = worst_window(replay(lim, arrivals), WINDOW)
        self.assertGreater(worst, 1.9 * LIMIT)


class TestLongRunRate(unittest.TestCase):
    def test_all_four_converge_to_the_nominal_rate(self):
        minutes = 30
        total = LIMIT * 3 * minutes
        span = WINDOW * minutes
        arrivals = [i * span / total for i in range(total)]
        for lim in build(LIMIT, WINDOW, start=0.0):
            with self.subTest(lim.name):
                per_minute = len(replay(lim, arrivals)) / minutes
                # the bucket starts full, which is a one-off +LIMIT amortised
                self.assertAlmostEqual(per_minute, LIMIT, delta=LIMIT / minutes + 0.5)


class TestFixedWindow(unittest.TestCase):
    def test_admits_up_to_the_limit(self):
        lim = FixedWindow(3, 10.0)
        self.assertEqual([lim.allow(t) for t in (0, 1, 2, 3)], [True, True, True, False])

    def test_resets_on_the_boundary(self):
        lim = FixedWindow(2, 10.0)
        self.assertEqual([lim.allow(t) for t in (0, 1, 2)], [True, True, False])
        self.assertTrue(lim.allow(10.0))

    def test_does_not_reset_mid_window(self):
        lim = FixedWindow(1, 10.0)
        self.assertTrue(lim.allow(0.0))
        self.assertFalse(lim.allow(9.999))


class TestSlidingLog(unittest.TestCase):
    def test_expires_by_age_not_by_boundary(self):
        lim = SlidingLog(2, 10.0)
        self.assertTrue(lim.allow(0.0))
        self.assertTrue(lim.allow(5.0))
        self.assertFalse(lim.allow(9.0))
        self.assertTrue(lim.allow(10.1))   # the 0.0 entry aged out
        self.assertFalse(lim.allow(10.2))  # the 5.0 entry has not

    def test_log_never_grows_past_the_limit(self):
        lim = SlidingLog(5, 10.0)
        for i in range(500):
            lim.allow(i * 0.01)
        self.assertLessEqual(len(lim.log), 5)

    def test_an_exact_window_old_entry_is_expired(self):
        lim = SlidingLog(1, 10.0)
        self.assertTrue(lim.allow(0.0))
        self.assertTrue(lim.allow(10.0))


class TestSlidingCounter(unittest.TestCase):
    def test_weights_the_previous_window(self):
        lim = SlidingCounter(10, 10.0)
        for i in range(10):
            self.assertTrue(lim.allow(i * 0.1))
        self.assertFalse(lim.allow(5.0))
        # halfway into the next window the previous count counts for half
        self.assertTrue(lim.allow(15.0))

    def test_a_full_window_of_silence_clears_the_history(self):
        lim = SlidingCounter(1, 10.0)
        self.assertTrue(lim.allow(0.0))
        self.assertTrue(lim.allow(25.0))  # two windows later, nothing carried


class TestTokenBucket(unittest.TestCase):
    def test_starts_full(self):
        lim = TokenBucket(5, 10.0)
        self.assertEqual([lim.allow(0.0) for _ in range(6)],
                         [True] * 5 + [False])

    def test_refills_at_the_nominal_rate(self):
        lim = TokenBucket(10, 10.0)  # one token per second
        for _ in range(10):
            lim.allow(0.0)
        self.assertFalse(lim.allow(0.5))
        self.assertTrue(lim.allow(1.0))

    def test_never_refills_past_capacity(self):
        lim = TokenBucket(5, 10.0)
        lim.allow(0.0)
        lim.allow(10_000.0)  # an age of idleness
        self.assertLessEqual(lim.tokens, 5)

    def test_capacity_above_the_limit_is_an_explicit_burst(self):
        lim = TokenBucket(5, 10.0, capacity=20)
        self.assertEqual(sum(lim.allow(0.0) for _ in range(25)), 20)


class TestAudit(unittest.TestCase):
    def test_empty_trace(self):
        self.assertEqual(worst_window([], 60.0), (0, 0.0))

    def test_finds_the_dense_window_not_the_first_one(self):
        times = [0.0, 1.0, 100.0, 101.0, 102.0, 103.0]
        worst, at = worst_window(times, 10.0)
        self.assertEqual(worst, 4)
        self.assertEqual(at, 100.0)

    def test_window_is_half_open(self):
        self.assertEqual(worst_window([0.0, 10.0], 10.0)[0], 1)

    def test_unsorted_input_is_handled(self):
        self.assertEqual(worst_window([5.0, 0.0, 1.0], 10.0)[0], 3)


if __name__ == "__main__":
    unittest.main()
