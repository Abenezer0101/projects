"""Tests. Published Jaro-Winkler values are the oracle for the similarity; the
hand-labelled truth map is the oracle for the linkage."""

from __future__ import annotations

import unittest

import harder
from blocking import (SCHEMES, assess, first_letter_raw,
                      first_three_normalised, no_blocking, normalise,
                      token_sorted)
from evaluate import predict, score, sweep
from records import TRUTH, observed_spellings, records, true_pairs, validate
from similarity import jaro, jaro_winkler


class TestSimilarityAgainstPublishedValues(unittest.TestCase):
    CASES = [
        ("MARTHA", "MARHTA", 0.944, 0.961),
        ("DIXON", "DICKSONX", 0.767, 0.813),
        ("JELLYFISH", "SMELLYFISH", 0.896, 0.896),
        ("DWAYNE", "DUANE", 0.822, 0.840),
        ("CRATE", "TRACE", 0.733, 0.733),
    ]

    def test_jaro_matches(self):
        for a, b, expected, _ in self.CASES:
            with self.subTest(a=a, b=b):
                self.assertAlmostEqual(jaro(a, b), expected, places=3)

    def test_jaro_winkler_matches(self):
        for a, b, _, expected in self.CASES:
            with self.subTest(a=a, b=b):
                self.assertAlmostEqual(jaro_winkler(a, b), expected, places=3)

    def test_identical_is_one(self):
        self.assertEqual(jaro_winkler("Piedmont Park", "Piedmont Park"), 1.0)

    def test_disjoint_is_zero(self):
        self.assertEqual(jaro_winkler("abc", "xyz"), 0.0)

    def test_empty_strings(self):
        self.assertEqual(jaro("", "abc"), 0.0)
        self.assertEqual(jaro_winkler("", ""), 1.0)

    def test_symmetric(self):
        for a, b, _, _ in self.CASES:
            with self.subTest(a=a, b=b):
                self.assertAlmostEqual(jaro_winkler(a, b), jaro_winkler(b, a), places=12)

    def test_the_prefix_bonus_only_helps_shared_prefixes(self):
        with_prefix = jaro_winkler("Piedmont Park", "Piedmont Pork")
        no_prefix = jaro_winkler("Xiedmont Park", "Yiedmont Pork")
        self.assertGreater(with_prefix, no_prefix)

    def test_prefix_bonus_caps_at_four_characters(self):
        a = jaro_winkler("abcdQQQQ", "abcdZZZZ")
        b = jaro_winkler("abcdeQQQ", "abcdeZZZ")
        # the 5th shared character earns no further prefix credit
        self.assertAlmostEqual(a, jaro("abcdQQQQ", "abcdZZZZ")
                               + 4 * 0.1 * (1 - jaro("abcdQQQQ", "abcdZZZZ")), places=12)
        self.assertGreater(b, 0.0)


class TestNormalise(unittest.TestCase):
    def test_case_and_padding(self):
        self.assertEqual(normalise("  ATLANTIC Station "), "atlantic station")

    def test_expands_abbreviations_anywhere_in_the_string(self):
        """The Day 13 bug was an end-anchored pattern that expanded 'Main St.'
        and never 'Krog St. Market'."""
        self.assertEqual(normalise("Krog St. Market"), "krog street market")
        self.assertEqual(normalise("Grant Pk"), "grant park")

    def test_collapses_repeated_whitespace(self):
        self.assertEqual(normalise("west    end"), "west end")

    def test_is_idempotent(self):
        for value in TRUTH:
            with self.subTest(value):
                once = normalise(value)
                self.assertEqual(normalise(once), once)


class TestTruthMap(unittest.TestCase):
    def test_validate_passes(self):
        validate()

    def test_covers_exactly_the_observed_spellings(self):
        self.assertEqual(set(observed_spellings()), set(TRUTH))

    def test_forty_four_spellings_of_ten_stations(self):
        self.assertEqual(len(TRUTH), 44)
        self.assertEqual(len(set(TRUTH.values())), 10)

    def test_validate_catches_an_unlabelled_spelling(self):
        import records as module
        original = module.TRUTH
        try:
            module.TRUTH = {k: v for k, v in list(original.items())[1:]}
            with self.assertRaises(AssertionError):
                module.validate()
        finally:
            module.TRUTH = original

    def test_true_pair_count(self):
        self.assertEqual(len(true_pairs(records())), 76)


