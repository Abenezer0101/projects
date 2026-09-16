"""python3 test_shortener.py   (stdlib unittest, no pytest needed)

The security tests are the point. A shortener that stores `javascript:` and
later emits it in a Location header or an href is an XSS delivery service, and
one that lets a user claim the alias "api" breaks its own routing.
"""

import sqlite3
import threading
import unittest
from urllib.parse import urlsplit

import store
from app import create_app
from validate import ValidationError, check_not_self, normalize_url, validate_alias


class TestNormalize(unittest.TestCase):
    def test_adds_missing_scheme(self):
        self.assertEqual(normalize_url("example.com/x"), "http://example.com/x")

    def test_lowercases_host_but_not_path(self):
        self.assertEqual(normalize_url("HTTP://Example.COM/Path?A=B"),
                         "http://example.com/Path?A=B")

    def test_keeps_port_and_query_and_fragment(self):
        self.assertEqual(normalize_url("http://a.com:8080/p?q=1#f"),
                         "http://a.com:8080/p?q=1#f")

    def test_https_survives(self):
        self.assertEqual(normalize_url("https://a.com/"), "https://a.com/")

    # --- the schemes that make a shortener dangerous ---
    def test_rejects_javascript(self):
        for bad in ("javascript:alert(1)", "JaVaScRiPt:alert(1)", "  javascript:alert(1)  "):
            with self.assertRaises(ValidationError, msg=bad):
                normalize_url(bad)

    def test_rejects_data_file_and_vbscript(self):
        for bad in ("data:text/html,<script>alert(1)</script>",
                    "file:///etc/passwd", "vbscript:msgbox(1)", "ftp://a.com/x"):
            with self.assertRaises(ValidationError, msg=bad):
                normalize_url(bad)

    def test_rejects_control_character_smuggling(self):
        # "java\tscript:" is stripped by some parsers into a working scheme
        for bad in ("java\tscript:alert(1)", "java\nscript:alert(1)", "http://a.com/\x00x"):
            with self.assertRaises(ValidationError, msg=repr(bad)):
                normalize_url(bad)

    def test_rejects_embedded_credentials(self):
        # http://google.com@evil.com reads as "google.com" to a human
        with self.assertRaises(ValidationError):
            normalize_url("http://google.com@evil.com/")

    def test_rejects_empty_and_hostless_and_overlong(self):
        for bad in (None, "", "   ", "notahost", "http://", "http://x/y", "http://a.com/" + "x" * 3000):
            with self.assertRaises(ValidationError, msg=repr(bad)[:40]):
                normalize_url(bad)

    def test_localhost_is_allowed_for_local_testing(self):
        self.assertEqual(normalize_url("http://localhost:5000/x"), "http://localhost:5000/x")

    def test_self_reference_is_rejected(self):
        with self.assertRaises(ValidationError):
            check_not_self("http://short.example/abc", {"short.example"})
        self.assertTrue(check_not_self("http://other.com/a", {"short.example"}))


class TestAlias(unittest.TestCase):
    def test_blank_means_generate_one(self):
        for blank in (None, "", "   "):
            self.assertIsNone(validate_alias(blank))

    def test_accepts_sane_aliases(self):
        for good in ("my-link", "abc", "A_b-9", "x" * 32):
            self.assertEqual(validate_alias(good), good)

    def test_rejects_reserved_words(self):
        # claiming these would shadow the app's own routes
        for bad in ("api", "API", "static", "stats", "s", "health", "favicon.ico"):
            with self.assertRaises(ValidationError, msg=bad):
                validate_alias(bad)

    def test_rejects_bad_shapes(self):
        for bad in ("ab", "x" * 33, "has space", "sla/sh", "dot.dot", "emoji\U0001F600", "semi;colon"):
            with self.assertRaises(ValidationError, msg=repr(bad)):
                validate_alias(bad)


