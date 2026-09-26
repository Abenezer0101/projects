"""python3 -m unittest discover -s tests -v   (stdlib only)

The tests that matter are the ones asserting a rule does NOT fire: a data
quality gate that flags everything is as useless as one that flags nothing,
and false positives are how a team learns to ignore the gate.
"""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from assay import mutate, read_csv, run, split, write_csv
from assay.engine import Report
from assay.rules import (ControlTotal, Compare, ColumnsExist, ForeignKey, InSet,
                         IsType, Matches, NoPadding, NotNull, Range, RowCount,
                         Unique, as_datetime, as_number, is_null)
from assay.spec import SpecError, Suite, build_rule, load_spec

ROOT = Path(__file__).resolve().parents[1]


def rows(*dicts):
    return [dict(d) for d in dicts]


def fire(rule, data):
    return [v.row for v in rule.run(data).violations]


class TestCoercion(unittest.TestCase):
    def test_nullish_values(self):
        for v in ("", "  ", "NA", "n/a", "NULL", "none", "NaN", "-", None):
            self.assertTrue(is_null(v), repr(v))

    def test_real_values_are_not_null(self):
        for v in ("0", "false", "no", "none of the above", "N", "0.0"):
            self.assertFalse(is_null(v), repr(v))

    def test_number_parsing_tolerates_formatting(self):
        self.assertEqual(as_number("1,234"), 1234)
        self.assertEqual(as_number("$5.50"), 5.5)
        self.assertEqual(as_number(" -3 "), -3)
        self.assertIsNone(as_number("twelve"))
        self.assertIsNone(as_number(""))

    def test_datetime_accepts_the_common_layouts(self):
        for v in ("2026-07-19 14:03:00", "07/19/2026 14:10", "21-Jul-2026 18:38",
                  "2026-07-19", "2026-07-19T14:03:00"):
            self.assertIsNotNone(as_datetime(v), v)

    def test_datetime_rejects_non_dates(self):
        for v in ("not a date", "13/45/2026", "2026-13-01"):
            self.assertIsNone(as_datetime(v), v)


