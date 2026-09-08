-- STAGE 3 — Third Normal Form (3NF)
-- Rule: 2NF, and no non-key column depends on another non-key column.
-- Fix: instructors and departments become their own entities. A course
-- now references them by key instead of copying their attributes.
--
-- Every fact now lives in exactly one place.

CREATE TABLE departments (
  dept_id   INT PRIMARY KEY,
  dept_name VARCHAR(60) NOT NULL UNIQUE,
  dept_head VARCHAR(80) NOT NULL
);

CREATE TABLE instructors (
  instructor_id INT PRIMARY KEY,
  full_name     VARCHAR(80) NOT NULL,
  office        VARCHAR(20) NOT NULL,
  dept_id       INT NOT NULL,
  FOREIGN KEY (dept_id) REFERENCES departments(dept_id)
);

CREATE TABLE students (
  student_id INT PRIMARY KEY,
  full_name  VARCHAR(80)  NOT NULL,
  email      VARCHAR(255) NOT NULL UNIQUE
);

CREATE TABLE courses (
  course_code   VARCHAR(10) PRIMARY KEY,
  course_name   VARCHAR(80) NOT NULL,
  instructor_id INT NOT NULL,
  dept_id       INT NOT NULL,
  FOREIGN KEY (instructor_id) REFERENCES instructors(instructor_id),
  FOREIGN KEY (dept_id)       REFERENCES departments(dept_id)
);

CREATE TABLE enrollments (
  student_id  INT,
  course_code VARCHAR(10),
  grade       VARCHAR(2),
  PRIMARY KEY (student_id, course_code),
  FOREIGN KEY (student_id)  REFERENCES students(student_id),
  FOREIGN KEY (course_code) REFERENCES courses(course_code)
);

INSERT INTO departments VALUES
 (1,'Computer Science','Dr. Vance'),(2,'Mathematics','Dr. Ling'),(3,'Physics','Dr. Ito');

INSERT INTO instructors VALUES
 (1,'Dr. Reed','E-204',1),(2,'Dr. Osei','S-118',2);

INSERT INTO students VALUES
 (1,'Amara Diallo','amara@ex.com'),(2,'Ben Cohen','ben@ex.com'),
 (3,'Chloe Tan','chloe@ex.com'),(4,'Diego Silva','diego@ex.com');

INSERT INTO courses VALUES
 ('CS101','Intro to Programming',1,1),
 ('MA201','Linear Algebra',2,2),
 ('PH110','Classical Mechanics',2,3);

INSERT INTO enrollments VALUES
 (1,'CS101','A'),(1,'MA201','A'),(2,'CS101','B'),
 (3,'MA201','A'),(3,'PH110','B'),(4,'CS101','C');

-- The original flat view is still reconstructible -- nothing was lost.
CREATE VIEW v_enrollment_report AS
SELECT s.student_id, s.full_name AS student_name, s.email AS student_email,
       c.course_code, c.course_name,
       i.full_name AS instructor, i.office AS instructor_office,
       d.dept_name AS department, d.dept_head, e.grade
FROM enrollments e
JOIN students    s ON s.student_id = e.student_id
JOIN courses     c ON c.course_code = e.course_code
JOIN instructors i ON i.instructor_id = c.instructor_id
JOIN departments d ON d.dept_id = c.dept_id;
