"""Time each query with and without its candidate index, and print the plan.

Method, because a benchmark without one is decoration:

  * a fresh connection per timed run, so SQLite's own page cache does not carry
    results between runs
  * `REPEATS` runs per configuration, median reported -- the mean is hostage to
    one unlucky run
  * one warm-up run per configuration, discarded, so the OS page cache is in
    the same state for the indexed and unindexed timings
  * EXPLAIN QUERY PLAN captured for both, because the timing is only
    interesting once you can see which access path the planner chose
"""

from __future__ import annotations

import sqlite3
import statistics
import time

DB = "shop.db"
REPEATS = 15

QUERIES = {
    "revenue_by_month": (
        """SELECT substr(o.ordered_at,1,7) AS ym,
                  ROUND(SUM(i.quantity * i.unit_price), 2) AS revenue
             FROM orders o JOIN order_items i ON i.order_id = o.id
            WHERE o.status = 'paid'
            GROUP BY ym ORDER BY ym""",
        "CREATE INDEX idx_items_order ON order_items(order_id)",
    ),
    "one_customers_orders": (
        """SELECT id, ordered_at, status FROM orders
            WHERE customer_id = 8123 ORDER BY ordered_at""",
        "CREATE INDEX idx_orders_customer ON orders(customer_id)",
    ),
    "orders_in_a_quarter": (
        """SELECT COUNT(*) FROM orders
            WHERE ordered_at >= '2024-04-01' AND ordered_at < '2024-07-01'""",
        "CREATE INDEX idx_orders_date ON orders(ordered_at)",
    ),
    "all_paid_orders": (
        """SELECT COUNT(*), MIN(ordered_at), MAX(ordered_at)
             FROM orders WHERE status = 'paid'""",
        "CREATE INDEX idx_orders_status ON orders(status)",
    ),
    "top_products": (
        """SELECT p.name, SUM(i.quantity) AS units
             FROM order_items i JOIN products p ON p.id = i.product_id
            GROUP BY p.id ORDER BY units DESC LIMIT 10""",
        "CREATE INDEX idx_items_product ON order_items(product_id)",
    ),
}


def plan(sql: str) -> str:
    con = sqlite3.connect(DB)
    rows = con.execute("EXPLAIN QUERY PLAN " + sql).fetchall()
    con.close()
    return " / ".join(r[-1] for r in rows)


def time_ms(sql: str) -> tuple[float, float]:
    """Median and interquartile spread over REPEATS runs, warm-up discarded."""
    samples = []
    for i in range(REPEATS + 1):
        con = sqlite3.connect(DB)
        t0 = time.perf_counter()
        con.execute(sql).fetchall()
        dt = (time.perf_counter() - t0) * 1000
        con.close()
        if i:
            samples.append(dt)
    samples.sort()
    q1 = samples[len(samples) // 4]
    q3 = samples[3 * len(samples) // 4]
    return statistics.median(samples), q3 - q1


def drop_all() -> None:
    con = sqlite3.connect(DB)
    for (name,) in con.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'"
    ).fetchall():
        con.execute(f"DROP INDEX {name}")
    con.execute("ANALYZE sqlite_master")  # ensures sqlite_stat1 exists...
    con.execute("DELETE FROM sqlite_stat1")  # ...then empty it, so the planner
    con.commit()                             # is back to guessing
    con.close()


def run() -> list[tuple]:
    drop_all()
    out = []
    for name, (sql, create) in QUERIES.items():
        before_plan, (before, b_iqr) = plan(sql), time_ms(sql)
        con = sqlite3.connect(DB)
        con.execute(create)
        con.commit()
        con.close()
        after_plan, (after, a_iqr) = plan(sql), time_ms(sql)
        out.append((name, before, after, before_plan, after_plan, max(b_iqr, a_iqr)))
    return out


def main() -> None:
    rows = run()
    print(f"{'query':22} {'no index':>10} {'indexed':>10} {'change':>9}  verdict")
    print("-" * 72)
    for name, before, after, bp, ap, iqr in rows:
        change = (after - before) / before * 100
        delta = abs(after - before)
        if bp == ap:
            verdict = "plan unchanged -- noise"
        elif delta < iqr:
            verdict = "inside run-to-run spread"
        elif change > 0:
            verdict = "REGRESSION"
        else:
            verdict = "real win"
        print(f"{name:22} {before:9.2f}ms {after:9.2f}ms {change:+8.1f}%  {verdict}")
    print("\nA timing difference only counts when the plan changed and the gap clears\n"
          "the interquartile spread of the runs themselves.")

    print("\nplans:")
    for name, _, _, bp, ap, _ in rows:
        print(f"\n  {name}")
        print(f"    without: {bp}")
        print(f"    with:    {ap}")

    # Does ANALYZE rescue the regression? Asking is cheap; assuming is not.
    sql = QUERIES["all_paid_orders"][0]
    con = sqlite3.connect(DB)
    con.execute("ANALYZE")
    con.commit()
    stat = con.execute(
        "SELECT stat FROM sqlite_stat1 WHERE idx = 'idx_orders_status'"
    ).fetchone()[0]
    actual = con.execute("SELECT COUNT(*) FROM orders WHERE status='paid'").fetchone()[0]
    con.close()
    rows, per_value = (int(x) for x in stat.split()[:2])
    print("\nafter ANALYZE, all_paid_orders:")
    print(f"    sqlite_stat1: {stat!r} -- {rows} rows, {per_value} per distinct status")
    print(f"    actual matching rows: {actual} ({actual / rows:.1%} of the table)")
    print(f"    plan:  {plan(sql)}")
    print(f"    time:  {time_ms(sql)[0]:.2f}ms")

    forced = sql.replace("FROM orders", "FROM orders NOT INDEXED")
    covering = "SELECT COUNT(*) FROM orders WHERE status = 'paid'"
    print(f"    same query, NOT INDEXED (forced scan): {time_ms(forced)[0]:.2f}ms")
    print(f"    covering variant, COUNT(*) only:       {time_ms(covering)[0]:.2f}ms")


if __name__ == "__main__":
    main()
