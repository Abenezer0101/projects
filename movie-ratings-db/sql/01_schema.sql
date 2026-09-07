-- Movie ratings & recommendations (MySQL 8.0).
-- Users rate movies 1-5. Recommendations are derived from co-rating
-- overlap, so no recommendation data is ever stored.

DROP DATABASE IF EXISTS movies;
CREATE DATABASE movies CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE movies;

CREATE TABLE users (
  id         INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  username   VARCHAR(30) NOT NULL UNIQUE,
  joined_at  DATE        NOT NULL
) ENGINE=InnoDB;

CREATE TABLE movies (
  id           INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  title        VARCHAR(200) NOT NULL,
  release_year SMALLINT UNSIGNED NOT NULL,
  UNIQUE KEY uq_movie (title, release_year)
) ENGINE=InnoDB;

CREATE TABLE genres (
  id         INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  genre_name VARCHAR(40) NOT NULL UNIQUE
) ENGINE=InnoDB;

-- M:N — a movie has many genres.
CREATE TABLE movie_genres (
  movie_id INT UNSIGNED NOT NULL,
  genre_id INT UNSIGNED NOT NULL,
  PRIMARY KEY (movie_id, genre_id),
  FOREIGN KEY (movie_id) REFERENCES movies(id) ON DELETE CASCADE,
  FOREIGN KEY (genre_id) REFERENCES genres(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- One rating per user per movie, enforced by the composite key.
CREATE TABLE ratings (
  user_id   INT UNSIGNED NOT NULL,
  movie_id  INT UNSIGNED NOT NULL,
  score     TINYINT UNSIGNED NOT NULL CHECK (score BETWEEN 1 AND 5),
  rated_at  DATE NOT NULL,
  PRIMARY KEY (user_id, movie_id),
  FOREIGN KEY (user_id)  REFERENCES users(id)  ON DELETE CASCADE,
  FOREIGN KEY (movie_id) REFERENCES movies(id) ON DELETE CASCADE,
  INDEX idx_ratings_movie (movie_id)
) ENGINE=InnoDB;
