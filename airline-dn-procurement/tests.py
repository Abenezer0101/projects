import sqlite3
import unittest

import analysis
import seed


class TestSchemaIntegrity(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        seed.generate(self.conn)

    def tearDown(self):
        self.conn.close()

    def test_dn_line_quantities_balance(self):
        bad = self.conn.execute(
            "SELECT COUNT(*) FROM dn_lines WHERE qty_accepted + qty_rejected != qty_delivered"
        ).fetchone()[0]
        self.assertEqual(bad, 0)

    def test_no_orphan_dn_lines(self):
        orphans = self.conn.execute("""
            SELECT COUNT(*) FROM dn_lines dl
            LEFT JOIN po_lines pl ON pl.po_line_id = dl.po_line_id
            WHERE pl.po_line_id IS NULL
        """).fetchone()[0]
        self.assertEqual(orphans, 0)

    def test_no_orphan_issues(self):
        orphans = self.conn.execute("""
            SELECT COUNT(*) FROM project_stock_issues psi
            LEFT JOIN projects p ON p.project_id = psi.project_id
            LEFT JOIN parts pt ON pt.part_id = psi.part_id
            WHERE p.project_id IS NULL OR pt.part_id IS NULL
        """).fetchone()[0]
        self.assertEqual(orphans, 0)

    def test_non_trivial_volume(self):
        n_projects = self.conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
        n_po_lines = self.conn.execute("SELECT COUNT(*) FROM po_lines").fetchone()[0]
        n_dn_lines = self.conn.execute("SELECT COUNT(*) FROM dn_lines").fetchone()[0]
        n_issues = self.conn.execute("SELECT COUNT(*) FROM project_stock_issues").fetchone()[0]
        self.assertEqual(n_projects, 15)
        self.assertGreater(n_po_lines, 100)
        self.assertGreater(n_dn_lines, 50)
        self.assertGreater(n_issues, 50)

    def test_seed_is_deterministic(self):
        conn2 = sqlite3.connect(":memory:")
        seed.generate(conn2)
        rows1 = self.conn.execute("SELECT * FROM po_lines ORDER BY po_line_id").fetchall()
        rows2 = conn2.execute("SELECT * FROM po_lines ORDER BY po_line_id").fetchall()
        self.assertEqual(rows1, rows2)
        conn2.close()


class TestStrandedStockFinding(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        seed.generate(self.conn)

    def tearDown(self):
        self.conn.close()

    def test_shortfall_and_idle_surplus_both_exist(self):
        rows = analysis.positions(self.conn)
        total_short = sum(r[5] for r in rows if r[5] > 0)
        total_idle = sum(r[6] for r in rows if r[6] > 0)
        self.assertGreater(total_short, 0)
        self.assertGreater(total_idle, 0)

    def test_stranded_coverage_never_exceeds_shortfall_or_surplus(self):
        cases = analysis.stranded_coverage(self.conn)
        self.assertGreater(len(cases), 0)
        for c in cases:
            self.assertLessEqual(c["coverable"], c["shortfall"])
            self.assertLessEqual(c["coverable"], c["surplus_available"])
            self.assertNotEqual(c["short_project"], c["surplus_project"])

    def test_stranded_coverage_never_overdraws_one_surplus_pool(self):
        # A single (project, part) surplus pool must not be credited to more
        # coverage than it actually holds, even split across several
        # different shortages drawing on it.
        cases = analysis.stranded_coverage(self.conn)
        rows = {(r[0], r[1]): r[6] for r in analysis.positions(self.conn)}
        drawn = {}
        for c in cases:
            key = (c["surplus_project"], c["part_id"])
            drawn[key] = drawn.get(key, 0) + c["coverable"]
        for key, total_drawn in drawn.items():
            self.assertLessEqual(total_drawn, rows[key])

    def test_headline_numbers_match_known_run(self):
        # Pinned to the fixed seed so a logic change that moves these numbers
        # gets caught, instead of silently reported as a new "finding".
        rows = analysis.positions(self.conn)
        total_short = sum(r[5] for r in rows if r[5] > 0)
        cases = analysis.stranded_coverage(self.conn)
        total_coverable = sum(c["coverable"] for c in cases)
        self.assertEqual(total_short, 509)
        self.assertEqual(total_coverable, 495)


class TestDateGeneration(unittest.TestCase):
    def test_all_dates_are_valid_calendar_dates_across_seeds(self):
        for s in (1, 7, 42, 824, 999):
            conn = sqlite3.connect(":memory:")
            seed.generate(conn, seed=s)
            bad = conn.execute(
                "SELECT delivery_date FROM delivery_notes "
                "WHERE julianday(delivery_date) IS NULL"
            ).fetchall()
            conn.close()
            self.assertEqual(bad, [], f"invalid delivery_date under seed={s}")


if __name__ == "__main__":
    unittest.main()
