-- Sample data for ig_clone. Small but enough to exercise every query.
USE ig_clone;

INSERT INTO users (username, email, full_name, created_at) VALUES
 ('maya',   'maya@ex.com',   'Maya Ortiz',   '2024-01-02'),
 ('leo',    'leo@ex.com',    'Leo Park',      '2024-01-05'),
 ('aisha',  'aisha@ex.com',  'Aisha Khan',    '2024-01-08'),
 ('noah',   'noah@ex.com',   'Noah Bell',     '2024-01-11'),
 ('sofia',  'sofia@ex.com',  'Sofia Rossi',   '2024-01-15'),
 ('kenji',  'kenji@ex.com',  'Kenji Sato',    '2024-01-20'),
 ('ghost',  'ghost@ex.com',  'No Posts',      '2024-01-22');  -- user with zero photos

INSERT INTO photos (image_url, caption, user_id, created_at) VALUES
 ('img/1.jpg','sunrise',        1,'2024-02-01'),
 ('img/2.jpg','coffee',         1,'2024-02-03'),
 ('img/3.jpg','trail run',      2,'2024-02-04'),
 ('img/4.jpg','city lights',    3,'2024-02-06'),
 ('img/5.jpg','ramen night',    6,'2024-02-08'),
 ('img/6.jpg','beach',          5,'2024-02-10'),
 ('img/7.jpg','studio',         2,'2024-02-12'),
 ('img/8.jpg','museum',         4,'2024-02-14');

INSERT INTO tags (tag_name) VALUES
 ('travel'),('food'),('fitness'),('art'),('night');

INSERT INTO photo_tags (photo_id, tag_id) VALUES
 (1,1),(2,2),(3,3),(4,5),(4,1),(5,2),(6,1),(7,4),(8,4),(8,1);

INSERT INTO likes (user_id, photo_id) VALUES
 (2,1),(3,1),(4,1),(5,1),         -- photo 1: 4 likes
 (1,3),(5,3),(6,3),                -- photo 3: 3 likes
 (1,4),(2,4),(3,4),(5,4),(6,4),    -- photo 4: 5 likes (top)
 (1,5),(3,5),                       -- photo 5: 2 likes
 (2,6),(4,6),(6,6),                 -- photo 6: 3 likes
 (3,8);                             -- photo 8: 1 like

INSERT INTO comments (body, user_id, photo_id) VALUES
 ('love this',2,1),('so calm',3,1),('nice',4,4),
 ('where is this?',1,4),('yum',3,5),('great shot',6,6);

INSERT INTO follows (follower_id, followee_id) VALUES
 (1,2),(1,3),(2,1),(2,3),(3,1),(4,1),(4,2),(5,1),(6,2),(3,5),(5,3);