class TestRules(unittest.TestCase):
    def test_not_null(self):
        self.assertEqual(fire(NotNull("r", columns=("a",)),
                              rows({"a": "1"}, {"a": ""}, {"a": "NA"})), [1, 2])

    def test_unique_reports_the_later_copy(self):
        self.assertEqual(fire(Unique("r", columns=("a",)),
                              rows({"a": "x"}, {"a": "y"}, {"a": "x"})), [2])

    def test_unique_on_a_composite_key(self):
        data = rows({"a": "1", "b": "x"}, {"a": "1", "b": "y"}, {"a": "1", "b": "x"})
        self.assertEqual(fire(Unique("r", columns=("a", "b")), data), [2])
        self.assertEqual(fire(Unique("r", columns=("a",)), data), [1, 2])

    def test_rules_other_than_not_null_skip_nulls(self):
        """The single most important behaviour in the library.

        If `range` flagged empty cells, every optional column would need a
        null exemption and the suite would drown in noise. The cost is that a
        column with no not_null rule has NO coverage against becoming empty --
        which is exactly the blind spot `assay audit` reports.
        """
        blank = rows({"a": ""}, {"a": "NA"})
        for rule in (Range("r", columns=("a",), min=0, max=1),
                     InSet("r", columns=("a",), allowed=frozenset({"x"})),
                     Matches("r", columns=("a",), pattern="x"),
                     IsType("r", columns=("a",), type="int")):
            self.assertEqual(fire(rule, blank), [], rule.kind)
        self.assertEqual(fire(NotNull("r", columns=("a",)), blank), [0, 1])

    def test_range_separates_out_of_range_from_not_a_number(self):
        data = rows({"a": "5"}, {"a": "50"}, {"a": "abc"})
        res = Range("r", columns=("a",), min=0, max=10).run(data)
        self.assertEqual([v.row for v in res.violations], [1, 2])
        self.assertIn("above", res.violations[0].detail)
        self.assertIn("not a number", res.violations[1].detail)

    def test_range_with_only_one_bound(self):
        data = rows({"a": "-1"}, {"a": "5"})
        self.assertEqual(fire(Range("r", columns=("a",), min=0), data), [0])
        self.assertEqual(fire(Range("r", columns=("a",), max=0), data), [1])

    def test_in_set_is_case_insensitive_by_default(self):
        data = rows({"a": "Member"}, {"a": "ghost"})
        allowed = frozenset({"member"})
        self.assertEqual(fire(InSet("r", columns=("a",), allowed=allowed), data), [1])
        self.assertEqual(fire(InSet("r", columns=("a",), allowed=allowed,
                                    case_sensitive=True), data), [0, 1])

    def test_matches_must_cover_the_whole_value(self):
        # a partial match would let "R123456-DELETED" pass an id format check
        data = rows({"a": "R123456"}, {"a": "R123456-DELETED"})
        self.assertEqual(fire(Matches("r", columns=("a",), pattern="R[0-9]{6}"), data), [1])

    def test_is_type_int_rejects_a_fraction(self):
        data = rows({"a": "3"}, {"a": "3.5"})
        self.assertEqual(fire(IsType("r", columns=("a",), type="int"), data), [1])
        self.assertEqual(fire(IsType("r", columns=("a",), type="float"), data), [])

    def test_no_padding(self):
        self.assertEqual(fire(NoPadding("r", columns=("a",)),
                              rows({"a": "x"}, {"a": " x"}, {"a": "x "})), [1, 2])

    def test_compare_on_datetimes(self):
        data = rows({"s": "2026-01-01 10:00:00", "e": "2026-01-01 11:00:00"},
                    {"s": "2026-01-01 12:00:00", "e": "2026-01-01 11:00:00"},
                    {"s": "2026-01-01 11:00:00", "e": "2026-01-01 11:00:00"})
        self.assertEqual(fire(Compare("r", columns=("s", "e"), op="<"), data), [1, 2])

    def test_compare_across_mixed_date_layouts(self):
        # the same instant written two ways must still compare correctly
        data = rows({"s": "07/19/2026 14:03", "e": "2026-07-19 14:10:00"})
        self.assertEqual(fire(Compare("r", columns=("s", "e"), op="<"), data), [])

    def test_compare_skips_rows_with_a_missing_side(self):
        data = rows({"s": "", "e": "2026-01-01"}, {"s": "2026-01-01", "e": ""})
        self.assertEqual(fire(Compare("r", columns=("s", "e"), op="<"), data), [])

    def test_row_count(self):
        three = rows({"a": "1"}, {"a": "2"}, {"a": "3"})
        self.assertEqual(fire(RowCount("r", min=3, max=3), three), [])
        self.assertEqual(len(fire(RowCount("r", min=4), three)), 1)
        self.assertEqual(len(fire(RowCount("r", max=2), three)), 1)

    def test_columns_exist(self):
        data = rows({"a": "1"})
        self.assertEqual(fire(ColumnsExist("r", columns=("a",)), data), [])
        self.assertEqual(len(fire(ColumnsExist("r", columns=("a", "b")), data)), 1)

    def test_foreign_key(self):
        refs = {"dim": rows({"id": "1"}, {"id": "2"})}
        data = rows({"fk": "1"}, {"fk": "9"})
        rule = ForeignKey("r", columns=("fk",), ref="dim", ref_column="id")
        self.assertEqual([v.row for v in rule.run(data, {"refs": refs}).violations], [1])

    def test_foreign_key_without_its_reference_fails_loudly(self):
        """A missing reference is a broken rule, not a clean dataset."""
        rule = ForeignKey("r", columns=("fk",), ref="dim", ref_column="id")
        res = rule.run(rows({"fk": "1"}), {"refs": {}})
        self.assertFalse(res.passed)
        self.assertIn("not supplied", res.violations[0].detail)

    def test_control_total_catches_what_a_range_cannot(self):
        # x10 on a small value: inside any plausible per-row bound, visible in the sum
        clean = rows({"p": "1000"}, {"p": "2000"}, {"p": "3000"})
        shifted = rows({"p": "10000"}, {"p": "2000"}, {"p": "3000"})
        per_row = Range("r", columns=("p",), min=0, max=50000)
        total = ControlTotal("t", columns=("p",), stat="sum", expected=6000, tolerance=0.01)
        self.assertEqual(fire(per_row, shifted), [])        # per-row rule is blind
        self.assertEqual(fire(total, clean), [])
        self.assertEqual(len(fire(total, shifted)), 1)      # the aggregate is not

    def test_control_total_stats(self):
        data = rows({"p": "1"}, {"p": "2"}, {"p": "3"}, {"p": ""})
        for stat, expected in (("sum", 6), ("mean", 2), ("min", 1), ("max", 3), ("count", 3)):
            rule = ControlTotal("t", columns=("p",), stat=stat, expected=expected, tolerance=0.001)
            self.assertEqual(fire(rule, data), [], f"{stat} should equal {expected}")

    def test_control_total_respects_its_tolerance(self):
        data = rows({"p": "101"})
        self.assertEqual(fire(ControlTotal("t", columns=("p",), expected=100, tolerance=0.02), data), [])
        self.assertEqual(len(fire(ControlTotal("t", columns=("p",), expected=100, tolerance=0.005), data)), 1)


