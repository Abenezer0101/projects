# SQL Quick Reference

A compact cheat sheet for the SQL patterns used across these database projects, with a runnable example for each.

## Core clauses

```sql
SELECT col1, col2        -- what to return
FROM table               -- source
WHERE condition          -- filter rows (before grouping)
GROUP BY col             -- collapse into groups
HAVING agg_condition     -- filter groups (after aggregation)
ORDER BY col [ASC|DESC]  -- sort
LIMIT n;                 -- cap rows
```

## Joins

| Join | Keeps |
|---|---|
| `INNER JOIN` | only rows matching on both sides |
| `LEFT JOIN` | all left rows; NULLs where no right match |
| `SELF JOIN` | a table joined to itself (e.g. mutual follows, manager→report) |

```sql
-- Members and their open loans (LEFT keeps members with none)
SELECT m.full_name, l.id
FROM members m
LEFT JOIN loans l ON l.member_id = m.id AND l.returned_at IS NULL;
```

## Aggregates & grouping

```sql
SELECT category, COUNT(*) AS n, AVG(total_copies) AS avg_copies
FROM books
GROUP BY category
HAVING COUNT(*) > 1;
```
`COUNT` `SUM` `AVG` `MIN` `MAX`. Filter groups with `HAVING`, not `WHERE`.

## Subqueries

```sql
-- Scalar subquery in SELECT
SELECT title,
       (SELECT COUNT(*) FROM loans l JOIN copies c ON c.id=l.copy_id
        WHERE c.book_id = b.id) AS times_borrowed
FROM books b;

-- IN / EXISTS for membership tests
SELECT * FROM copies
WHERE id IN (SELECT copy_id FROM loans WHERE returned_at IS NULL);
```

## Window functions

Compute across a set of rows *without* collapsing them.

```sql
RANK()       OVER (ORDER BY score DESC)          -- 1,2,2,4 (ties skip)
DENSE_RANK() OVER (ORDER BY score DESC)          -- 1,2,2,3
ROW_NUMBER() OVER (PARTITION BY cat ORDER BY x)  -- per-group counter
SUM(amt)     OVER (ORDER BY d)                    -- running total
```

## Dates

```sql
DATEDIFF(due_date, borrowed_at)   -- days between
CURRENT_DATE, NOW()
DATE_ADD(borrowed_at, INTERVAL 14 DAY)
```

## Constraints (DDL)

```sql
PRIMARY KEY, FOREIGN KEY ... REFERENCES,
UNIQUE, NOT NULL, DEFAULT, CHECK (x <> y),
ON DELETE CASCADE   -- child rows die with the parent
```

## NULL handling

`NULL` is unknown: `x = NULL` is never true — use `IS NULL` / `IS NOT NULL`. `COALESCE(x, 0)` substitutes a default.
