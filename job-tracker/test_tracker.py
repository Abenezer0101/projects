"""python3 test_tracker.py   (stdlib unittest)

The funnel tests are the point. A funnel built from `current_stage` is the
single most common analytics bug in a pipeline tracker, and it fails silently:
the chart renders, the percentages look plausible, and every one of them is
wrong.
"""

import unittest
from datetime import date, timedelta

import db
from app import create_app

TODAY = "2026-09-17"


def d(offset):
    return (date.fromisoformat(TODAY) + timedelta(days=offset)).isoformat()


class TestSchema(unittest.TestCase):
    def setUp(self):
        self.c = db.connect()
        self.cid = db.add_company(self.c, "Acme", "Software")

    def test_company_is_deduplicated(self):
        again = db.add_company(self.c, "Acme", "Software")
        self.assertEqual(again, self.cid)
        self.assertEqual(self.c.execute("SELECT COUNT(*) n FROM companies").fetchone()["n"], 1)

    def test_creating_an_application_writes_its_applied_event(self):
        a = db.add_application(self.c, self.cid, "Analyst", "Referral", d(-10))
        rows = db.get_application(self.c, a)["events"]
        self.assertEqual([r["stage"] for r in rows], ["applied"])

    def test_advance_appends_and_never_rewrites(self):
        a = db.add_application(self.c, self.cid, "Analyst", "Referral", d(-30))
        db.advance(self.c, a, "screen", d(-20))
        db.advance(self.c, a, "interview", d(-10))
        got = db.get_application(self.c, a)
        self.assertEqual([r["stage"] for r in got["events"]], ["applied", "screen", "interview"])
        self.assertEqual(got["app"]["current_stage"], "interview")

    def test_days_in_is_measured_from_applying(self):
        a = db.add_application(self.c, self.cid, "Analyst", "Referral", d(-30))
        db.advance(self.c, a, "screen", d(-23))
        self.assertEqual(db.get_application(self.c, a)["events"][1]["days_in"], 7)

    def test_terminal_stage_closes_the_application(self):
        a = db.add_application(self.c, self.cid, "Analyst", "Referral", d(-30))
        db.advance(self.c, a, "rejected", d(-5))
        app = db.get_application(self.c, a)["app"]
        self.assertEqual(app["outcome"], "rejected")
        self.assertEqual(app["closed_on"], d(-5))

    def test_unknown_stage_is_refused(self):
        a = db.add_application(self.c, self.cid, "Analyst", "Referral", d(-1))
        with self.assertRaises(ValueError):
            db.advance(self.c, a, "vibes", d(0))

    def test_delete_removes_the_history_too(self):
        a = db.add_application(self.c, self.cid, "Analyst", "Referral", d(-9))
        db.advance(self.c, a, "screen", d(-3))
        db.delete_application(self.c, a)
        self.assertIsNone(db.get_application(self.c, a))
        self.assertEqual(self.c.execute("SELECT COUNT(*) n FROM stage_events").fetchone()["n"], 0)

    def test_update_ignores_fields_it_does_not_own(self):
        a = db.add_application(self.c, self.cid, "Analyst", "Referral", d(-9))
        db.update_application(self.c, a, role="Senior Analyst", current_stage="offer", id=999)
        app = db.get_application(self.c, a)["app"]
        self.assertEqual(app["role"], "Senior Analyst")
        self.assertEqual(app["current_stage"], "applied")   # not settable this way
        self.assertEqual(app["id"], a)

    def test_missing_application_is_none(self):
        self.assertIsNone(db.get_application(self.c, 12345))


class TestFunnel(unittest.TestCase):
    """The core claim: counting the log and counting current_stage disagree."""

    def setUp(self):
        self.c = db.connect()
        cid = db.add_company(self.c, "Acme", "Software")
        # one application that went all the way to an offer
        a = db.add_application(self.c, cid, "Analyst", "Referral", d(-90))
        for i, s in enumerate(["screen", "interview", "onsite", "offer"]):
            db.advance(self.c, a, s, d(-80 + i * 10))
        # one rejected after the interview
        b = db.add_application(self.c, cid, "Analyst", "LinkedIn", d(-80))
        db.advance(self.c, b, "screen", d(-70))
        db.advance(self.c, b, "interview", d(-60))
        db.advance(self.c, b, "rejected", d(-55))
        # one that never got a reply
        db.add_application(self.c, cid, "Analyst", "Job board", d(-70))

    def test_funnel_counts_every_stage_an_application_passed(self):
        f = {r["stage"]: r["n"] for r in db.funnel(self.c)}
        self.assertEqual(f, {"applied": 3, "screen": 2, "interview": 2, "onsite": 1, "offer": 1})

    def test_the_naive_funnel_disagrees_with_reality(self):
        naive = {r["stage"]: r["n"] for r in db.funnel_naive(self.c)}
        # two applications reached interview; current_stage can see neither,
        # because one moved on to an offer and the other was rejected
        self.assertEqual(naive["interview"], 0)
        self.assertEqual(db.funnel(self.c)[2]["n"], 2)

    def test_the_naive_funnel_can_be_internally_impossible(self):
        naive = {r["stage"]: r["n"] for r in db.funnel_naive(self.c)}
        self.assertGreater(naive["offer"], naive["interview"])   # more offers than interviews

    def test_a_funnel_never_increases_down_the_stages(self):
        ns = [r["n"] for r in db.funnel(self.c)]
        self.assertEqual(ns, sorted(ns, reverse=True), ns)

    def test_conversion_is_relative_to_the_previous_stage(self):
        f = db.funnel(self.c)
        self.assertIsNone(f[0]["from_prev"])
        self.assertAlmostEqual(f[1]["from_prev"], 2 / 3)
        self.assertAlmostEqual(f[2]["from_prev"], 1.0)
        self.assertAlmostEqual(f[3]["from_top"], 1 / 3)

    def test_empty_database_does_not_divide_by_zero(self):
        empty = db.connect()
        f = db.funnel(empty)
        self.assertEqual([r["n"] for r in f], [0, 0, 0, 0, 0])
        self.assertTrue(all(r["from_prev"] is None for r in f))
        self.assertIsNone(db.response_times(empty)["median"])
        self.assertIsNone(db.ghost_rate(empty, TODAY)["rate"])


