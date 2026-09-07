-- E-commerce analytics schema (MySQL 8.0).
-- Customers place orders; each order has line items referencing products.
-- Order total is derived from line items (never stored), keeping 3NF.

DROP DATABASE IF EXISTS shop;
CREATE DATABASE shop CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE shop;

CREATE TABLE customers (
  id         INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  full_name  VARCHAR(80)  NOT NULL,
  email      VARCHAR(255) NOT NULL UNIQUE,
  country    VARCHAR(40)  NOT NULL,
  created_at DATE         NOT NULL
) ENGINE=InnoDB;

CREATE TABLE products (
  id         INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  name       VARCHAR(120)  NOT NULL,
  category   VARCHAR(40)   NOT NULL,
  price      DECIMAL(10,2) NOT NULL CHECK (price >= 0)
) ENGINE=InnoDB;

CREATE TABLE orders (
  id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  customer_id INT UNSIGNED NOT NULL,
  ordered_at  DATE NOT NULL,
  status      ENUM('paid','refunded','cancelled') NOT NULL DEFAULT 'paid',
  FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
  INDEX idx_orders_customer (customer_id),
  INDEX idx_orders_date (ordered_at)
) ENGINE=InnoDB;

-- Line item: unit_price is captured at purchase time (price can change later).
CREATE TABLE order_items (
  order_id   INT UNSIGNED NOT NULL,
  product_id INT UNSIGNED NOT NULL,
  quantity   INT UNSIGNED  NOT NULL CHECK (quantity > 0),
  unit_price DECIMAL(10,2) NOT NULL,
  PRIMARY KEY (order_id, product_id),
  FOREIGN KEY (order_id)   REFERENCES orders(id)   ON DELETE CASCADE,
  FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
) ENGINE=InnoDB;
