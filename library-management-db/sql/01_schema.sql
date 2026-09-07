-- Library Management System — relational schema (MySQL 8.0)
-- Members borrow copies of books; loans track checkout/return and drive
-- overdue detection. Normalized to 3NF.

DROP DATABASE IF EXISTS library;
CREATE DATABASE library CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE library;

CREATE TABLE members (
  id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  full_name   VARCHAR(80)  NOT NULL,
  email       VARCHAR(255) NOT NULL UNIQUE,
  joined_at   DATE         NOT NULL DEFAULT (CURRENT_DATE)
) ENGINE=InnoDB;

CREATE TABLE books (
  id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  title       VARCHAR(200) NOT NULL,
  author      VARCHAR(120) NOT NULL,
  isbn        CHAR(13)     NOT NULL UNIQUE,
  category    VARCHAR(40)  NOT NULL,
  total_copies INT UNSIGNED NOT NULL DEFAULT 1
) ENGINE=InnoDB;

-- One physical copy of a book (a book can have many copies).
CREATE TABLE copies (
  id        INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  book_id   INT UNSIGNED NOT NULL,
  barcode   VARCHAR(20)  NOT NULL UNIQUE,
  FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE,
  INDEX idx_copies_book (book_id)
) ENGINE=InnoDB;

-- A loan: due_date = borrowed + 14 days; returned_at NULL means still out.
CREATE TABLE loans (
  id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  copy_id     INT UNSIGNED NOT NULL,
  member_id   INT UNSIGNED NOT NULL,
  borrowed_at DATE NOT NULL,
  due_date    DATE NOT NULL,
  returned_at DATE DEFAULT NULL,
  FOREIGN KEY (copy_id)   REFERENCES copies(id)   ON DELETE CASCADE,
  FOREIGN KEY (member_id) REFERENCES members(id)  ON DELETE CASCADE,
  INDEX idx_loans_member (member_id),
  INDEX idx_loans_open (returned_at)
) ENGINE=InnoDB;
