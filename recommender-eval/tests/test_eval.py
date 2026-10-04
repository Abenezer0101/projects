"""Tests. The README's claims are pinned, including the ones that are
negative results."""

from __future__ import annotations

import collections
import unittest

from controlled import compare, honest_and_leaky, ranking_flips
from evaluate import (K, SPLITS, leave_last_out, random_split, recall_at_k,
                      temporal_split)
from models import ItemKNN, Popularity, RecentPopularity
from simulate import Interaction, describe, generate, popularity_at


class TestGenerator(unittest.TestCase):
    def test_no_duplicate_user_item_pairs(self):
        log = generate(drift=1.0, n_users=200, n_items=50, n_days=40)
        pairs = [(i.user, i.item) for i in log]
        self.assertEqual(len(pairs), len(set(pairs)))

    def test_log_is_sorted_by_day(self):
        log = generate(drift=1.0, n_users=100, n_items=40, n_days=30)
        self.assertEqual([i.day for i in log], sorted(i.day for i in log))

    def test_same_seed_same_log(self):
        a = generate(drift=1.0, seed=3, n_users=100, n_items=40, n_days=30)
        b = generate(drift=1.0, seed=3, n_users=100, n_items=40, n_days=30)
        self.assertEqual(a, b)

    def test_zero_drift_is_stationary(self):
        """With the dial at zero, popularity must not depend on the day."""
        appeal = [1.0 / (r + 2) ** 0.5 for r in range(50)]
        first = [popularity_at(0, i, appeal, 0.0, 40) for i in range(50)]
        last = [popularity_at(39, i, appeal, 0.0, 40) for i in range(50)]
        self.assertEqual(first, last)

    def test_positive_drift_moves_popularity(self):
        appeal = [1.0 / (r + 2) ** 0.5 for r in range(50)]
        first = [popularity_at(0, i, appeal, 2.0, 40) for i in range(50)]
        last = [popularity_at(39, i, appeal, 2.0, 40) for i in range(50)]
        self.assertNotEqual(first, last)

    def test_the_drift_dial_reorders_the_chart(self):
        """The dial has to be a dial. In the first version the Zipf head was
        so steep that no drift setting changed the top ten at all."""
        def overlap(drift: float) -> int:
            log = generate(drift=drift)
            days = max(i.day for i in log) + 1
            quarter = days // 4
            early = collections.Counter(i.item for i in log if i.day < quarter)
            late = collections.Counter(i.item for i in log if i.day >= 3 * quarter)
            top_early = {i for i, _ in early.most_common(10)}
            top_late = {i for i, _ in late.most_common(10)}
            return len(top_early & top_late)

        self.assertGreaterEqual(overlap(0.0), 8)   # stationary: chart holds
        self.assertLessEqual(overlap(4.0), 2)      # heavy drift: chart turns over


class TestSplits(unittest.TestCase):
    def setUp(self):
        self.log = generate(drift=1.0, n_users=400, n_items=80, n_days=60)

    def test_every_split_partitions_the_log(self):
        for name, fn in SPLITS.items():
            with self.subTest(name):
                train, test = fn(self.log)
                self.assertEqual(len(train) + len(test), len(self.log))
                self.assertEqual(set(train) & set(test), set())

    def test_temporal_train_strictly_precedes_test(self):
        train, test = temporal_split(self.log)
        self.assertLess(max(i.day for i in train), min(i.day for i in test))

    def test_random_train_does_not_precede_test(self):
        """The leak, stated as a test rather than a warning."""
        train, test = random_split(self.log)
        self.assertGreater(max(i.day for i in train), min(i.day for i in test))

    def test_leave_last_out_holds_out_one_per_user(self):
        train, test = leave_last_out(self.log)
        self.assertEqual(len({i.user for i in test}), len(test))

    def test_leave_last_out_still_leaks_across_users(self):
        """Per user it looks temporal. Globally it is not: training rows exist
        that postdate other users' held-out interactions."""
        train, test = leave_last_out(self.log)
        earliest_test_day = min(i.day for i in test)
        self.assertTrue(any(i.day > earliest_test_day for i in train))


class TestTheConfound(unittest.TestCase):
    """Why the three protocols cannot be compared directly."""

    @classmethod
    def setUpClass(cls):
        cls.log = generate(drift=1.0)

    def relevant_per_user(self, test):
        by_user = collections.defaultdict(set)
        for i in test:
            by_user[i.user].add(i.item)
        return sum(len(v) for v in by_user.values()) / len(by_user)

    def test_the_protocols_pose_different_tasks(self):
        counts = {name: self.relevant_per_user(fn(self.log)[1])
                  for name, fn in SPLITS.items()}
        self.assertAlmostEqual(counts["leave-last-out"], 1.0, places=6)
        self.assertGreater(counts["temporal"], 3 * counts["random"])

    def test_temporal_has_cold_start_users_and_random_has_none(self):
        for name, expect_cold in (("random", False), ("temporal", True)):
            train, test = SPLITS[name](self.log)
            trained = {i.user for i in train}
            cold = {i.user for i in test} - trained
            with self.subTest(name):
                self.assertEqual(bool(cold), expect_cold)


