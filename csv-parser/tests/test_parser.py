"""Tests. `csv.reader` is the oracle everywhere except the one documented
divergence, which has its own test saying why.
"""

from __future__ import annotations

import csv
import io
import unittest

from difftest import run as diffrun
from parser import BOM, naive, parse


def ref(text: str) -> list[list[str]]:
    return list(csv.reader(io.StringIO(text, newline="")))


class TestAgainstCsvModule(unittest.TestCase):
    CASES = [
        "", "\n", "\n\n", "a", "a\n", "a,b", "a,b\n",
        "a,b,c\n1,2,3\n",
        'a,"b,c",d\n',                 # comma inside quotes
        'a,"line1\nline2",c\n',        # newline inside quotes
        'a,"line1\r\nline2",c\n',      # CRLF inside quotes
        'a,"say ""hi""",c\n',          # escaped quotes
        '"""",x\n',                    # a field that is just one quote
        "a,b\r\nc,d\r\n",              # CRLF rows
        "a,b\rc,d\r",                  # lone CR rows
        "a,b\nc,d\r\ne,f\n",           # mixed endings in one file
        "a,b\n\nc,d\n",                # blank line in the middle
        ",\n", ",,\n", '"",""\n',
        'a"b,c\n',                     # quote inside an unquoted field
        '"ab"c,d\n',                    # text after a closing quote
        '"unterminated,x\n',           # quote never closed
        '"a""\n',                      # ends mid-escape
        "a,b,c",                       # no trailing newline
        " a , b \n",                   # spaces are data, not trimmed
        '" a ",b\n',
        "é,ß\n",                       # bytes are not the unit; characters are
    ]

    def test_every_case_matches(self):
        for text in self.CASES:
            with self.subTest(text=text):
                self.assertEqual(parse(text, strip_bom=False), ref(text))


class TestTheDivergence(unittest.TestCase):
    """The one place this parser deliberately differs, and the reason."""

    def test_bom_is_stripped_here_and_not_by_csv(self):
        text = BOM + "id,name\n1,a\n"
        self.assertEqual(parse(text)[0], ["id", "name"])
        # the csv module leaves it attached to the first header
        self.assertEqual(ref(text)[0][0], BOM + "id")

    def test_the_bom_bug_it_prevents(self):
        """Why it matters: with the BOM attached, the obvious lookup fails."""
        header = ref(BOM + "id,name\n")[0]
        self.assertNotIn("id", header)   # the column is there, under a name
        self.assertIn("id", parse(BOM + "id,name\n")[0])

    def test_opting_out_reproduces_csv_behaviour(self):
        text = BOM + "id\n"
        self.assertEqual(parse(text, strip_bom=False), ref(text))

    def test_a_bom_elsewhere_is_left_alone(self):
        text = "a," + BOM + "b\n"
        self.assertEqual(parse(text), [["a", BOM + "b"]])


class TestBlankLines(unittest.TestCase):
    def test_a_blank_line_has_no_fields(self):
        self.assertEqual(parse("\n"), [[]])

    def test_a_single_empty_quoted_field_has_one(self):
        self.assertEqual(parse('""\n'), [[""]])

    def test_the_distinction_matters_for_skipping(self):
        rows = parse("a,b\n\nc,d\n")
        self.assertEqual([r for r in rows if r], [["a", "b"], ["c", "d"]])


class TestEmbedded(unittest.TestCase):
    def test_newline_inside_quotes_does_not_end_the_row(self):
        self.assertEqual(parse('a,"x\ny",b\n'), [["a", "x\ny", "b"]])

    def test_crlf_inside_quotes_is_preserved_verbatim(self):
        self.assertEqual(parse('"x\r\ny"\n'), [["x\r\ny"]])

    def test_comma_inside_quotes_is_not_a_delimiter(self):
        self.assertEqual(parse('"a,b,c"\n'), [["a,b,c"]])

    def test_doubled_quote_becomes_one(self):
        self.assertEqual(parse('"a""b"\n'), [['a"b']])

    def test_a_field_of_only_escaped_quotes(self):
        self.assertEqual(parse('""""""\n'), [['""']])

    def test_delimiter_is_configurable(self):
        self.assertEqual(parse("a\tb\n", delimiter="\t"), [["a", "b"]])

    def test_no_trailing_empty_row_after_a_final_newline(self):
        self.assertEqual(len(parse("a\nb\n")), 2)

    def test_a_file_without_a_final_newline_keeps_its_last_row(self):
        self.assertEqual(parse("a\nb"), [["a"], ["b"]])


class TestNaiveBaseline(unittest.TestCase):
    """The baseline is only interesting if it is honestly implemented."""

    def test_it_is_right_on_trivial_input(self):
        text = "a,b\n1,2\n"
        self.assertEqual(naive(text), ref(text))

    def test_it_invents_a_column_on_a_quoted_comma(self):
        self.assertEqual(len(naive('a,"b,c"\n')[0]), 3)
        self.assertEqual(len(parse('a,"b,c"\n')[0]), 2)

    def test_it_splits_a_row_on_a_quoted_newline(self):
        self.assertEqual(len(naive('a,"x\ny"\n')), 2)
        self.assertEqual(len(parse('a,"x\ny"\n')), 1)

    def test_it_leaves_quotes_in_the_value(self):
        self.assertIn('"', naive('"a"\n')[0][0])
        self.assertNotIn('"', parse('"a"\n')[0][0])


class TestDifferential(unittest.TestCase):
    def test_a_short_generated_run_finds_nothing(self):
        trials, failures, naive_wrong = diffrun(trials=4000, seed=11)
        self.assertEqual(failures, [])
        # and the baseline should still be failing, or the generator went soft
        self.assertGreater(naive_wrong, trials // 4)


class TestCompounding(unittest.TestCase):
    def test_per_file_failure_follows_the_binomial(self):
        """One bad field ruins the file, so the per-file rate is
        1-(1-p)^rows. Pinned because the README quotes it."""
        import random

        from failures import FIRST_NAMES

        rng = random.Random(5)
        rows, p, trials = 8, 0.05, 3000
        wrong = 0
        for _ in range(trials):
            out = ["id,name,note"]
            for i in range(rows):
                note = '"a,b"' if rng.random() < p else "fine"
                out.append(f"{i},{rng.choice(FIRST_NAMES)},{note}")
            text = "\n".join(out) + "\n"
            if naive(text) != ref(text):
                wrong += 1
        predicted = 1 - (1 - p) ** rows
        self.assertAlmostEqual(wrong / trials, predicted, delta=0.04)


if __name__ == "__main__":
    unittest.main()
