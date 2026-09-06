-- Analytical queries for ig_clone. Each answers a product/analytics question.
USE ig_clone;

-- Q1. Most-liked photo(s) — the classic "top post" leaderboard.
SELECT p.id, u.username, p.caption, COUNT(l.user_id) AS likes
FROM photos p
JOIN users u  ON u.id = p.user_id
LEFT JOIN likes l ON l.photo_id = p.id
GROUP BY p.id, u.username, p.caption
ORDER BY likes DESC
LIMIT 5;

-- Q2. Most influential users by average likes per photo (min 2 photos).
SELECT u.username,
       COUNT(DISTINCT p.id)                      AS photos,
       COUNT(l.user_id)                          AS total_likes,
       ROUND(COUNT(l.user_id)/COUNT(DISTINCT p.id),2) AS avg_likes
FROM users u
JOIN photos p ON p.user_id = u.id
LEFT JOIN likes l ON l.photo_id = p.id
GROUP BY u.id, u.username
HAVING photos >= 2
ORDER BY avg_likes DESC;

-- Q3. Users who have never posted a photo (retention / activation gap).
SELECT u.username
FROM users u
LEFT JOIN photos p ON p.user_id = u.id
WHERE p.id IS NULL;

-- Q4. Mutual follows (pairs who follow each other) — friendship graph.
SELECT a.username AS user_a, b.username AS user_b
FROM follows f1
JOIN follows f2 ON f1.follower_id = f2.followee_id
               AND f1.followee_id = f2.follower_id
JOIN users a ON a.id = f1.follower_id
JOIN users b ON b.id = f1.followee_id
WHERE f1.follower_id < f1.followee_id;

-- Q5. Top 3 hashtags by usage.
SELECT t.tag_name, COUNT(pt.photo_id) AS uses
FROM tags t
JOIN photo_tags pt ON pt.tag_id = t.id
GROUP BY t.id, t.tag_name
ORDER BY uses DESC
LIMIT 3;

-- Q6. Engagement per photo: likes + comments, ranked (window function).
SELECT p.id, u.username, p.caption,
       COUNT(DISTINCT l.user_id)   AS likes,
       COUNT(DISTINCT c.id)        AS comments,
       COUNT(DISTINCT l.user_id) + COUNT(DISTINCT c.id) AS engagement,
       RANK() OVER (ORDER BY COUNT(DISTINCT l.user_id) + COUNT(DISTINCT c.id) DESC) AS rnk
FROM photos p
JOIN users u ON u.id = p.user_id
LEFT JOIN likes l    ON l.photo_id = p.id
LEFT JOIN comments c ON c.photo_id = p.id
GROUP BY p.id, u.username, p.caption
ORDER BY engagement DESC;

-- Q7. Follower counts and each user's most-used tag (correlated subquery).
SELECT u.username,
       (SELECT COUNT(*) FROM follows f WHERE f.followee_id = u.id) AS followers,
       (SELECT COUNT(*) FROM follows f WHERE f.follower_id = u.id) AS following
FROM users u
ORDER BY followers DESC;