class TestStore(unittest.TestCase):
    def setUp(self):
        self.c = store.connect(":memory:")

    def test_code_shape(self):
        code = store.generate_code()
        self.assertEqual(len(code), store.CODE_LEN)
        self.assertTrue(set(code) <= set(store.ALPHABET))

    def test_codes_are_not_sequential(self):
        codes = {store.generate_code() for _ in range(500)}
        self.assertEqual(len(codes), 500)          # 500 draws, no repeats

    def test_create_and_find(self):
        code, lid = store.create_link(self.c, "http://a.com/x")
        row = store.find(self.c, code)
        self.assertEqual(row["url"], "http://a.com/x")
        self.assertEqual(row["id"], lid)
        self.assertEqual(row["custom"], 0)

    def test_missing_code_is_none(self):
        self.assertIsNone(store.find(self.c, "nothere"))

    def test_custom_alias_is_flagged(self):
        store.create_link(self.c, "http://a.com", alias="mine")
        self.assertEqual(store.find(self.c, "mine")["custom"], 1)

    def test_duplicate_alias_raises_rather_than_overwriting(self):
        store.create_link(self.c, "http://first.com", alias="dup")
        with self.assertRaises(store.CodeTaken):
            store.create_link(self.c, "http://second.com", alias="dup")
        # the original link must survive; INSERT OR REPLACE would have stolen it
        self.assertEqual(store.find(self.c, "dup")["url"], "http://first.com")

    def test_generation_retries_past_a_collision(self):
        taken, seq = "AAAAAA", ["AAAAAA", "AAAAAA", "BBBBBB"]
        store.create_link(self.c, "http://taken.com", alias=taken)
        real = store.generate_code
        store.generate_code = lambda n=6: seq.pop(0)
        try:
            code, _ = store.create_link(self.c, "http://new.com")
        finally:
            store.generate_code = real
        self.assertEqual(code, "BBBBBB")
        self.assertEqual(store.find(self.c, taken)["url"], "http://taken.com")

    def test_gives_up_loudly_rather_than_silently(self):
        store.create_link(self.c, "http://x.com", alias="ZZZZZZ")
        real = store.generate_code
        store.generate_code = lambda n=6: "ZZZZZZ"
        try:
            with self.assertRaises(store.OutOfCodes):
                store.create_link(self.c, "http://y.com")
        finally:
            store.generate_code = real

    def test_concurrent_inserts_of_one_alias_yield_exactly_one_winner(self):
        """A SELECT-then-INSERT would let both threads think the alias was free."""
        path = "file:race?mode=memory&cache=shared"
        keep = sqlite3.connect(path, uri=True)          # holds the shared db alive
        conn = store.connect(path)
        conn.close()
        results, barrier = [], threading.Barrier(8)

        def worker(i):
            c = sqlite3.connect(path, uri=True, check_same_thread=False)
            c.row_factory = sqlite3.Row
            barrier.wait()
            try:
                results.append(("ok", store.create_link(c, f"http://n{i}.com", alias="hot")[0]))
            except store.CodeTaken:
                results.append(("taken", None))
            except sqlite3.OperationalError as e:
                results.append(("locked", str(e)))
            finally:
                c.close()

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
        [t.start() for t in threads]; [t.join() for t in threads]
        keep.close()
        winners = [r for r in results if r[0] == "ok"]
        self.assertEqual(len(winners), 1, results)
        self.assertEqual(len(results), 8)

    def test_clicks_are_counted_not_stored(self):
        code, lid = store.create_link(self.c, "http://a.com")
        for _ in range(3):
            store.record_click(self.c, lid)
        self.assertEqual(store.link_stats(self.c, code)["clicks"], 3)
        self.assertEqual(store.recent_links(self.c)[0]["clicks"], 3)

    def test_link_with_no_clicks_reads_zero_not_missing(self):
        code, _ = store.create_link(self.c, "http://a.com")
        self.assertEqual(store.link_stats(self.c, code)["clicks"], 0)
        self.assertEqual(store.recent_links(self.c)[0]["clicks"], 0)

    def test_stats_of_unknown_code_is_none(self):
        self.assertIsNone(store.link_stats(self.c, "ghost"))

    def test_referrers_group_and_blank_reads_direct(self):
        code, lid = store.create_link(self.c, "http://a.com")
        store.record_click(self.c, lid, referrer="http://news.site")
        store.record_click(self.c, lid, referrer="http://news.site")
        store.record_click(self.c, lid, referrer=None)
        store.record_click(self.c, lid, referrer="")
        refs = {r["src"]: r["n"] for r in store.link_stats(self.c, code)["referrers"]}
        self.assertEqual(refs, {"http://news.site": 2, "direct": 2})

    def test_totals_match_the_rows(self):
        a, aid = store.create_link(self.c, "http://a.com")
        b, bid = store.create_link(self.c, "http://b.com")
        store.record_click(self.c, aid); store.record_click(self.c, bid)
        self.assertEqual(store.totals(self.c), {"links": 2, "clicks": 2})

    def test_recent_is_newest_first_and_limited(self):
        for i in range(12):
            store.create_link(self.c, f"http://s{i}.com")
        rows = store.recent_links(self.c, limit=5)
        self.assertEqual(len(rows), 5)
        self.assertEqual(rows[0]["url"], "http://s11.com")


