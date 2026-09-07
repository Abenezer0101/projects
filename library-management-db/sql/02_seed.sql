-- Sample data for the library. "Today" for the queries is 2024-03-01.
USE library;

INSERT INTO members (id, full_name, email, joined_at) VALUES
 (1,'Amara Diallo','amara@ex.com','2023-09-01'),
 (2,'Ben Cohen','ben@ex.com','2023-10-12'),
 (3,'Chloe Tan','chloe@ex.com','2023-11-05'),
 (4,'Diego Silva','diego@ex.com','2024-01-20'),
 (5,'Ella Novak','ella@ex.com','2024-02-14');

INSERT INTO books (id, title, author, isbn, category, total_copies) VALUES
 (1,'The Pragmatic Programmer','Hunt & Thomas','9780201616224','Tech',3),
 (2,'Clean Code','Robert Martin','9780132350884','Tech',2),
 (3,'Sapiens','Yuval Noah Harari','9780062316097','History',2),
 (4,'Educated','Tara Westover','9780399590504','Memoir',1),
 (5,'The Design of Everyday Things','Don Norman','9780465050659','Design',1);

INSERT INTO copies (id, book_id, barcode) VALUES
 (1,1,'BC-0001'),(2,1,'BC-0002'),(3,1,'BC-0003'),
 (4,2,'BC-0004'),(5,2,'BC-0005'),
 (6,3,'BC-0006'),(7,3,'BC-0007'),
 (8,4,'BC-0008'),
 (9,5,'BC-0009');

-- Loans. Some returned, some open, some open-and-overdue (due < 2024-03-01).
INSERT INTO loans (copy_id, member_id, borrowed_at, due_date, returned_at) VALUES
 (1,1,'2024-01-10','2024-01-24','2024-01-20'),  -- returned on time
 (4,2,'2024-01-15','2024-01-29','2024-02-10'),  -- returned late
 (6,3,'2024-02-01','2024-02-15',NULL),          -- OPEN + overdue
 (8,1,'2024-02-05','2024-02-19',NULL),          -- OPEN + overdue
 (2,4,'2024-02-25','2024-03-10',NULL),          -- open, not yet due
 (9,5,'2024-02-28','2024-03-13',NULL),          -- open, not yet due
 (7,2,'2024-01-20','2024-02-03','2024-02-01'),  -- returned on time
 (3,3,'2023-12-01','2023-12-15','2023-12-20');  -- returned late