class TestAnalytics(unittest.TestCase):
    def setUp(self):
        self.c = db.connect()
        self.cid = db.add_company(self.c, "Acme", "Software")

    def test_response_time_is_to_the_FIRST_reply(self):
        a = db.add_application(self.c, self.cid, "A", "Referral", d(-60))
        db.advance(self.c, a, "screen", d(-50))       # 10 days
        db.advance(self.c, a, "interview", d(-20))    # later, must not win
        self.assertEqual(db.response_times(self.c)["median"], 10)

    def test_median_is_not_the_mean(self):
        for offset, reply in ((-90, 1), (-80, 2), (-70, 60)):
            a = db.add_application(self.c, self.cid, "A", "Referral", d(offset))
            db.advance(self.c, a, "screen", d(offset + reply))
        r = db.response_times(self.c)
        self.assertEqual(r["median"], 2)              # unmoved by the 60-day outlier
        self.assertAlmostEqual(r["mean"], 21.0)
        self.assertEqual(r["n"], 3)

    def test_applications_with_no_reply_are_not_counted_as_fast(self):
        db.add_application(self.c, self.cid, "A", "Referral", d(-60))
        self.assertEqual(db.response_times(self.c)["n"], 0)

    def test_recent_applications_are_excluded_from_the_no_reply_rate(self):
        db.add_application(self.c, self.cid, "Old", "Referral", d(-60))      # silent, counts
        db.add_application(self.c, self.cid, "New", "Referral", d(-3))       # too recent
        g = db.ghost_rate(self.c, TODAY)
        self.assertEqual(g["eligible"], 1)
        self.assertEqual(g["silent"], 1)
        self.assertEqual(g["excluded_too_recent"], 1)
        self.assertEqual(g["rate"], 1.0)

    def test_a_reply_clears_the_no_reply_flag(self):
        a = db.add_application(self.c, self.cid, "A", "Referral", d(-60))
        db.advance(self.c, a, "screen", d(-50))
        self.assertEqual(db.ghost_rate(self.c, TODAY)["silent"], 0)

    def test_by_source_counts_interviews_ever_reached(self):
        a = db.add_application(self.c, self.cid, "A", "Referral", d(-60))
        db.advance(self.c, a, "screen", d(-55))
        db.advance(self.c, a, "interview", d(-50))
        db.advance(self.c, a, "rejected", d(-45))     # closed, but it DID interview
        db.add_application(self.c, self.cid, "B", "Job board", d(-60))
        rows = {r["source"]: r for r in db.by_source(self.c)}
        self.assertEqual(rows["Referral"]["interviews"], 1)
        self.assertEqual(rows["Job board"]["interviews"], 0)

    def test_monthly_groups_by_year_month(self):
        db.add_application(self.c, self.cid, "A", "Referral", "2026-01-14")
        db.add_application(self.c, self.cid, "B", "Referral", "2026-01-30")
        db.add_application(self.c, self.cid, "C", "Referral", "2026-02-02")
        self.assertEqual(db.monthly(self.c), [{"month": "2026-01", "n": 2}, {"month": "2026-02", "n": 1}])