class TestSpec(unittest.TestCase):
    def test_loads_the_shipped_examples(self):
        for name in ("trips.toml", "states.toml", "states_hardened.toml"):
            suite = load_spec(ROOT / "examples" / name)
            self.assertGreater(len(suite), 0, name)

    def test_column_singular_and_plural_both_work(self):
        a = build_rule({"id": "x", "kind": "not_null", "column": "c"})
        b = build_rule({"id": "x", "kind": "not_null", "columns": ["c"]})
        self.assertEqual(a.columns, b.columns, )

    def test_unknown_kind_is_refused(self):
        with self.assertRaises(SpecError):
            build_rule({"id": "x", "kind": "vibes", "column": "c"})

    def test_a_typo_in_a_field_name_is_refused(self):
        """Silently ignoring an unknown key means a rule that does not do
        what its author believes it does."""
        with self.assertRaises(SpecError):
            build_rule({"id": "x", "kind": "range", "column": "c", "minimum": 0})

    def test_missing_required_fields_are_refused(self):
        for entry in ({"kind": "not_null", "column": "c"},
                      {"id": "x", "kind": "in_set", "column": "c"},
                      {"id": "x", "kind": "range", "column": "c"},
                      {"id": "x", "kind": "matches", "column": "c"},
                      {"id": "x", "kind": "compare", "columns": ["a"], "op": "<"},
                      {"id": "x", "kind": "control_total", "column": "c"},
                      {"id": "x", "kind": "foreign_key", "column": "c"}):
            with self.assertRaises(SpecError, msg=str(entry)):
                build_rule(entry)

    def test_bad_values_are_refused(self):
        for entry in ({"id": "x", "kind": "not_null", "column": "c", "severity": "maybe"},
                      {"id": "x", "kind": "matches", "column": "c", "pattern": "([a-z"},
                      {"id": "x", "kind": "is_type", "column": "c", "type": "blob"},
                      {"id": "x", "kind": "compare", "columns": ["a", "b"], "op": "~"},
                      {"id": "x", "kind": "control_total", "column": "c",
                       "expected": 1, "tolerance": 2.0}):
            with self.assertRaises(SpecError, msg=str(entry)):
                build_rule(entry)

    def test_a_suite_with_no_rules_is_refused(self):
        with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as fh:
            fh.write('name = "empty"\n')
        with self.assertRaises(SpecError):
            load_spec(fh.name)

    def test_duplicate_rule_ids_are_refused(self):
        with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as fh:
            fh.write('[[rule]]\nid="a"\nkind="not_null"\ncolumn="c"\n'
                     '[[rule]]\nid="a"\nkind="not_null"\ncolumn="d"\n')
        with self.assertRaises(SpecError):
            load_spec(fh.name)


