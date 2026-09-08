USE hr;

INSERT INTO departments (id, dept_name, location) VALUES
 (1,'Engineering','Atlanta'),(2,'Sales','Atlanta'),
 (3,'Marketing','Remote'),(4,'Finance','Atlanta');

INSERT INTO job_titles (id, title, job_level) VALUES
 (1,'Engineering Manager',5),(2,'Senior Engineer',4),(3,'Engineer',3),
 (4,'Sales Director',5),(5,'Account Executive',3),
 (6,'Marketing Specialist',2),(7,'Financial Analyst',3);

-- managers first (self-referencing FK)
INSERT INTO employees (id, full_name, email, dept_id, job_id, manager_id, hired_at, terminated_at) VALUES
 (1,'Amara Diallo','amara@ex.com',1,1,NULL,'2020-03-02',NULL),
 (2,'Ben Cohen','ben@ex.com',2,4,NULL,'2020-06-15',NULL),
 (3,'Chloe Tan','chloe@ex.com',1,2,1,'2021-01-11',NULL),
 (4,'Diego Silva','diego@ex.com',1,3,1,'2022-04-04',NULL),
 (5,'Ella Novak','ella@ex.com',1,3,1,'2023-02-20',NULL),
 (6,'Kenji Sato','kenji@ex.com',2,5,2,'2021-09-06',NULL),
 (7,'Fatima Noor','fatima@ex.com',2,5,2,'2022-11-14',NULL),
 (8,'Grace Lin','grace@ex.com',3,6,NULL,'2023-05-08',NULL),
 (9,'Hugo Martin','hugo@ex.com',4,7,NULL,'2021-07-19',NULL),
 (10,'Ivan Petrov','ivan@ex.com',1,3,1,'2021-03-01','2023-08-31');  -- departed

-- Salary history. Closed rows (effective_to set) are prior versions.
INSERT INTO salaries (employee_id, annual_amount, effective_from, effective_to) VALUES
 (1,150000,'2020-03-02','2022-03-01'),(1,168000,'2022-03-02',NULL),
 (2,145000,'2020-06-15','2023-01-01'),(2,159000,'2023-01-02',NULL),
 (3,120000,'2021-01-11','2023-01-01'),(3,132000,'2023-01-02',NULL),
 (4,98000,'2022-04-04',NULL),
 (5,95000,'2023-02-20',NULL),
 (6,88000,'2021-09-06','2023-06-01'),(6,96000,'2023-06-02',NULL),
 (7,85000,'2022-11-14',NULL),
 (8,72000,'2023-05-08',NULL),
 (9,91000,'2021-07-19',NULL),
 (10,90000,'2021-03-01','2023-08-31');
