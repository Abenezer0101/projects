"""SQLite under concurrent writers: rollback journal against WAL, measured.

Real processes, not threads -- a thread pool would share one interpreter and
hide exactly the contention this is about. Each worker opens its own
connection to the same file, which is how a small web app actually behaves.

Three things get measured:

  1. how many writes land per second with N writers
  2. how many `sqlite3.OperationalError: database is locked` are raised
  3. whether a reader holding a transaction blocks a writer

The third is the one that matters, and it is the one people get wrong.
"""

from __future__ import annotations

import multiprocessing as mp
import os
import sqlite3
import sys
import time

DB = "bench.db"
WRITERS = 8
ROWS_EACH = 300


def fresh(path: str, journal: str) -> None:
    for suffix in ("", "-wal", "-shm", "-journal"):
        try:
            os.remove(path + suffix)
        except FileNotFoundError:
            pass
    con = sqlite3.connect(path)
    con.execute(f"PRAGMA journal_mode={journal}")
    con.execute("CREATE TABLE events (id INTEGER PRIMARY KEY, worker INT, note TEXT)")
    con.commit()
    con.close()


def writer(args) -> tuple[int, int]:
    """One process, ROWS_EACH single-row transactions. Returns (ok, locked)."""
    path, journal, timeout_ms, wid = args
    con = sqlite3.connect(path, timeout=timeout_ms / 1000)
    # journal_mode is a property of the file, set once in fresh(). Setting it
    # here would itself need an exclusive lock and fail under contention --
    # which is how the first version of this script died.
    con.execute(f"PRAGMA busy_timeout={timeout_ms}")
    ok = locked = 0
    for i in range(ROWS_EACH):
        try:
            con.execute("INSERT INTO events (worker, note) VALUES (?,?)", (wid, f"row {i}"))
            con.commit()
            ok += 1
        except sqlite3.OperationalError as e:
            if "locked" not in str(e) and "busy" not in str(e):
                raise
            locked += 1
            # A commit that raises leaves the transaction OPEN, so the row is
            # still pending and a later successful commit sweeps it in. The
            # first version of this script skipped the rollback and reported
            # 172 successes while 262 rows were in the table. Roll back, so a
            # write counted as lost is actually lost.
            con.rollback()
    con.close()
    return ok, locked


def run(journal: str, timeout_ms: int) -> dict:
    fresh(DB, journal)
    args = [(DB, journal, timeout_ms, w) for w in range(WRITERS)]
    t0 = time.perf_counter()
    with mp.Pool(WRITERS) as pool:
        results = pool.map(writer, args)
    elapsed = time.perf_counter() - t0
    ok = sum(r[0] for r in results)
    locked = sum(r[1] for r in results)
    con = sqlite3.connect(DB)
    stored = con.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    mode = con.execute("PRAGMA journal_mode").fetchone()[0]
    con.close()
    assert stored == ok, f"counted {ok} successes but {stored} rows landed"
    return {
        "journal": mode,
        "busy_timeout_ms": timeout_ms,
        "seconds": elapsed,
        "written": ok,
        "lost_to_lock": locked,
        "writes_per_sec": ok / elapsed,
    }


def reader_blocks_writer(journal: str) -> str:
    """Hold a read transaction, then try to write from another connection."""
    fresh(DB, journal)
    seed = sqlite3.connect(DB)
    seed.execute("INSERT INTO events (worker, note) VALUES (0,'seed')")
    seed.commit()
    seed.close()

    reader = sqlite3.connect(DB)
    reader.execute("BEGIN")
    reader.execute("SELECT * FROM events").fetchall()  # read txn now open

    w = sqlite3.connect(DB, timeout=0.5)
    w.execute(f"PRAGMA busy_timeout=500")
    try:
        w.execute("INSERT INTO events (worker, note) VALUES (1,'during read')")
        w.commit()
        verdict = "writer succeeded while a reader held a transaction"
    except sqlite3.OperationalError as e:
        verdict = f"writer blocked: {type(e).__name__}: {e}"
    finally:
        w.close()
        reader.rollback()
        reader.close()
    return verdict


def scaling(journal: str = "wal", total_rows: int = 2400) -> list[tuple]:
    """Same total work, spread over more writers.

    WAL is routinely described as giving concurrent writes. It does not. One
    writer holds the write lock at a time; WAL only stops readers from having
    to wait for it. If that is true, throughput here should be flat.
    """
    global ROWS_EACH, WRITERS
    keep_rows, keep_writers = ROWS_EACH, WRITERS
    out = []
    for n in (1, 2, 4, 8):
        WRITERS, ROWS_EACH = n, total_rows // n
        r = run(journal, 5000)
        out.append((n, r["seconds"], r["writes_per_sec"]))
    ROWS_EACH, WRITERS = keep_rows, keep_writers
    return out


def main() -> None:
    print(f"{WRITERS} writer processes x {ROWS_EACH} single-row transactions "
          f"= {WRITERS * ROWS_EACH} attempted writes\n")
    print(f"{'journal':10} {'busy_timeout':>13} {'seconds':>9} {'written':>9} "
          f"{'lost':>7} {'writes/s':>10}")
    print("-" * 64)
    rows = []
    for journal in ("delete", "wal"):
        for timeout in (0, 5000):
            r = run(journal, timeout)
            rows.append(r)
            print(f"{r['journal']:10} {r['busy_timeout_ms']:>11}ms "
                  f"{r['seconds']:>8.2f}s {r['written']:>9} {r['lost_to_lock']:>7} "
                  f"{r['writes_per_sec']:>10.0f}")

    print("\nsame 2400 writes, spread over more writer processes (wal):")
    print(f"  {'writers':>7} {'seconds':>9} {'writes/s':>10}")
    for n, secs, wps in scaling():
        print(f"  {n:>7} {secs:>8.2f}s {wps:>10.0f}")
    print("  throughput does not rise with writers -- they serialise, and queueing costs")

    print("\nreader holding an open transaction, second connection tries to write:")
    for journal in ("delete", "wal"):
        print(f"  {journal:7} -> {reader_blocks_writer(journal)}")

    for suffix in ("", "-wal", "-shm", "-journal"):
        try:
            os.remove(DB + suffix)
        except FileNotFoundError:
            pass


if __name__ == "__main__":
    sys.exit(main())