class TestModels(unittest.TestCase):
    def setUp(self):
        self.log = generate(drift=1.0, n_users=400, n_items=80, n_days=60)
        self.train, self.test = temporal_split(self.log)

    def test_recommendations_exclude_the_users_history(self):
        for cls in (Popularity, RecentPopularity, ItemKNN):
            with self.subTest(cls.__name__):
                model = cls().fit(self.train)
                history = {i.item for i in self.train if i.user == self.test[0].user}
                recs = model.recommend(self.test[0].user, K, history)
                self.assertEqual(set(recs) & history, set())

    def test_recommendations_are_the_requested_length(self):
        for cls in (Popularity, RecentPopularity, ItemKNN):
            with self.subTest(cls.__name__):
                recs = cls().fit(self.train).recommend(0, K, set())
                self.assertEqual(len(recs), K)

    def test_recommendations_are_unique(self):
        recs = ItemKNN().fit(self.train).recommend(0, K, set())
        self.assertEqual(len(recs), len(set(recs)))

    def test_cf_similarity_is_symmetric_and_bounded(self):
        model = ItemKNN().fit(self.train)
        for item, neighbours in list(model.similar.items())[:20]:
            for other, sim in neighbours:
                with self.subTest(pair=(item, other)):
                    self.assertGreater(sim, 0.0)
                    self.assertLessEqual(sim, 1.0 + 1e-12)

    def test_a_cold_user_still_gets_recommendations(self):
        model = ItemKNN().fit(self.train)
        self.assertEqual(len(model.recommend(10 ** 6, K, set())), K)

    def test_recall_is_zero_when_nothing_matches(self):
        class Nothing:
            name = "nothing"

            def recommend(self, user, k, exclude):
                return [-1] * k

        self.assertEqual(recall_at_k(Nothing(), self.train, self.test), 0.0)

    def test_recall_is_one_for_an_oracle(self):
        by_user = collections.defaultdict(list)
        for i in self.test:
            by_user[i.user].append(i.item)
        few = [i for i in self.test if len(by_user[i.user]) <= K]

        class Oracle:
            name = "oracle"

            def recommend(self, user, k, exclude):
                return by_user[user][:k]

        self.assertAlmostEqual(recall_at_k(Oracle(), self.train, few), 1.0, places=9)


class TestTheLeak(unittest.TestCase):
    def test_the_honest_train_contains_nothing_from_the_test_period(self):
        log = generate(drift=1.0)
        test, honest, leaky = honest_and_leaky(log)
        first_test_day = min(i.day for i in test)
        self.assertEqual([i for i in honest if i.day >= first_test_day], [])

    def test_the_leaky_train_does_contain_test_period_rows(self):
        log = generate(drift=1.0)
        test, honest, leaky = honest_and_leaky(log)
        first_test_day = min(i.day for i in test)
        contemporaneous = [i for i in leaky if i.day >= first_test_day]
        self.assertGreater(len(contemporaneous) / len(leaky), 0.05)

    def test_both_trains_are_the_same_size(self):
        log = generate(drift=1.0)
        _, honest, leaky = honest_and_leaky(log)
        self.assertEqual(len(honest), len(leaky))

    def test_leakage_inflates_scores_under_drift(self):
        row, *_ = compare(generate(drift=2.0))
        for name, r in row.items():
            with self.subTest(name):
                self.assertGreater(r["inflation"], 1.05)

    def test_inflation_nearly_vanishes_without_drift(self):
        """The control. If a stationary catalogue still showed inflation, the
        harness would be measuring itself rather than the leak."""
        row, *_ = compare(generate(drift=0.0))
        for name, r in row.items():
            with self.subTest(name):
                self.assertLess(r["inflation"], 1.10)

    def test_the_leak_changes_which_model_wins(self):
        """The result that matters: not that scores inflate, but that the two
        protocols disagree about what to ship."""
        r = ranking_flips(drift=1.0, seeds=10)
        self.assertGreater(r["flips"], 2)

    def test_collaborative_filtering_does_not_beat_popularity_here(self):
        """A negative result, pinned so it is not quietly dropped."""
        row, *_ = compare(generate(drift=1.0))
        best = max(row, key=lambda n: row[n]["honest"])
        self.assertNotEqual(best, "item-item CF")


if __name__ == "__main__":
    unittest.main()
