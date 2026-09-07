-- Each query isolates one window-function pattern. Read top to bottom.
USE sales_wf;

-- 1. RUNNING TOTAL of sales per rep, ordered by date.
--    The frame defaults to start-of-partition → current row.
SELECT rep, sale_date, amount,
       SUM(amount) OVER (PARTITION BY rep ORDER BY sale_date) AS running_total
FROM sales
ORDER BY rep, sale_date;

-- 2. RANK reps by total sales (aggregate first, then rank).
SELECT rep,
       SUM(amount) AS total,
       RANK()       OVER (ORDER BY SUM(amount) DESC) AS rnk,
       DENSE_RANK() OVER (ORDER BY SUM(amount) DESC) AS dense_rnk
FROM sales
GROUP BY rep
ORDER BY total DESC;

-- 3. TOP SALE PER REGION using ROW_NUMBER in a subquery.
SELECT region, rep, sale_date, amount
FROM (
  SELECT region, rep, sale_date, amount,
         ROW_NUMBER() OVER (PARTITION BY region ORDER BY amount DESC) AS rn
  FROM sales
) t
WHERE rn = 1;

-- 4. MONTH-OVER-MONTH change per rep with LAG.
SELECT rep, sale_date, amount,
       LAG(amount) OVER (PARTITION BY rep ORDER BY sale_date) AS prev_amount,
       amount - LAG(amount) OVER (PARTITION BY rep ORDER BY sale_date) AS delta
FROM sales
ORDER BY rep, sale_date;

-- 5. SHARE OF REGION TOTAL — amount as % of the rep's region revenue.
SELECT rep, region, SUM(amount) AS rep_total,
       ROUND(100 * SUM(amount) / SUM(SUM(amount)) OVER (PARTITION BY region), 1) AS pct_of_region
FROM sales
GROUP BY rep, region
ORDER BY region, pct_of_region DESC;

-- 6. NTILE — split reps into 2 performance tiers by total sales.
SELECT rep, total, NTILE(2) OVER (ORDER BY total DESC) AS tier
FROM (SELECT rep, SUM(amount) AS total FROM sales GROUP BY rep) s;

-- 7. 3-ROW MOVING AVERAGE per rep (current + 2 preceding).
SELECT rep, sale_date, amount,
       ROUND(AVG(amount) OVER (
         PARTITION BY rep ORDER BY sale_date
         ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 0) AS moving_avg_3
FROM sales
ORDER BY rep, sale_date;
