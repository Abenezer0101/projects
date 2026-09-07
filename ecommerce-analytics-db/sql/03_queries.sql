-- E-commerce analytics. Revenue counts PAID orders only.
USE shop;

-- Q1. Total revenue and Average Order Value (AOV), paid orders only.
SELECT ROUND(SUM(line),2) AS revenue,
       COUNT(DISTINCT order_id) AS paid_orders,
       ROUND(SUM(line)/COUNT(DISTINCT order_id),2) AS aov
FROM (
  SELECT oi.order_id, oi.quantity*oi.unit_price AS line
  FROM order_items oi
  JOIN orders o ON o.id = oi.order_id
  WHERE o.status = 'paid'
) t;

-- Q2. Revenue by product category (paid only), ranked.
SELECT p.category, ROUND(SUM(oi.quantity*oi.unit_price),2) AS revenue
FROM order_items oi
JOIN orders o   ON o.id = oi.order_id AND o.status='paid'
JOIN products p ON p.id = oi.product_id
GROUP BY p.category
ORDER BY revenue DESC;

-- Q3. Top customers by lifetime spend (paid only).
SELECT c.full_name, c.country,
       ROUND(SUM(oi.quantity*oi.unit_price),2) AS spend
FROM customers c
JOIN orders o     ON o.customer_id = c.id AND o.status='paid'
JOIN order_items oi ON oi.order_id = o.id
GROUP BY c.id, c.full_name, c.country
ORDER BY spend DESC;

-- Q4. Best-selling products by units and revenue.
SELECT p.name, SUM(oi.quantity) AS units,
       ROUND(SUM(oi.quantity*oi.unit_price),2) AS revenue
FROM order_items oi
JOIN orders o   ON o.id = oi.order_id AND o.status='paid'
JOIN products p ON p.id = oi.product_id
GROUP BY p.id, p.name
ORDER BY units DESC;

-- Q5. Monthly revenue trend (paid only).
SELECT DATE_FORMAT(o.ordered_at,'%Y-%m') AS month,
       ROUND(SUM(oi.quantity*oi.unit_price),2) AS revenue
FROM orders o
JOIN order_items oi ON oi.order_id = o.id
WHERE o.status='paid'
GROUP BY month
ORDER BY month;

-- Q6. Refund/cancellation rate by order status.
SELECT status, COUNT(*) AS orders,
       ROUND(100*COUNT(*)/SUM(COUNT(*)) OVER (),1) AS pct
FROM orders
GROUP BY status
ORDER BY orders DESC;

-- Q7. Repeat customers (more than one paid order).
SELECT c.full_name, COUNT(DISTINCT o.id) AS paid_orders
FROM customers c
JOIN orders o ON o.customer_id = c.id AND o.status='paid'
GROUP BY c.id, c.full_name
HAVING paid_orders > 1;
