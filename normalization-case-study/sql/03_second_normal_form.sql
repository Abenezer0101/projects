-- STAGE 2 — Second Normal Form (2NF)
-- Rule: 1NF, and every non-key column depends on the WHOLE composite key.
-- Fix: pull out the columns that depended on only part of (student_id,
-- course_code) into their own tables.
--
--   student_id  -> student_name, student_email        (partial)
--   course_code -> course_name, instructor, ...       (partial)
--   (student_id, course_code) -> grade                (full -- stays)
--
-- Still broken: inside courses, instructor -> instructor_office and
-- department -> dept_head are TRANSITIVE dependencies (3NF's problem).

CREATE TABLE students_2nf (
  student_id    INT PRIMARY KEY,
  student_name  VARCHAR(80)  NOT NULL,
  student_email VARCHAR(255) NOT NULL UNIQUE
);

CREATE TABLE courses_2nf (
  course_code       VARCHAR(10) PRIMARY KEY,
  course_name       VARCHAR(80) NOT NULL,
  instructor        VARCHAR(80) NOT NULL,
  instructor_office VARCHAR(20) NOT NULL,  -- depends on instructor, not course
  department        VARCHAR(60) NOT NULL,
  dept_head         VARCHAR(80) NOT NULL   -- depends on department, not course
);

CREATE TABLE enrollments_2nf (
  student_id  INT,
  course_code VARCHAR(10),
  grade       VARCHAR(2),
  PRIMARY KEY (student_id, course_code),
  FOREIGN KEY (student_id)  REFERENCES students_2nf(student_id),
  FOREIGN KEY (course_code) REFERENCES courses_2nf(course_code)
);

INSERT INTO students_2nf VALUES
 (1,'Amara Diallo','amara@ex.com'),(2,'Ben Cohen','ben@ex.com'),
 (3,'Chloe Tan','chloe@ex.com'),(4,'Diego Silva','diego@ex.com');

INSERT INTO courses_2nf VALUES
 ('CS101','Intro to Programming','Dr. Reed','E-204','Computer Science','Dr. Vance'),
 ('MA201','Linear Algebra','Dr. Osei','S-118','Mathematics','Dr. Ling'),
 ('PH110','Classical Mechanics','Dr. Osei','S-118','Physics','Dr. Ito');

INSERT INTO enrollments_2nf VALUES
 (1,'CS101','A'),(1,'MA201','A'),(2,'CS101','B'),
 (3,'MA201','A'),(3,'PH110','B'),(4,'CS101','C');
