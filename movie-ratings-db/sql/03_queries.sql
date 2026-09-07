-- Ratings analytics + collaborative-filtering recommendations.
-- "Liked" = a score of 4 or 5.
USE movies;

-- Q1. Highest-rated movies (min 2 ratings, to avoid 1-vote flukes).
SELECT m.title, m.release_year,
       COUNT(r.user_id) AS votes,
       ROUND(AVG(r.score),2) AS avg_score
FROM movies m
JOIN ratings r ON r.movie_id = m.id
GROUP BY m.id, m.title, m.release_year
HAVING votes >= 2
ORDER BY avg_score DESC, votes DESC;

-- Q2. "USERS WHO LIKED X ALSO LIKED..." — item-based collaborative filtering.
--     Self-join ratings: find users who liked the seed movie (id 1,
--     Arrival), then count what else those same users liked.
SELECT m.title,
       COUNT(*) AS co_likes,
       ROUND(AVG(other.score),2) AS avg_score
FROM ratings seed
JOIN ratings other ON other.user_id = seed.user_id
                  AND other.movie_id <> seed.movie_id
JOIN movies m      ON m.id = other.movie_id
WHERE seed.movie_id = 1          -- the movie being viewed
  AND seed.score  >= 4           -- by users who liked it
  AND other.score >= 4           -- what else they liked
GROUP BY m.id, m.title
ORDER BY co_likes DESC, avg_score DESC;

-- Q3. Most similar users to user 1, by count of movies both rated >= 4.
SELECT u.username, COUNT(*) AS shared_likes
FROM ratings a
JOIN ratings b ON b.movie_id = a.movie_id
              AND b.user_id <> a.user_id
              AND a.score >= 4 AND b.score >= 4
JOIN users u  ON u.id = b.user_id
WHERE a.user_id = 1
GROUP BY u.id, u.username
ORDER BY shared_likes DESC;

-- Q4. Personalized picks for user 1: liked by their nearest neighbours
--     but NOT yet rated by user 1.
SELECT m.title, COUNT(*) AS endorsements, ROUND(AVG(r.score),2) AS avg_score
FROM ratings r
JOIN movies m ON m.id = r.movie_id
WHERE r.score >= 4
  AND r.user_id IN (
        SELECT b.user_id
        FROM ratings a
        JOIN ratings b ON b.movie_id = a.movie_id AND b.user_id <> a.user_id
        WHERE a.user_id = 1 AND a.score >= 4 AND b.score >= 4
        GROUP BY b.user_id
        HAVING COUNT(*) >= 2)                 -- neighbours: >=2 shared likes
  AND m.id NOT IN (SELECT movie_id FROM ratings WHERE user_id = 1)
GROUP BY m.id, m.title
ORDER BY endorsements DESC, avg_score DESC;

-- Q5. Average score by genre.
SELECT g.genre_name, COUNT(r.user_id) AS ratings, ROUND(AVG(r.score),2) AS avg_score
FROM genres g
JOIN movie_genres mg ON mg.genre_id = g.id
JOIN ratings r       ON r.movie_id  = mg.movie_id
GROUP BY g.id, g.genre_name
ORDER BY avg_score DESC;

-- Q6. Most active raters.
SELECT u.username, COUNT(*) AS ratings_given, ROUND(AVG(r.score),2) AS avg_given
FROM users u
JOIN ratings r ON r.user_id = u.id
GROUP BY u.id, u.username
ORDER BY ratings_given DESC;
