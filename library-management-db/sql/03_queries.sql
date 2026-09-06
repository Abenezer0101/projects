-- Library analytics. Reference date ("today") = 2024-03-01.
USE library;
SET @today = DATE('2024-03-01');

-- Q1. Currently checked-out copies (not yet returned).
SELECT l.id AS loan, m.full_name, b.title, l.borrowed_at, l.due_date
FROM loans l
JOIN members m ON m.id = l.member_id
JOIN copies c  ON c.id = l.copy_id
JOIN books b   ON b.id = c.book_id
WHERE l.returned_at IS NULL
ORDER BY l.due_date;

-- Q2. Overdue loans: open AND past due. Includes days overdue.
SELECT m.full_name, b.title, l.due_date,
       DATEDIFF(@today, l.due_date) AS days_overdue
FROM loans l
JOIN members m ON m.id = l.member_id
JOIN copies c  ON c.id = l.copy_id
JOIN books b   ON b.id = c.book_id
WHERE l.returned_at IS NULL AND l.due_date < @today
ORDER BY days_overdue DESC;

-- Q3. Available copies per book = total copies minus copies currently out.
SELECT b.title, b.total_copies,
       COUNT(c.id) - COALESCE(SUM(c.id IN
             (SELECT copy_id FROM loans WHERE returned_at IS NULL)),0) AS available
FROM books b
JOIN copies c ON c.book_id = b.id
GROUP BY b.id, b.title, b.total_copies
ORDER BY available;

-- Q4. Most-borrowed books (all-time loan count).
SELECT b.title, b.category, COUNT(l.id) AS times_borrowed
FROM books b
JOIN copies c ON c.book_id = b.id
JOIN loans l  ON l.copy_id = c.id
GROUP BY b.id, b.title, b.category
ORDER BY times_borrowed DESC
LIMIT 5;

-- Q5. Members with at least one overdue book (who to email).
SELECT DISTINCT m.full_name, m.email
FROM loans l
JOIN members m ON m.id = l.member_id
WHERE l.returned_at IS NULL AND l.due_date < @today;

-- Q6. Return punctuality: on-time vs late returns per member.
SELECT m.full_name,
       SUM(l.returned_at <= l.due_date) AS on_time,
       SUM(l.returned_at >  l.due_date) AS late
FROM loans l
JOIN members m ON m.id = l.member_id
WHERE l.returned_at IS NOT NULL
GROUP BY m.id, m.full_name
ORDER BY late DESC;
