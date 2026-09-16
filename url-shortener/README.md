# URL Shortener

A working Flask + SQLite backend: shorten a link, follow it, and see real click
analytics. It is a small program with a large attack surface, because its entire
job is to take a string from a stranger and later send somebody else to it.

## Run it

```bash
pip install -r requirements.txt
python3 app.py                 # http://127.0.0.1:5000
python3 test_shortener.py      # 44 tests, stdlib unittest
python3 collision_study.py     # the measurement below
```

## The three things that actually bite

**Open redirect.** `javascript:alert(1)` and `data:text/html,<script>…</script>`
are perfectly valid URLs. Store one, emit it in a `Location` header or an
`href`, and the service becomes an XSS delivery mechanism. Only `http` and
`https` survive, the check runs *after* normalization so a default scheme can
never smuggle one through, and control characters are rejected because
`java\tscript:` is stripped back into a working scheme by some parsers.
Credentials are refused too — `http://google.com@evil.com` reads as "google.com"
to a human.

**Aliases that shadow routes.** The app serves its own routes off the root, so a
custom alias of `api` or `static` would shadow them and break the service for
everyone. Reserved words are rejected, and a test asserts the real `/api` route
still answers afterwards.

**Collisions and races.** Random codes collide. The two common fixes are both
wrong: `SELECT`-then-`INSERT` is a race where two requests can each find a code
free, and `INSERT OR REPLACE` silently steals somebody else's link. The database
is the authority here — a `UNIQUE` constraint — and a generated code simply
retries on the conflict.

## Measuring the collision rate

`collision_study.py` verifies the birthday approximation against simulation at
short code lengths, where collisions are easy to observe, then applies the
verified formula to the shipped 6-character code.

| Code length | Key space | Codes drawn | Collisions observed | Model predicts |
| --- | --- | --- | --- | --- |
| 2 | 3,844 | 500 | 30.6 | 32.5 |
| 3 | 238,328 | 3,000 | 19.2 | 18.9 |
| 4 | 14,776,336 | 20,000 | 13.9 | 13.5 |

The model holds, so applying it to base62⁶ (56,800,235,584 codes):

| Links stored | Chance the next insert collides | Collisions expected so far |
| --- | --- | --- |
| 100,000 | 0.00018% | 0.1 |
| 1,000,000 | 0.0018% | **8.8** |
| 10,000,000 | 0.018% | 880 |

A service with a million links will already have hit about nine collisions. The
retry loop fires almost never, and is still mandatory — the alternative when it
does fire is a 500 or a silently stolen link.

## The race, actually run

`test_concurrent_inserts_of_one_alias_yield_exactly_one_winner` starts eight
threads on a shared in-memory database, holds them at a barrier, and releases
them at the same alias. The outcome is worth stating precisely rather than
rounding off: one thread wins, two are rejected by the `UNIQUE` constraint, and
five get `SQLITE_BUSY` because SQLite serializes writers. Exactly one row
exists, and no link is overwritten. SQLite's write lock does part of the work
here — the constraint is what makes the guarantee hold regardless.

## Other details worth the trouble

Redirects are **302, not 301**. A permanent redirect is cached by the browser,
so the second click never reaches the server and the analytics silently flatten.

Click counts are `COUNT(*)` over a `clicks` table via a `LEFT JOIN`, never a
counter column on `links`. A stored counter is a second source of truth that
drifts; a join means the number shown is the number of rows that exist. The
`LEFT` matters — an inner join would hide every link that has never been clicked.

Codes come from `secrets`, not `random`, so they cannot be walked by
incrementing and guessed.

## API

| Method | Route | Purpose |
| --- | --- | --- |
| `POST` | `/api/shorten` | `{"url": "...", "alias": "optional"}` → `201` with `code` and `short_url` |
| `GET` | `/<code>` | `302` to the destination, recording the click |
| `GET` | `/s/<code>` | Stats page: clicks by day and by referrer |
| `GET` | `/api/stats/<code>` | The same as JSON |

Errors are `400` for a rejected URL or alias, `409` for a taken alias, `404` for
an unknown code — never a 500, which a test asserts for empty and non-JSON bodies.
