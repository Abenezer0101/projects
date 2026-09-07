USE shop;

INSERT INTO customers (id, full_name, email, country, created_at) VALUES
 (1,'Amara Diallo','amara@ex.com','USA','2024-01-03'),
 (2,'Ben Cohen','ben@ex.com','USA','2024-01-10'),
 (3,'Chloe Tan','chloe@ex.com','Singapore','2024-01-18'),
 (4,'Diego Silva','diego@ex.com','Brazil','2024-02-02'),
 (5,'Ella Novak','ella@ex.com','Germany','2024-02-11');

INSERT INTO products (id, name, category, price) VALUES
 (1,'Wireless Mouse','Electronics',24.99),
 (2,'Mechanical Keyboard','Electronics',89.00),
 (3,'USB-C Hub','Electronics',39.50),
 (4,'Notebook','Stationery',6.75),
 (5,'Desk Lamp','Home',34.00),
 (6,'Coffee Mug','Home',12.50);

INSERT INTO orders (id, customer_id, ordered_at, status) VALUES
 (1,1,'2024-02-05','paid'),
 (2,1,'2024-02-20','paid'),
 (3,2,'2024-02-06','paid'),
 (4,3,'2024-02-15','paid'),
 (5,3,'2024-03-01','refunded'),
 (6,4,'2024-03-03','paid'),
 (7,5,'2024-03-05','cancelled');

-- unit_price mirrors product price here (captured at purchase).
INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES
 (1,1,1,24.99),(1,4,3,6.75),                 -- order 1: 24.99 + 20.25 = 45.24
 (2,2,1,89.00),                               -- order 2: 89.00
 (3,3,2,39.50),(3,6,1,12.50),                 -- order 3: 79.00 + 12.50 = 91.50
 (4,5,1,34.00),(4,6,2,12.50),                 -- order 4: 34.00 + 25.00 = 59.00
 (5,2,1,89.00),                               -- order 5: 89.00 (refunded)
 (6,1,2,24.99),(6,3,1,39.50),                 -- order 6: 49.98 + 39.50 = 89.48
 (7,4,5,6.75);                                -- order 7: 33.75 (cancelled)
