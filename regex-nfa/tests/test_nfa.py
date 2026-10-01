"""Tests. `re` is the oracle wherever the two engines are supposed to agree."""

from __future__ import annotations

import re
import unittest

from difftest import run as diffrun
from nfa import CharClass, Regex, fullmatch, tokenize, to_postfix


class TestAgainstRe(unittest.TestCase):
    """Hand-picked cases, each asserted against `re` rather than a literal."""

    CASES = [
        ("", ""), ("", "a"),
        ("a", "a"), ("a", "b"), ("a", "aa"),
        ("a*", ""), ("a*", "aaaa"), ("a*", "aab"),
        ("a+", ""), ("a+", "aaa"),
        ("a?", ""), ("a?", "a"), ("a?", "aa"),
        ("a|b", "a"), ("a|b", "b"), ("a|b", "c"),
        ("(a|b)+c", "abbac"), ("(a|b)+c", "c"),
        ("(ab)*", "ababab"), ("(ab)*", "aba"),
        ("a.c", "axc"), ("a.c", "ac"),
        ("[abc]+", "cabba"), ("[abc]+", "cabd"),
        ("[^x]+", "abc"), ("[^x]+", "abx"),
        ("[a-f]+", "faced"), ("[a-f]+", "zed"),
        ("[]]", "]"), ("[a-]", "-"), ("[-a]", "-"),
        ("a|", ""), ("()", ""), ("(|a)b", "b"),
        ("(a*)*", "aaa"), ("((a|b)*c)+", "abcbbc"),
        (r"a\.c", "a.c"), (r"a\.c", "axc"),
        (r"\(", "("), (r"[\]]", "]"),
        ("x(y|z)*w", "xyzyzw"), ("x(y|z)*w", "xyq w"),
    ]

    def test_every_case_agrees_with_re(self):
        for pattern, text in self.CASES:
            with self.subTest(pattern=pattern, text=text):
                self.assertEqual(
                    fullmatch(pattern, text),
                    re.fullmatch(pattern, text) is not None,
                )


class TestCharClass(unittest.TestCase):
    def test_literal(self):
        self.assertTrue(CharClass(frozenset("a")).matches("a"))
        self.assertFalse(CharClass(frozenset("a")).matches("b"))

    def test_any_char_matches_anything(self):
        self.assertTrue(CharClass(any_char=True).matches("\n"))

    def test_negation(self):
        cls = CharClass(frozenset("abc"), negated=True)
        self.assertFalse(cls.matches("b"))
        self.assertTrue(cls.matches("z"))

    def test_range_expands(self):
        self.assertTrue(fullmatch("[a-e]", "c"))
        self.assertFalse(fullmatch("[a-e]", "f"))

    def test_dash_at_either_end_is_a_literal(self):
        self.assertTrue(fullmatch("[-a]", "-"))
        self.assertTrue(fullmatch("[a-]", "-"))

    def test_closing_bracket_first_is_a_literal(self):
        self.assertTrue(fullmatch("[]]", "]"))


class TestParsing(unittest.TestCase):
    def test_concatenation_is_made_explicit(self):
        self.assertEqual(len(tokenize("ab")), 3)  # a, CONCAT, b

    def test_no_concat_inserted_after_an_alternation_bar(self):
        self.assertEqual(len(tokenize("a|b")), 3)

    def test_postfix_respects_precedence(self):
        # a|bc parses as a | (bc), so the bar is applied last
        postfix = to_postfix(tokenize("a|bc"))
        self.assertEqual(postfix[-1], "|")

    def test_unbalanced_paren_is_rejected(self):
        for bad in ["(a", "a)", "((a)"]:
            with self.subTest(bad), self.assertRaises(ValueError):
                Regex(bad)

    def test_unterminated_class_is_rejected(self):
        with self.assertRaises(ValueError):
            Regex("[abc")

    def test_trailing_backslash_is_rejected(self):
        with self.assertRaises(ValueError):
            Regex("a\\")

    def test_stacked_quantifier_is_refused_by_name(self):
        """Lazy and possessive quantifiers mean something this engine cannot
        express, so they are rejected rather than silently reinterpreted."""
        for bad in ["a+?", "a*+", "a??", "a*?"]:
            with self.subTest(bad), self.assertRaises(ValueError) as e:
                Regex(bad)
            self.assertIn("possessive", str(e.exception))


class TestPossessiveIsNotRegular(unittest.TestCase):
    def test_re_rejects_a_string_the_language_contains(self):
        """Justifies the refusal above: 'aa' is in the language a*a, and `re`
        still will not match it possessively. That is a property of
        backtracking, not of the regular language."""
        self.assertIsNone(re.fullmatch("a*+a", "aa"))
        self.assertTrue(fullmatch("a*a", "aa"))

    def test_lazy_does_not_change_the_language(self):
        """And justifies calling lazy harmless: same strings, different spans."""
        for text in ["", "a", "aa", "aaa"]:
            with self.subTest(text):
                self.assertEqual(
                    re.fullmatch("a*?a", text) is not None,
                    fullmatch("a*a", text),
                )


class TestNoBacktracking(unittest.TestCase):
    def test_the_pathological_pattern_is_fast(self):
        n = 26
        pattern, text = "a?" * n + "a" * n, "a" * n
        import time

        t0 = time.perf_counter()
        self.assertTrue(fullmatch(pattern, text))
        # `re` takes seconds on this; a tenth of a second is a generous ceiling
        self.assertLess(time.perf_counter() - t0, 0.1)

    def test_a_star_loop_terminates(self):
        """(a*)* can loop through epsilon transitions forever without the
        visited-set guard in _add."""
        self.assertTrue(fullmatch("(a*)*", "aaa"))
        self.assertTrue(fullmatch("(a*)*", ""))


class TestDifferential(unittest.TestCase):
    def test_a_short_generated_run_finds_nothing(self):
        checked, _, failures = diffrun(trials=2000, seed=7)
        self.assertGreater(checked, 5000)
        self.assertEqual(failures, [])


if __name__ == "__main__":
    unittest.main()