class TestEngine(unittest.TestCase):
    def setUp(self):
        self.data = rows({"a": "1", "b": "x"}, {"a": "", "b": "y"}, {"a": "3", "b": ""})

    def suite(self, *rules):
        return Suite("t", list(rules))

    def test_error_rules_quarantine_rows_and_warnings_do_not(self):
        rep = run(self.suite(NotNull("err", severity="error", columns=("a",)),
                             NotNull("warn", severity="warn", columns=("b",))), self.data)
        self.assertEqual(rep.bad_rows, {1})
        self.assertFalse(rep.ok)
        self.assertEqual(len(rep.warnings), 1)

    def test_a_suite_of_only_warnings_still_passes(self):
        rep = run(self.suite(NotNull("w", severity="warn", columns=("a",))), self.data)
        self.assertTrue(rep.ok)
        self.assertEqual(rep.bad_rows, set())

    def test_split_preserves_order_and_loses_nothing(self):
        rep = run(self.suite(NotNull("e", columns=("a",))), self.data)
        clean, dirty = split(self.data, rep)
        self.assertEqual(len(clean) + len(dirty), len(self.data))
        self.assertEqual(clean, [self.data[0], self.data[2]])
        self.assertEqual(dirty, [self.data[1]])

    def test_table_level_failures_fail_the_run_without_quarantining(self):
        rep = run(self.suite(RowCount("n", min=99)), self.data)
        self.assertFalse(rep.ok)
        self.assertEqual(rep.bad_rows, set())      # there is no one row to blame

    def test_csv_round_trip(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "x.csv"
            write_csv(p, self.data)
            self.assertEqual(read_csv(p), self.data)

    def test_report_json_is_serialisable(self):
        import json
        rep = run(self.suite(NotNull("e", columns=("a",))), self.data)
        json.dumps(rep.as_dict())


class TestMutations(unittest.TestCase):
    def setUp(self):
        self.data = [{"id": f"R{i:03d}", "n": str(i * 10)} for i in range(1, 51)]

    def test_every_mutation_leaves_the_original_alone(self):
        before = [dict(r) for r in self.data]
        for m in (mutate.blank_out("id"), mutate.duplicate_rows(), mutate.drop_rows(),
                  mutate.shift_decimal("n"), mutate.rescale("n"),
                  mutate.swap_columns("id", "n"), mutate.unknown_category("id"),
                  mutate.pad_whitespace("id"), mutate.reverse_pair("id", "n"),
                  mutate.inject_outlier("n"), mutate.truncate_values("id"),
                  mutate.corrupt_type("n")):
            m(self.data)
            self.assertEqual(self.data, before, m.name)

    def test_mutations_are_deterministic(self):
        m = mutate.blank_out("id", frac=0.2, seed=99)
        self.assertEqual(m(self.data), m(self.data))

    def test_each_mutation_actually_changes_something(self):
        for m in (mutate.blank_out("id"), mutate.shift_decimal("n"), mutate.rescale("n"),
                  mutate.swap_columns("id", "n"), mutate.pad_whitespace("id"),
                  mutate.inject_outlier("n"), mutate.truncate_values("id")):
            self.assertNotEqual(m(self.data), self.data, m.name)
        self.assertGreater(len(mutate.duplicate_rows()(self.data)), len(self.data))
        self.assertLess(len(mutate.drop_rows()(self.data)), len(self.data))


class TestAudit(unittest.TestCase):
    def setUp(self):
        self.data = [{"id": f"R{i:03d}", "n": str(i * 10)} for i in range(1, 51)]

    def test_a_rule_that_sees_the_corruption_is_recorded_as_catching_it(self):
        suite = Suite("s", [NotNull("id_present", columns=("id",))])
        res = mutate.audit(suite, self.data, [mutate.blank_out("id", frac=0.2)])
        self.assertTrue(res.findings[0].caught)
        self.assertEqual(res.findings[0].by, ["id_present"])

    def test_a_suite_blind_to_the_corruption_scores_zero(self):
        suite = Suite("s", [NotNull("id_present", columns=("id",))])
        res = mutate.audit(suite, self.data, [mutate.pad_whitespace("id")])
        self.assertFalse(res.findings[0].caught)
        self.assertEqual(res.score, 0.0)

    def test_warn_rules_do_not_count_as_catching(self):
        """A warning does not stop a pipeline, so it has not caught anything."""
        suite = Suite("s", [NotNull("w", severity="warn", columns=("id",))])
        res = mutate.audit(suite, self.data, [mutate.blank_out("id", frac=0.2)])
        self.assertFalse(res.findings[0].caught)

    def test_a_corruption_that_deepens_an_existing_failure_is_caught(self):
        """Real data already fails rules at baseline. Counting only NEWLY
        failing rules would miss a corruption that makes a known problem
        worse, so an increase in violations counts too."""
        dirty = self.data + [{"id": "", "n": "1"}]
        suite = Suite("s", [NotNull("id_present", columns=("id",))])
        res = mutate.audit(suite, dirty, [mutate.blank_out("id", frac=0.2)])
        self.assertFalse(res.baseline_ok)
        self.assertTrue(res.findings[0].caught)

    def test_drop_rows_is_only_visible_to_a_table_level_rule(self):
        """Violations go DOWN when rows vanish, so an increase-only test
        would miss it. A row_count rule is the only thing that sees it."""
        per_row = Suite("s", [NotNull("id_present", columns=("id",))])
        self.assertFalse(mutate.audit(per_row, self.data, [mutate.drop_rows()]).findings[0].caught)
        with_count = Suite("s", [RowCount("n", min=50)])
        self.assertTrue(mutate.audit(with_count, self.data, [mutate.drop_rows()]).findings[0].caught)

    def test_score_is_the_fraction_caught(self):
        suite = Suite("s", [NotNull("id_present", columns=("id",))])
        res = mutate.audit(suite, self.data,
                           [mutate.blank_out("id", frac=0.2), mutate.pad_whitespace("id")])
        self.assertEqual(res.score, 0.5)
        self.assertEqual(len(res.caught), 1)
        self.assertEqual(len(res.missed), 1)

    def test_audit_json_is_serialisable(self):
        import json
        suite = Suite("s", [NotNull("p", columns=("id",))])
        json.dumps(mutate.audit(suite, self.data, [mutate.blank_out("id")]).as_dict())


class TestCLI(unittest.TestCase):
    """End to end, as a subprocess, because the exit code is the product."""

    def run_cli(self, *args):
        return subprocess.run([sys.executable, "-m", "assay.cli", *args],
                              capture_output=True, text=True, cwd=ROOT,
                              env={"PYTHONPATH": str(ROOT), "PATH": "/usr/bin:/bin"})

    def test_a_failing_dataset_exits_nonzero(self):
        r = self.run_cli("check", "examples/trips.toml", "--no-colour")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("FAIL", r.stdout)

    def test_a_clean_dataset_exits_zero(self):
        r = self.run_cli("check", "examples/states_hardened.toml", "--no-colour")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("PASS", r.stdout)

    def test_the_colour_flag_works_on_either_side_of_the_subcommand(self):
        a = self.run_cli("--no-colour", "check", "examples/states_hardened.toml")
        b = self.run_cli("check", "examples/states_hardened.toml", "--no-colour")
        self.assertEqual(a.returncode, 0, a.stderr)
        self.assertEqual(b.returncode, 0, b.stderr)
        self.assertNotIn("\033[", a.stdout)
        self.assertNotIn("\033[", b.stdout)

    def test_quarantine_and_clean_files_partition_the_input(self):
        with tempfile.TemporaryDirectory() as d:
            good, bad = Path(d) / "g.csv", Path(d) / "b.csv"
            self.run_cli("check", "examples/trips.toml", "--no-colour",
                         "--clean", str(good), "--quarantine", str(bad))
            total = len(read_csv(ROOT / "examples" / "trips.csv"))
            self.assertEqual(len(read_csv(good)) + len(read_csv(bad)), total)
            self.assertGreater(len(read_csv(bad)), 0)

    def test_a_broken_spec_exits_two_and_says_why(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "bad.toml"
            p.write_text('[[rule]]\nid="x"\nkind="nonsense"\ncolumn="c"\n')
            r = self.run_cli("check", str(p), "examples/trips.csv")
            self.assertEqual(r.returncode, 2)
            self.assertIn("unknown kind", r.stderr)

    def test_a_missing_file_exits_two(self):
        r = self.run_cli("check", "examples/trips.toml", "nope.csv")
        self.assertEqual(r.returncode, 2)

    def test_audit_reports_a_score(self):
        r = self.run_cli("audit", "examples/states.toml", "--no-colour")
        self.assertEqual(r.returncode, 0)
        self.assertIn("detection score", r.stdout)
        self.assertIn("MISSED", r.stdout)

    def test_audit_fail_under_gates(self):
        ok = self.run_cli("audit", "examples/states.toml", "--no-colour", "--fail-under", "0.5")
        bad = self.run_cli("audit", "examples/states.toml", "--no-colour", "--fail-under", "0.9")
        self.assertEqual(ok.returncode, 0)
        self.assertEqual(bad.returncode, 1)

    def test_hardening_the_suite_raises_the_score(self):
        """The claim the README makes, asserted."""
        import json
        before = json.loads(self.run_cli("audit", "examples/states.toml", "--json").stdout)
        after = json.loads(self.run_cli("audit", "examples/states_hardened.toml", "--json").stdout)
        self.assertGreater(after["score"], before["score"])
        self.assertEqual(before["caught"], 8)
        self.assertEqual(after["caught"], 12)
        self.assertEqual(before["mutations"], after["mutations"])


if __name__ == "__main__":
    unittest.main(verbosity=1)
