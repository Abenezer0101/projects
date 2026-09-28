# Query planner lab

An index is not a performance feature. It is a bet the planner makes on your
behalf, and this measures a case where the bet loses.

The Day 3 e-commerce schema, rebuilt in SQLite at a size where the planner's
choices are visible: 20,000 customers, 120,000 orders, 299,834 line items,
generated from a fixed seed so every number below reproduces.

```
python3 build_db.py shop.db     # ~2s, builds a 12 MB database
python3 lab.py                  # times five queries with and without an index
```

## Result

Each query is timed with no index and then with one candidate index, 15 runs
per configuration on a fresh connection, warm-up discarded, median reported.

| query | no index | indexed | change | verdict |
| --- | ---: | ---: | ---: | --- |
| revenue_by_month | 183.24ms | 179.90ms | −1.8% | plan unchanged — noise |
| one_customers_orders | 5.04ms | 0.15ms | −97.1% | real win |
| orders_in_a_quarter | 7.99ms | 0.45ms | −94.3% | real win |
| all_paid_orders | 13.39ms | 18.60ms | **+39.0%** | regression |
| top_products | 261.32ms | 297.85ms | +14.0% | inside run-to-run spread |

Two of those five apparent changes are not results. `revenue_by_month` got an
index the planner never used — its plan is byte-identical before and after, so
the −1.8% is the machine breathing. `top_products` did change plan, but the
gap does not clear the interquartile spread of its own runs, so on this
evidence it is unproven rather than real. A benchmark that reports five
findings where there are three is worse than one that reports nothing.

## The index that makes things slower

```sql
SELECT COUNT(*), MIN(ordered_at), MAX(ordered_at)
  FROM orders WHERE status = 'paid';
```

```
without: SCAN orders
with:    SEARCH orders USING INDEX idx_orders_status (status=?)
```

107,896 of the 120,000 orders are `paid` — 89.9%. Seeking an index to find
almost the whole table, then following 107,896 rowids back to the main B-tree
in index order rather than storage order, is strictly more work than reading
the table start to finish. Forcing the scan back with `NOT INDEXED` returns
the query to 16.76ms against the index's 26.34ms.

The mechanism is the rowid lookups, not the index itself. Ask only for
`COUNT(*)` and the same index becomes *covering* — every column the query
needs lives in the index, no trips to the table — and the query drops to
5.25ms, three times faster than the scan. The identical index is a 3× win or
a 1.6× loss depending on which columns you select.

## ANALYZE does not fix it

The obvious next move is to give the planner statistics. It does not help, and
the reason is worth knowing:

```
sqlite_stat1: '120000 40000'  -- 120000 rows, 40000 per distinct status
actual matching rows: 107896 (89.9% of the table)
```

`ANALYZE` stores one number per index: the *mean* rows per distinct value.
There are three statuses, so it records 120000/3 = 40000 and the planner
believes `status = 'paid'` returns a third of the table. The true answer is
2.7× that. SQLite keeps no per-value histogram, so a skewed column is
mis-estimated even with fully current statistics, and the plan does not
change after `ANALYZE`.

That is the actual lesson. The planner was not stale or uninformed. It was
correctly applying a statistic that cannot represent this data.

## What to do about it

Drop the index if nothing needs it. Keep it and add the selected columns to
make it covering if something does. Or pin the plan with `NOT INDEXED` and
leave a comment saying why, which is the honest option when the distribution
is known to be lopsided and unlikely to change.

## Method notes

A fresh connection per timed run, so SQLite's page cache does not carry
results forward. One discarded warm-up per configuration so the OS page cache
is in the same state for both sides. Median of 15, not mean — one unlucky run
should not move the answer. A change is only reported as real when the plan
actually changed *and* the gap clears the interquartile spread of the runs.
