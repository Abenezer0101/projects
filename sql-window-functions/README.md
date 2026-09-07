# SQL Window-Functions Playground

Seven worked examples of SQL window functions on one small sales table — the analytics patterns that separate "can write `GROUP BY`" from "can do reporting SQL." Each query isolates one concept.

## Why window functions

`GROUP BY` collapses rows; a window function computes across a set of rows **while keeping every row**. That's what lets you show a sale *and* its running total on the same line.

```sql
func(...) OVER (PARTITION BY col ORDER BY col frame)
```

## The seven patterns (`sql/02_windows.sql`)

| # | Function | Answers |
|---|---|---|
| 1 | `SUM() OVER (ORDER BY)` | running total per rep |
| 2 | `RANK` / `DENSE_RANK` | rank reps by total sales |
| 3 | `ROW_NUMBER` | top sale per region (dedupe to 1 row/group) |
| 4 | `LAG` | period-over-period change |
| 5 | `SUM()/SUM(SUM()) OVER` | share of region total (%) |
| 6 | `NTILE(2)` | split into performance tiers |
| 7 | `AVG() OVER (ROWS 2 PRECEDING)` | 3-row moving average |

## Verified output

Computed in SQLite before commit:
- **Ranking:** Chloe $5,400 (1), Amara $4,100 (2), Ben $4,000 (3), Diego $2,900 (4)
- **Top sale per region:** East → Amara $1,500; West → Chloe $2,000
- **Share of region:** East is near-even (Amara 50.6% / Ben 49.4%); West is concentrated (Chloe 65.1% / Diego 34.9%)
- **NTILE tiers:** Chloe & Amara → tier 1; Ben & Diego → tier 2
- Amara's running total climbs 1200 → 2000 → 3500 → 4100 across her four sales

## Run

```bash
mysql -u root -p < sql/01_setup.sql       # creates + seeds sales_wf
mysql -u root -p sales_wf < sql/02_windows.sql
```
Also runs on SQLite 3.25+ (drop the `CREATE DATABASE`/`USE` lines).

## Skills

`PARTITION BY` / `ORDER BY` / frame clauses, ranking vs. numbering, `LAG`/`LEAD`, nested aggregate windows for share-of-total, `NTILE` bucketing, moving averages.
