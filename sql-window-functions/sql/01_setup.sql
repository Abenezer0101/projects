-- Window-functions playground. One sales table; every query below is a
-- worked example of a different window pattern. MySQL 8.0 / SQLite 3.25+.

DROP DATABASE IF EXISTS sales_wf;
CREATE DATABASE sales_wf CHARACTER SET utf8mb4;
USE sales_wf;

CREATE TABLE sales (
  id        INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  rep       VARCHAR(40)  NOT NULL,
  region    VARCHAR(20)  NOT NULL,
  sale_date DATE         NOT NULL,
  amount    DECIMAL(10,2) NOT NULL
) ENGINE=InnoDB;

INSERT INTO sales (rep, region, sale_date, amount) VALUES
 ('Amara','East','2024-01-05',1200),('Amara','East','2024-01-22',800),
 ('Amara','East','2024-02-10',1500),('Amara','East','2024-03-02',600),
 ('Ben','East','2024-01-08',900),('Ben','East','2024-02-01',1100),
 ('Ben','East','2024-02-20',1300),('Ben','East','2024-03-11',700),
 ('Chloe','West','2024-01-12',2000),('Chloe','West','2024-02-05',1600),
 ('Chloe','West','2024-03-01',1800),('Diego','West','2024-01-19',500),
 ('Diego','West','2024-02-14',1400),('Diego','West','2024-03-07',1000);
