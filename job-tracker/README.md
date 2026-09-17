# Application Tracker — capstone

Flask, SQLite and a dashboard in one app: full CRUD over job applications, with
a funnel, reply times and channel analytics computed from the database at
request time. This is Day 21 of the 21-day build, and it ties together the
database design, the analytics and the UI work from the rest of the repo.

## Run it

```bash
pip install -r requirements.txt
SEED=1 python3 app.py        # starts with 120 sample applications
python3 test_tracker.py      # 36 tests, stdlib unittest
```

Then open `http://127.0.0.1:5001` — applications list, per-application history,
and `/dashboard`. Everything is also available as JSON at `/api/analytics`.

## The design decision the whole thing turns on

An application's history is an **append-only log of stage events**, not a
`current_stage` column.

That sounds like over-engineering for a personal tracker until you try to build
the funnel. If an application is sitting at "offer", then `GROUP BY
current_stage` counts it once, under "offer" — so it does not appear in the
interview row, even though it obviously got through an interview. Every
application that moved on, or got rejected later, vanishes from the stage it
actually passed through.

Both versions are implemented, so the gap can be measured instead of asserted.
On the 120 seeded applications:

| Stage | Counted from the event log | `GROUP BY current_stage` |
| --- | --- | --- |
| applied | 120 | 97 |
| screen | 23 | 4 |
| interview | **9** | **1** |
| onsite | 4 | 0 |
| offer | 2 | 2 |

The naive funnel reports one interview where nine happened. It also reports
**more offers (2) than interviews (1)** — an impossible funnel, from the same
database, rendering without an error. That is the failure worth designing
against: not a crash, but a chart that looks fine and is wrong.

A test asserts the correct funnel never increases as it goes down the stages,
which is a property the naive one cannot satisfy.

## Two other places the obvious number is the wrong one

**Ghost rate excludes recent applications.** An application sent four days ago
has not been ignored, it just has not been answered yet. Counting it as "no
reply" means a burst of applying shows up as a collapse in response rate. The
rate is computed only over applications at least 30 days old, and the dashboard
says how many were excluded (21 of 120 here). Survivorship bias, in the
direction people usually forget.

**Reply time is a median.** Reply times are bounded below and unbounded above,
so one company answering after three months moves a mean and barely moves a
median. On this data the two are close (10.0 vs 10.3 days) — the median is used
because it does not depend on that staying true.

## A claim the data did not support

The by-source table originally said the channel producing the most applications
is rarely the one producing the most interviews. The seeded data says otherwise:
Job board leads on volume (39) **and** on raw interviews (4), so the note was
wrong on its own dashboard.

It now compares reply *rates*, which is both the accurate claim and the one
resting on real sample size:

| Source | Applications | Replied | Reply rate |
| --- | --- | --- | --- |
| Job board | 39 | 6 | 15% |
| LinkedIn | 37 | 5 | 14% |
| Company site | 18 | 4 | 22% |
| Referral | 14 | 5 | **36%** |
| Career fair | 12 | 3 | 25% |

Referrals reply at more than twice the rate of job boards while making up an
eighth of the volume. The interview column is left visible but not leaned on —
single-digit counts move several percentage points on one extra interview, and
the seed test was rewritten to assert reply rate for exactly that reason.

## Schema

```
companies     (id, name UNIQUE, industry)
applications  (id, company_id → companies, role, source, applied_on,
               current_stage, closed_on, outcome, notes)
stage_events  (id, application_id → applications, stage, occurred_on)
```

`applications.current_stage` exists only as a cache for cheap list rendering.
No analytic query reads it — every number comes from `stage_events`. The one
place it is allowed to be authoritative is deciding what badge to draw in a
table row.

`update_application` accepts a field allowlist, so a form post cannot set
`current_stage` or `id` and quietly desynchronise the cache from the log; a test
covers that.

## Tests

36 tests, stdlib `unittest`, no pytest needed. The ones that matter:

- the funnel counts every stage an application passed through
- the naive funnel disagrees, and can be internally impossible
- a correct funnel never increases down the stages
- a median is not a mean, checked against a deliberate outlier
- recent applications are excluded from the ghost rate
- seeded data is deterministic, and no event predates its own application
- company names render escaped, not executed
- acting on a missing application is 404, never 500
