-- STAGE 1 — First Normal Form (1NF)
-- Rule: every column holds a single atomic value; no repeating groups.
-- Fix: split the comma list so each (student, course) pair is its own row.
-- Primary key becomes the composite (student_id, course_code).
--
-- Still broken: partial dependencies. student_name depends on student_id
-- alone, course_name on course_code alone -- neither needs the full key.

CREATE TABLE enrollment_1nf (
  student_id    INT,
  student_name  VARCHAR(80),
  student_email VARCHAR(255),
  course_code   VARCHAR(10),
  course_name   VARCHAR(80),
  instructor    VARCHAR(80),
  instructor_office VARCHAR(20),
  department    VARCHAR(60),
  dept_head     VARCHAR(80),
  grade         VARCHAR(2),
  PRIMARY KEY (student_id, course_code)
);

INSERT INTO enrollment_1nf VALUES
 (1,'Amara Diallo','amara@ex.com','CS101','Intro to Programming','Dr. Reed','E-204','Computer Science','Dr. Vance','A'),
 (1,'Amara Diallo','amara@ex.com','MA201','Linear Algebra','Dr. Osei','S-118','Mathematics','Dr. Ling','A'),
 (2,'Ben Cohen','ben@ex.com','CS101','Intro to Programming','Dr. Reed','E-204','Computer Science','Dr. Vance','B'),
 (3,'Chloe Tan','chloe@ex.com','MA201','Linear Algebra','Dr. Osei','S-118','Mathematics','Dr. Ling','A'),
 (3,'Chloe Tan','chloe@ex.com','PH110','Classical Mechanics','Dr. Osei','S-118','Physics','Dr. Ito','B'),
 (4,'Diego Silva','diego@ex.com','CS101','Intro to Programming','Dr. Reed','E-204','Computer Science','Dr. Vance','C');
