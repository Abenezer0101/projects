"""Schema, seeding and analytics for the application tracker.

The design decision the whole project turns on: an application's history is an
append-only log of stage events, not a single `current_stage` column.

A tracker that only stores the current stage cannot answer the one question
worth asking. If an application is sitting at "offer", a GROUP BY current_stage
counts it once, under "offer" -- so it does not appear in the interview row,
even though it obviously got through an interview. Every funnel built that way
undercounts the early stages, and the conversion rates that fall out of it are
not slightly off, they are meaningless.

Both versions are implemented here. `funnel()` is correct; `funnel_naive()` is
the mistake, kept so the difference can be measured rather than asserted.
"""

import random
import sqlite3
from datetime import date, timedelta

STAGES = ["applied", "screen", "interview", "onsite", "offer"]
TERMINAL = ["rejected", "withdrawn", "ghosted", "accepted"]
SOURCES = ["Referral", "Company site", "LinkedIn", "Job board", "Career fair"]

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS companies (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    name     TEXT NOT NULL UNIQUE,
    industry TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS applications (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    role       TEXT NOT NULL,
    source     TEXT NOT NULL,
    applied_on TEXT NOT NULL,
    -- a cache of the latest stage_event, for cheap listing. It is NEVER the
    -- source of truth for analytics; every number comes from stage_events.
    current_stage TEXT NOT NULL DEFAULT 'applied',
    closed_on  TEXT,
    outcome    TEXT,
    notes      TEXT
);

CREATE TABLE IF NOT EXISTS stage_events (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    application_id INTEGER NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    stage          TEXT NOT NULL,
    occurred_on    TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_events_app   ON stage_events(application_id);
CREATE INDEX IF NOT EXISTS idx_events_stage ON stage_events(stage);
CREATE INDEX IF NOT EXISTS idx_apps_company ON applications(company_id);
"""


def connect(path=":memory:"):
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


# ------------------------------------------------------------------ writes

def add_company(conn, name, industry):
    cur = conn.execute("INSERT OR IGNORE INTO companies (name, industry) VALUES (?,?)",
                       (name, industry))
    conn.commit()
    if cur.lastrowid:
        return cur.lastrowid
    return conn.execute("SELECT id FROM companies WHERE name = ?", (name,)).fetchone()["id"]


def add_application(conn, company_id, role, source, applied_on, notes=None):
    cur = conn.execute("""INSERT INTO applications
        (company_id, role, source, applied_on, current_stage, notes)
        VALUES (?,?,?,?,'applied',?)""", (company_id, role, source, applied_on, notes))
    app_id = cur.lastrowid
    # the 'applied' event is written with the application: an application that
    # exists has, by definition, reached the applied stage
    conn.execute("INSERT INTO stage_events (application_id, stage, occurred_on) VALUES (?,?,?)",
                 (app_id, "applied", applied_on))
    conn.commit()
    return app_id


def advance(conn, app_id, stage, occurred_on):
    """Record reaching a stage. Append-only: history is never rewritten."""
    if stage not in STAGES and stage not in TERMINAL:
        raise ValueError(f"unknown stage: {stage}")
    conn.execute("INSERT INTO stage_events (application_id, stage, occurred_on) VALUES (?,?,?)",
                 (app_id, stage, occurred_on))
    if stage in TERMINAL:
        conn.execute("UPDATE applications SET current_stage=?, closed_on=?, outcome=? WHERE id=?",
                     (stage, occurred_on, stage, app_id))
    else:
        conn.execute("UPDATE applications SET current_stage=? WHERE id=?", (stage, app_id))
    conn.commit()


def update_application(conn, app_id, **fields):
    allowed = {"role", "source", "applied_on", "notes"}
    sets = {k: v for k, v in fields.items() if k in allowed}
    if not sets:
        return
    conn.execute(f"UPDATE applications SET {', '.join(f'{k}=?' for k in sets)} WHERE id=?",
                 (*sets.values(), app_id))
    conn.commit()


def delete_application(conn, app_id):
    conn.execute("DELETE FROM stage_events WHERE application_id=?", (app_id,))
    conn.execute("DELETE FROM applications WHERE id=?", (app_id,))
    conn.commit()


# ------------------------------------------------------------------- reads

def list_applications(conn, stage=None, source=None, q=None):
    sql = """SELECT a.*, c.name AS company, c.industry,
                    (SELECT COUNT(*) FROM stage_events e WHERE e.application_id = a.id) AS events
             FROM applications a JOIN companies c ON c.id = a.company_id WHERE 1=1"""
    args = []
    if stage:
        sql += " AND a.current_stage = ?"; args.append(stage)
    if source:
        sql += " AND a.source = ?"; args.append(source)
    if q:
        sql += " AND (c.name LIKE ? OR a.role LIKE ?)"; args += [f"%{q}%", f"%{q}%"]
    sql += " ORDER BY date(a.applied_on) DESC, a.id DESC"
    return conn.execute(sql, args).fetchall()


def get_application(conn, app_id):
    row = conn.execute("""SELECT a.*, c.name AS company, c.industry
                          FROM applications a JOIN companies c ON c.id = a.company_id
                          WHERE a.id = ?""", (app_id,)).fetchone()
    if row is None:
        return None
    events = conn.execute("""SELECT stage, occurred_on,
                                    CAST(julianday(occurred_on) - julianday(?) AS INTEGER) AS days_in
                             FROM stage_events
                             WHERE application_id = ? ORDER BY date(occurred_on), id""",
                          (row["applied_on"], app_id)).fetchall()
    return {"app": dict(row), "events": [dict(e) for e in events]}


# --------------------------------------------------------------- analytics

def funnel(conn):
    """How many applications EVER reached each stage.

    Counts distinct applications in the event log, so an application now at
    'offer' is still counted in 'interview' -- because it went through one.
    """
    rows = conn.execute("""
        SELECT stage, COUNT(DISTINCT application_id) AS n
        FROM stage_events WHERE stage IN (%s)
        GROUP BY stage""" % ",".join("?" * len(STAGES)), STAGES).fetchall()
    counts = {r["stage"]: r["n"] for r in rows}
    out, prev = [], None
    for s in STAGES:
        n = counts.get(s, 0)
        out.append({"stage": s, "n": n,
                    "from_prev": None if prev in (None, 0) else n / prev,
                    "from_top": None if not counts.get("applied") else n / counts["applied"]})
        prev = n
    return out


def funnel_naive(conn):
    """The mistake: counting where applications are NOW, not where they have been."""
    rows = conn.execute("""SELECT current_stage AS stage, COUNT(*) AS n
                           FROM applications GROUP BY current_stage""").fetchall()
    counts = {r["stage"]: r["n"] for r in rows}
    return [{"stage": s, "n": counts.get(s, 0)} for s in STAGES]


def response_times(conn):
    """Days from applying to the first reply. Reports median, mean and p90.

    The median leads because reply times are bounded below and unbounded
    above: one company answering after three months moves a mean and barely
    moves a median. On the seeded data the two happen to sit close together --
    the median is used because it does not depend on that staying true.
    """
    rows = conn.execute("""
        WITH first_reply AS (
            SELECT e.application_id,
                   MIN(julianday(e.occurred_on) - julianday(a.applied_on)) AS days
            FROM stage_events e JOIN applications a ON a.id = e.application_id
            WHERE e.stage <> 'applied'
            GROUP BY e.application_id)
        SELECT days FROM first_reply WHERE days >= 0 ORDER BY days""").fetchall()
    days = [r["days"] for r in rows]
    if not days:
        return {"n": 0, "median": None, "mean": None, "p90": None}
    mid = len(days) // 2
    median = days[mid] if len(days) % 2 else (days[mid - 1] + days[mid]) / 2
    return {"n": len(days), "median": median,
            "mean": sum(days) / len(days),
            "p90": days[min(len(days) - 1, int(round(0.9 * (len(days) - 1))))]}


def ghost_rate(conn, today, silence_days=30):
    """Share of applications that got no reply at all.

    Applications submitted in the last `silence_days` are excluded: they have
    not had time to answer yet, and counting them as ghosted makes a recent
    burst of applying look like a collapse in response rate. This is
    survivorship handled in the direction people usually forget.
    """
    row = conn.execute("""
        SELECT
          COUNT(*) AS eligible,
          SUM(CASE WHEN (SELECT COUNT(*) FROM stage_events e
                         WHERE e.application_id = a.id AND e.stage <> 'applied') = 0
                   THEN 1 ELSE 0 END) AS silent
        FROM applications a
        WHERE julianday(?) - julianday(a.applied_on) >= ?""", (today, silence_days)).fetchone()
    eligible = row["eligible"] or 0
    silent = row["silent"] or 0
    total = conn.execute("SELECT COUNT(*) n FROM applications").fetchone()["n"]
    return {"eligible": eligible, "silent": silent, "excluded_too_recent": total - eligible,
            "rate": (silent / eligible) if eligible else None}


def by_source(conn):
    """Which channel actually converts, not just which produces volume."""
    return [dict(r) for r in conn.execute("""
        SELECT a.source,
               COUNT(*) AS applications,
               SUM(CASE WHEN EXISTS (SELECT 1 FROM stage_events e
                     WHERE e.application_id=a.id AND e.stage<>'applied') THEN 1 ELSE 0 END) AS replies,
               SUM(CASE WHEN EXISTS (SELECT 1 FROM stage_events e
                     WHERE e.application_id=a.id AND e.stage='interview') THEN 1 ELSE 0 END) AS interviews,
               SUM(CASE WHEN EXISTS (SELECT 1 FROM stage_events e
                     WHERE e.application_id=a.id AND e.stage='offer') THEN 1 ELSE 0 END) AS offers
        FROM applications a GROUP BY a.source ORDER BY applications DESC""").fetchall()]


def monthly(conn):
    return [dict(r) for r in conn.execute("""
        SELECT substr(applied_on,1,7) AS month, COUNT(*) AS n
        FROM applications GROUP BY month ORDER BY month""").fetchall()]


def totals(conn, today):
    n = conn.execute("SELECT COUNT(*) n FROM applications").fetchone()["n"]
    open_n = conn.execute("SELECT COUNT(*) n FROM applications WHERE closed_on IS NULL").fetchone()["n"]
    offers = conn.execute("""SELECT COUNT(DISTINCT application_id) n FROM stage_events
                             WHERE stage='offer'""").fetchone()["n"]
    return {"applications": n, "open": open_n, "offers": offers,
            "companies": conn.execute("SELECT COUNT(*) n FROM companies").fetchone()["n"],
            "ghost": ghost_rate(conn, today)}


# ---------------------------------------------------------------- seeding

COMPANY_POOL = [
    ("Northwind Analytics", "Software"), ("Cobalt Health", "Healthcare"),
    ("Piedmont Logistics", "Logistics"), ("Ardent Bank", "Finance"),
    ("Glasswing Media", "Media"), ("Verity Insurance", "Insurance"),
    ("Kestrel Robotics", "Manufacturing"), ("Bluegrass Retail", "Retail"),
    ("Summit Energy", "Energy"), ("Harbor Point Games", "Software"),
    ("Lattice Biotech", "Healthcare"), ("Ironwood Consulting", "Consulting"),
    ("Cedar Grove Foods", "Retail"), ("Tessellate Labs", "Software"),
    ("Anchor Freight", "Logistics"), ("Marigold Travel", "Travel"),
]
ROLE_POOL = ["Data Analyst", "Business Analyst", "Junior Data Engineer",
             "Reporting Analyst", "BI Developer", "Operations Analyst",
             "Data Analyst Intern", "Analytics Associate"]


def seed(conn, n=120, seed_value=20260917, today=None):
    """Deterministic sample data, so every number in the README is reproducible.

    The shape is deliberately realistic: most applications never get a reply,
    each stage loses most of what entered it, and referrals convert far better
    than job boards.
    """
    rnd = random.Random(seed_value)
    today = date.fromisoformat(today) if today else date(2026, 9, 17)

    for name, ind in COMPANY_POOL:
        add_company(conn, name, ind)
    company_ids = [r["id"] for r in conn.execute("SELECT id FROM companies").fetchall()]

    # a referral is far more likely to get a human to read the application
    reply_odds = {"Referral": 0.62, "Career fair": 0.34, "Company site": 0.27,
                  "LinkedIn": 0.19, "Job board": 0.12}
    advance_odds = {"screen": 0.55, "interview": 0.45, "onsite": 0.40}

    for _ in range(n):
        source = rnd.choices(SOURCES, weights=[10, 14, 30, 34, 12])[0]
        applied = today - timedelta(days=rnd.randint(0, 210))
        app_id = add_application(conn, rnd.choice(company_ids), rnd.choice(ROLE_POOL),
                                 source, applied.isoformat())
        cur = applied
        if rnd.random() >= reply_odds[source]:
            continue                                  # never heard back
        for nxt in ("screen", "interview", "onsite", "offer"):
            gap = rnd.randint(3, 18) if nxt == "screen" else rnd.randint(4, 21)
            cur = cur + timedelta(days=gap)
            if cur > today:
                break                                 # still in flight
            advance(conn, app_id, nxt, cur.isoformat())
            if nxt == "offer":
                break
            if rnd.random() >= advance_odds[nxt]:
                # rejected after reaching this stage
                rej = cur + timedelta(days=rnd.randint(2, 14))
                if rej <= today:
                    advance(conn, app_id, "rejected", rej.isoformat())
                break
    return conn