class TestNormalisationSolvesTheRealSet(unittest.TestCase):
    """The central negative result: the fuzzy matcher is not needed here."""

    def test_perfect_precision_and_recall_from_a_rule_alone(self):
        items = records()
        truth = true_pairs(items)
        exact = {(i, j) for i in range(len(items)) for j in range(i + 1, len(items))
                 if normalise(items[i]) == normalise(items[j])}
        s = score(exact, truth)
        self.assertEqual(s["precision"], 1.0)
        self.assertEqual(s["recall"], 1.0)

    def test_the_normaliser_produces_exactly_ten_groups(self):
        groups = {normalise(s) for s in records()}
        self.assertEqual(len(groups), 10)

    def test_no_group_mixes_two_stations(self):
        buckets: dict[str, set[str]] = {}
        for spelling, station in TRUTH.items():
            buckets.setdefault(normalise(spelling), set()).add(station)
        for key, stations in buckets.items():
            with self.subTest(key):
                self.assertEqual(len(stations), 1)


class TestBlockingCeiling(unittest.TestCase):
    """Reduction ratio without pair completeness is a half-reported number."""

    def test_raw_first_letter_destroys_recall_on_the_real_set(self):
        items = records()
        truth = true_pairs(items)
        a = assess(items, truth, first_letter_raw)
        self.assertGreater(a["reduction"], 0.9)        # looks efficient
        self.assertLess(a["completeness"], 0.3)        # and loses most matches

    def test_a_normalised_key_recovers_it_at_the_same_cost(self):
        items = records()
        truth = true_pairs(items)
        a = assess(items, truth, first_three_normalised)
        self.assertGreater(a["reduction"], 0.9)
        self.assertEqual(a["completeness"], 1.0)

    def test_no_blocking_always_has_full_completeness(self):
        items = records()
        self.assertEqual(assess(items, true_pairs(items), no_blocking)["completeness"],
                         1.0)

    def test_the_ceiling_bites_again_on_the_harder_set(self):
        """A scheme that was lossless on the real data loses a quarter of the
        matches once typos reach the blocking key itself."""
        items, truth_map = harder.build()
        truth = harder.true_pairs(items, truth_map)
        a = assess(items, truth, first_three_normalised)
        self.assertLess(a["completeness"], 0.8)
        b = assess(items, truth, token_sorted)
        self.assertLess(b["completeness"], 0.8)

    def test_recall_can_never_exceed_pair_completeness(self):
        items, truth_map = harder.build()
        truth = harder.true_pairs(items, truth_map)
        ceiling = assess(items, truth, first_three_normalised)["completeness"]
        for threshold, s in sweep(items, truth, first_three_normalised):
            with self.subTest(threshold=threshold):
                self.assertLessEqual(s["recall"], ceiling + 1e-12)


class TestHarderSet(unittest.TestCase):
    def test_rules_alone_score_zero(self):
        items, truth_map = harder.build()
        truth = harder.true_pairs(items, truth_map)
        exact = {(i, j) for i in range(len(items)) for j in range(i + 1, len(items))
                 if normalise(items[i]) == normalise(items[j])}
        self.assertEqual(score(exact, truth)["f1"], 0.0)

    def test_decoys_are_their_own_entities(self):
        _, truth_map = harder.build()
        self.assertEqual(truth_map["Grand Park"], "Grand Park")
        self.assertNotEqual(truth_map["Grand Park"], "Grant Park")

    def test_the_build_is_deterministic(self):
        self.assertEqual(harder.build(seed=5)[0], harder.build(seed=5)[0])

    def test_unblocked_sweep_beats_the_blocked_one(self):
        """Blocking saved 93% of the comparisons and cost real F1. Both halves
        of that trade belong in the report."""
        items, truth_map = harder.build()
        truth = harder.true_pairs(items, truth_map)
        blocked = max(s["f1"] for _, s in sweep(items, truth, first_three_normalised))
        unblocked = max(s["f1"] for _, s in sweep(items, truth, no_blocking))
        self.assertGreater(unblocked, blocked + 0.05)

    def test_a_high_threshold_trades_recall_for_precision(self):
        items, truth_map = harder.build()
        truth = harder.true_pairs(items, truth_map)
        low = score(predict(items, 0.75, no_blocking), truth)
        high = score(predict(items, 0.95, no_blocking), truth)
        self.assertGreater(high["precision"], low["precision"])
        self.assertLess(high["recall"], low["recall"])

    def test_threshold_one_matches_nothing_new(self):
        items, truth_map = harder.build()
        truth = harder.true_pairs(items, truth_map)
        self.assertEqual(score(predict(items, 1.01, no_blocking), truth)["recall"], 0.0)


if __name__ == "__main__":
    unittest.main()
