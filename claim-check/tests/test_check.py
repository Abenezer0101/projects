"""Tests for the checker.

A verifier that cannot fail is worse than no verifier: it produces a green
line that means nothing. Most of these tests therefore construct claims that
SHOULD fail and assert that they do.
"""

from __future__ import annotations

import subprocess
import sys
import unittest

from check import ROOT, check_code, check_prose, verify
from claims import CLAIMS, SKIPPED, Claim


class TestTheCheckerCanFail(unittest.TestCase):
    def test_a_wrong_number_fails(self):
        real = next(c for c in CLAIMS if c.project == "anomaly-detection")
        rotted = Claim(real.project, "9.999", real.snippet)
        result = verify(rotted)
        self.assertFalse(result.ok)
        self.assertFalse(result.code_ok)

    def test_a_claim_absent_from_the_readme_fails(self):
        claim = Claim("anomaly-detection", "2.846",
                      "print('a string no README contains')")
        result = verify(claim)
        self.assertTrue(result.prose_ok)       # 2.846 IS in that README
        self.assertFalse(result.code_ok)       # but the code prints something else
        self.assertFalse(result.ok)

    def test_prose_only_drift_is_caught(self):
        """The code is right and the README has been edited away from it."""
        claim = Claim("anomaly-detection", "a number nobody wrote",
                      "print('a number nobody wrote')")
        result = verify(claim)
        self.assertTrue(result.code_ok)
        self.assertFalse(result.prose_ok)
        self.assertFalse(result.ok)

    def test_a_snippet_that_raises_fails_with_its_error(self):
        result = verify(Claim("anomaly-detection", "x", "raise SystemExit('boom')"))
        self.assertFalse(result.code_ok)
        self.assertIn("boom", result.error)

    def test_a_missing_project_fails_rather_than_passing_quietly(self):
        ok, _, error = check_code(Claim("no-such-project", "x", "print('x')"))
        self.assertFalse(ok)
        self.assertIn("no such project", error)

    def test_a_missing_readme_fails_the_prose_check(self):
        self.assertFalse(check_prose(Claim("no-such-project", "x", "print('x')")))


class TestRegistryHygiene(unittest.TestCase):
    def test_every_claim_names_a_real_project_with_a_readme(self):
        for claim in CLAIMS:
            with self.subTest(claim.project):
                self.assertTrue((ROOT / claim.project / "README.md").exists())

    def test_every_skipped_entry_names_a_real_project(self):
        for project, _what, _why in SKIPPED:
            with self.subTest(project):
                self.assertTrue((ROOT / project).is_dir())

    def test_every_skipped_entry_gives_a_reason(self):
        for project, what, why in SKIPPED:
            with self.subTest(project):
                self.assertGreater(len(why), 20)
                self.assertGreater(len(what), 5)

    def test_no_duplicate_claims(self):
        seen = [(c.project, c.claimed) for c in CLAIMS]
        self.assertEqual(len(seen), len(set(seen)))

    def test_claims_are_not_trivially_short(self):
        """A claim of '1' or '5' would match half the prose in any README and
        prove nothing."""
        for claim in CLAIMS:
            with self.subTest(claim.claimed):
                self.assertGreaterEqual(len(claim.claimed), 3)

    def test_the_registry_covers_a_meaningful_share_of_the_repository(self):
        projects = {c.project for c in CLAIMS} | {p for p, _, _ in SKIPPED}
        self.assertGreaterEqual(len(projects), 15)


class TestTheCliContract(unittest.TestCase):
    def _run(self, *args):
        return subprocess.run([sys.executable, "check.py", *args],
                              cwd=ROOT / "claim-check",
                              capture_output=True, text=True, timeout=400)

    def test_exit_zero_when_everything_reproduces(self):
        done = self._run("--project", "anomaly-detection", "--quiet")
        self.assertEqual(done.returncode, 0, done.stderr)

    def test_unknown_project_exits_two(self):
        done = self._run("--project", "not-a-project")
        self.assertEqual(done.returncode, 2)

    def test_the_summary_line_is_always_printed(self):
        done = self._run("--project", "record-linkage", "--quiet")
        self.assertIn("claims reproduce", done.stdout)


if __name__ == "__main__":
    unittest.main()