class TestApp(unittest.TestCase):
    def setUp(self):
        self.app = create_app(":memory:")
        self.c = self.app.test_client()

    def shorten(self, url, alias=None):
        return self.c.post("/api/shorten", json={"url": url, "alias": alias})

    def test_index_renders(self):
        r = self.c.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"URL Shortener", r.data)

    def test_api_round_trip(self):
        r = self.shorten("example.com/deep/path?x=1")
        self.assertEqual(r.status_code, 201)
        body = r.get_json()
        self.assertEqual(body["url"], "http://example.com/deep/path?x=1")
        f = self.c.get("/" + body["code"])
        self.assertEqual(f.status_code, 302)
        self.assertEqual(f.headers["Location"], "http://example.com/deep/path?x=1")

    def test_redirect_is_302_so_clicks_keep_counting(self):
        # a 301 is cached by the browser and later clicks never reach the server
        code = self.shorten("http://a.com").get_json()["code"]
        self.assertEqual(self.c.get("/" + code).status_code, 302)

    def test_following_records_a_click(self):
        code = self.shorten("http://a.com").get_json()["code"]
        for _ in range(3):
            self.c.get("/" + code)
        self.assertEqual(self.c.get("/api/stats/" + code).get_json()["clicks"], 3)

    def test_referrer_header_is_recorded(self):
        code = self.shorten("http://a.com").get_json()["code"]
        self.c.get("/" + code, headers={"Referer": "http://news.site/page"})
        refs = self.c.get("/api/stats/" + code).get_json()["referrers"]
        self.assertEqual(refs[0]["src"], "http://news.site/page")

    def test_dangerous_schemes_never_reach_a_location_header(self):
        for bad in ("javascript:alert(1)", "data:text/html,<script>alert(1)</script>",
                    "file:///etc/passwd", "vbscript:msgbox(1)"):
            r = self.shorten(bad)
            self.assertEqual(r.status_code, 400, bad)
            self.assertIn("error", r.get_json())

    def test_custom_alias_works_and_conflicts_are_409(self):
        r = self.shorten("http://a.com", alias="my-link")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.get_json()["code"], "my-link")
        again = self.shorten("http://b.com", alias="my-link")
        self.assertEqual(again.status_code, 409)
        # and the first link still resolves where it always did
        self.assertEqual(self.c.get("/my-link").headers["Location"], "http://a.com")

    def test_reserved_alias_cannot_shadow_a_route(self):
        self.assertEqual(self.shorten("http://a.com", alias="api").status_code, 400)
        # the real route still answers
        self.assertEqual(self.c.post("/api/shorten", json={"url": "http://b.com"}).status_code, 201)

    def test_unknown_code_is_404(self):
        self.assertEqual(self.c.get("/doesnotexist").status_code, 404)
        self.assertEqual(self.c.get("/api/stats/doesnotexist").status_code, 404)
        self.assertEqual(self.c.get("/s/doesnotexist").status_code, 404)

    def test_form_path_reports_errors_without_500(self):
        r = self.c.post("/", data={"url": "javascript:alert(1)"})
        self.assertEqual(r.status_code, 400)
        self.assertIn(b"Only http and https", r.data)

    def test_form_and_api_agree(self):
        r = self.c.post("/", data={"url": "example.org/x", "alias": "viaform"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.c.get("/viaform").headers["Location"], "http://example.org/x")

    def test_stats_page_renders_and_escapes(self):
        # a destination containing markup must not become live HTML on the page
        code = self.shorten('http://evil.com/?x=<script>alert(1)</script>').get_json()["code"]
        r = self.c.get("/s/" + code)
        self.assertEqual(r.status_code, 200)
        self.assertNotIn(b"<script>alert(1)</script>", r.data)
        self.assertIn(b"&lt;script&gt;", r.data)

    def test_shortening_this_service_is_refused(self):
        r = self.c.post("/api/shorten", json={"url": "http://localhost/abc"})
        self.assertEqual(r.status_code, 400)

    def test_missing_body_is_400_not_500(self):
        self.assertEqual(self.c.post("/api/shorten", json={}).status_code, 400)
        self.assertEqual(self.c.post("/api/shorten", data="notjson").status_code, 400)


if __name__ == "__main__":
    unittest.main(verbosity=2)
