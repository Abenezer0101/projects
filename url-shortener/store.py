"""SQLite storage for links and clicks.

The interesting part is code generation. Random 6-character base62 codes
collide -- not rarely, and not only when the table is nearly full. The
birthday bound says a 62^6 space (~56.8 billion) starts producing collisions
after only a few hundred thousand codes, and any single insert can collide at
any time.

The wrong fixes are common: SELECT-then-INSERT (a race: two requests can both
find the code free), or INSERT OR REPLACE (silently steals somebody else's
link). The right fix is to let the database be the authority -- a UNIQUE
constraint -- and retry on the conflict it raises.
"""

import secrets
import sqlite3
import string
from datetime import datetime, timezone

ALPHABET = string.ascii_letters + string.digits      # 62 symbols
CODE_LEN = 6
MAX_ATTEMPTS = 8

SCHEMA = """
CREATE TABLE IF NOT EXISTS links (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    code        TEXT    NOT NULL UNIQUE,
    url         TEXT    NOT NULL,
    created_at  TEXT    NOT NULL,
    custom      INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS clicks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    link_id     INTEGER NOT NULL REFERENCES links(id) ON DELETE CASCADE,
    clicked_at  TEXT    NOT NULL,
    referrer    TEXT,
    user_agent  TEXT
);
CREATE INDEX IF NOT EXISTS idx_clicks_link ON clicks(link_id);
CREATE INDEX IF NOT EXISTS idx_links_code  ON links(code);
"""


def connect(path):
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    return conn


def generate_code(n=CODE_LEN):
    """Cryptographically random, so codes cannot be walked by incrementing."""
    return "".join(secrets.choice(ALPHABET) for _ in range(n))


class CodeTaken(Exception):
    """A requested custom alias already exists."""


class OutOfCodes(Exception):
    """Every generation attempt collided -- effectively impossible, but not ignored."""


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def create_link(conn, url, alias=None):
    """Insert a link, letting the UNIQUE constraint settle any race.

    A SELECT-then-INSERT would let two concurrent requests both see a code as
    free and one of them lose its link. Here the database decides, and a
    generated code simply tries again.
    """
    if alias:
        try:
            cur = conn.execute(
                "INSERT INTO links (code, url, created_at, custom) VALUES (?,?,?,1)",
                (alias, url, now_iso()))
            conn.commit()
            return alias, cur.lastrowid
        except sqlite3.IntegrityError:
            raise CodeTaken(alias)

    for _ in range(MAX_ATTEMPTS):
        code = generate_code()
        try:
            cur = conn.execute(
                "INSERT INTO links (code, url, created_at, custom) VALUES (?,?,?,0)",
                (code, url, now_iso()))
            conn.commit()
            return code, cur.lastrowid
        except sqlite3.IntegrityError:
            continue                      # collided; draw another code
    raise OutOfCodes()


def find(conn, code):
    return conn.execute("SELECT * FROM links WHERE code = ?", (code,)).fetchone()


def record_click(conn, link_id, referrer=None, user_agent=None):
    conn.execute(
        "INSERT INTO clicks (link_id, clicked_at, referrer, user_agent) VALUES (?,?,?,?)",
        (link_id, now_iso(), referrer, user_agent))
    conn.commit()


def recent_links(conn, limit=10):
    """Recent links with their click counts, counted rather than stored.

    A clicks column on `links` would be a second source of truth; a LEFT JOIN
    means the number shown is always the number of rows that exist.
    """
    return conn.execute("""
        SELECT l.code, l.url, l.created_at, l.custom, COUNT(c.id) AS clicks
        FROM links l LEFT JOIN clicks c ON c.link_id = l.id
        GROUP BY l.id
        ORDER BY l.id DESC
        LIMIT ?""", (limit,)).fetchall()


def link_stats(conn, code):
    row = find(conn, code)
    if row is None:
        return None
    total = conn.execute("SELECT COUNT(*) AS n FROM clicks WHERE link_id = ?",
                         (row["id"],)).fetchone()["n"]
    by_day = conn.execute("""
        SELECT substr(clicked_at, 1, 10) AS day, COUNT(*) AS n
        FROM clicks WHERE link_id = ?
        GROUP BY day ORDER BY day""", (row["id"],)).fetchall()
    referrers = conn.execute("""
        SELECT COALESCE(NULLIF(referrer, ''), 'direct') AS src, COUNT(*) AS n
        FROM clicks WHERE link_id = ?
        GROUP BY src ORDER BY n DESC LIMIT 8""", (row["id"],)).fetchall()
    return {
        "code": row["code"], "url": row["url"], "created_at": row["created_at"],
        "custom": bool(row["custom"]), "clicks": total,
        "by_day": [dict(r) for r in by_day],
        "referrers": [dict(r) for r in referrers],
    }


def totals(conn):
    return {
        "links": conn.execute("SELECT COUNT(*) n FROM links").fetchone()["n"],
        "clicks": conn.execute("SELECT COUNT(*) n FROM clicks").fetchone()["n"],
    }