class TestSeed(unittest.TestCase):
    def test_seed_is_deterministic(self):
        a, b = db.connect(), db.connect()
        db.seed(a); db.seed(b)
        self.assertEqual(db.funnel(a), db.funnel(b))

    def test_seed_produces_a_monotone_funnel(self):
        c = db.seed(db.connect())
        ns = [r["n"] for r in db.funnel(c)]
        self.assertEqual(ns, sorted(ns, reverse=True), ns)
        self.assertEqual(ns[0], 120)

    def test_no_event_precedes_its_application(self):
        c = db.seed(db.connect())
        bad = c.execute("""SELECT COUNT(*) n FROM stage_events e
                           JOIN applications a ON a.id = e.application_id
                           WHERE date(e.occurred_on) < date(a.applied_on)""").fetchone()["n"]
        self.assertEqual(bad, 0)

    def test_referrals_get_replies_more_often_than_job_boards(self):
        """Asserted on reply rate, not interview rate.

        Interview counts in the seed are single digits per source, where one
        extra interview moves the rate several points -- that is noise to
        assert on. Replies rest on a large enough count to mean something.
        """
        c = db.seed(db.connect())
        r = {x["source"]: x for x in db.by_source(c)}
        ref = r["Referral"]["replies"] / r["Referral"]["applications"]
        board = r["Job board"]["replies"] / r["Job board"]["applications"]
        self.assertGreater(ref, board * 1.5, (ref, board))


class TestApp(unittest.TestCase):
    def setUp(self):
        self.app = create_app(":memory:", seed=False, today=TODAY)
        self.app.config["TESTING"] = True
        self.c = self.app.test_client()

    def add(self, company="Acme", role="Analyst", **kw):
        return self.c.post("/applications", data={"company": company, "role": role,
                                                  "source": "Referral", "applied_on": d(-20), **kw},
                           follow_redirects=True)

    def test_pages_render(self):
        for path in ("/", "/dashboard", "/api/analytics"):
            self.assertEqual(self.c.get(path).status_code, 200, path)

    def test_create_read_update_delete(self):
        self.assertEqual(self.add().status_code, 200)
        self.assertIn(b"Acme", self.c.get("/").data)
        self.assertEqual(self.c.post("/applications/1/edit",
                                     data={"role": "BI Developer", "source": "LinkedIn", "notes": "n"},
                                     follow_redirects=True).status_code, 200)
        self.assertIn(b"BI Developer", self.c.get("/applications/1").data)
        self.c.post("/applications/1/delete", follow_redirects=True)
        self.assertEqual(self.c.get("/applications/1").status_code, 404)

    def test_creating_without_a_role_is_rejected(self):
        self.c.post("/applications", data={"company": "X", "role": ""}, follow_redirects=True)
        self.assertEqual(self.c.get("/api/analytics").get_json()["totals"]["applications"], 0)

    def test_advancing_through_the_ui_moves_the_funnel(self):
        self.add()
        for stage in ("screen", "interview"):
            self.c.post("/applications/1/advance", data={"stage": stage, "occurred_on": d(-5)},
                        follow_redirects=True)
        f = {r["stage"]: r["n"] for r in self.c.get("/api/analytics").get_json()["funnel"]}
        self.assertEqual(f["interview"], 1)
        self.assertEqual(f["screen"], 1)

    def test_a_bogus_stage_does_not_500(self):
        self.add()
        r = self.c.post("/applications/1/advance", data={"stage": "vibes"})
        self.assertIn(r.status_code, (302, 400))
        self.assertEqual(self.c.get("/api/analytics").get_json()["funnel"][1]["n"], 0)

    def test_acting_on_a_missing_application_is_404_not_500(self):
        for path in ("/applications/999", "/applications/999/advance",
                     "/applications/999/edit", "/applications/999/delete"):
            r = self.c.post(path, data={"stage": "screen"}) if path != "/applications/999" \
                else self.c.get(path)
            self.assertEqual(r.status_code, 404, path)

    def test_filters_narrow_the_list(self):
        self.add(company="Acme", role="Analyst")
        self.add(company="Globex", role="Engineer", source="Job board")
        # assert on the table rows, not the whole page: the company autocomplete
        # datalist lists every known company regardless of the active filter
        def rows(qs):
            body = self.c.get(qs).data.decode()
            table = body.split("<tbody>")[-1].split("</tbody>")[0]
            return [c for c in ("Acme", "Globex") if c in table]

        self.assertEqual(rows("/?q=Globex"), ["Globex"])
        self.assertEqual(rows("/?q=Acme"), ["Acme"])
        self.assertEqual(rows("/?source=Referral"), ["Acme"])
        self.assertEqual(sorted(rows("/")), ["Acme", "Globex"])

    def test_company_names_are_escaped_not_executed(self):
        self.add(company='<script>alert(1)</script>', role="Analyst")
        body = self.c.get("/").data
        self.assertNotIn(b"<script>alert(1)</script>", body)
        self.assertIn(b"&lt;script&gt;", body)

    def test_dashboard_shows_both_funnels(self):
        self.add()
        self.c.post("/applications/1/advance", data={"stage": "screen", "occurred_on": d(-5)})
        body = self.c.get("/dashboard").data
        self.assertIn(b"counted from the event log", body)
        self.assertIn(b"common wrong way", body)

    def test_api_matches_the_database(self):
        self.add()
        j = self.c.get("/api/analytics").get_json()
        self.assertEqual(j["funnel"], db.funnel(self.app.config["CONN"]))
        self.assertEqual(j["totals"]["applications"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=1)
