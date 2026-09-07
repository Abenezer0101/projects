USE movies;

INSERT INTO users (id, username, joined_at) VALUES
 (1,'amara','2023-06-01'),(2,'ben','2023-06-14'),(3,'chloe','2023-07-02'),
 (4,'diego','2023-08-19'),(5,'ella','2023-09-05'),(6,'kenji','2023-10-11');

INSERT INTO movies (id, title, release_year) VALUES
 (1,'Arrival',2016),(2,'Blade Runner 2049',2017),(3,'Dune',2021),
 (4,'The Grand Budapest Hotel',2014),(5,'Parasite',2019),
 (6,'Whiplash',2014),(7,'Interstellar',2014),(8,'Lady Bird',2017);

INSERT INTO genres (id, genre_name) VALUES
 (1,'Sci-Fi'),(2,'Drama'),(3,'Thriller'),(4,'Comedy');

INSERT INTO movie_genres (movie_id, genre_id) VALUES
 (1,1),(1,2),(2,1),(2,3),(3,1),(3,2),
 (4,4),(4,2),(5,2),(5,3),(6,2),(7,1),(7,2),(8,2),(8,4);

-- Deliberate structure: users 1,2,4 are the "sci-fi cluster" (they all
-- rate Arrival/BR2049/Dune highly); users 3,5 lean drama/comedy.
INSERT INTO ratings (user_id, movie_id, score, rated_at) VALUES
 (1,1,5,'2024-01-05'),(1,2,5,'2024-01-08'),(1,3,4,'2024-01-20'),(1,7,5,'2024-02-01'),
 (2,1,5,'2024-01-06'),(2,2,4,'2024-01-11'),(2,3,5,'2024-01-25'),(2,6,5,'2024-02-03'),
 (3,4,5,'2024-01-09'),(3,5,5,'2024-01-15'),(3,8,4,'2024-02-05'),(3,6,5,'2024-02-10'),
 (4,1,4,'2024-01-12'),(4,2,5,'2024-01-19'),(4,7,4,'2024-02-08'),(4,5,3,'2024-02-14'),(4,6,4,'2024-02-20'),(4,8,4,'2024-02-22'),
 (5,4,4,'2024-01-22'),(5,8,5,'2024-01-28'),(5,5,4,'2024-02-11'),
 (6,3,5,'2024-02-02'),(6,7,5,'2024-02-06'),(6,1,3,'2024-02-18');
