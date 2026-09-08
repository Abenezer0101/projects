-- STAGE 0 — Unnormalized (UNF). The spreadsheet someone actually sent.
-- Every problem in this file is deliberate.
--
-- Violations:
--   * `courses` holds a comma-separated list  -> not atomic (breaks 1NF)
--   * student, course, instructor and department facts all live in one row
--   * every fact is repeated once per enrollment

CREATE TABLE enrollment_raw (
  student_id       INT,
  student_name     VARCHAR(80),
  student_email    VARCHAR(255),
  courses          VARCHAR(255),   -- "CS101, MA201"  <-- repeating group
  instructor       VARCHAR(80),
  instructor_office VARCHAR(20),
  department       VARCHAR(60),
  dept_head        VARCHAR(80),
  grade            VARCHAR(2)
);

INSERT INTO enrollment_raw VALUES
 (1,'Amara Diallo','amara@ex.com','CS101, MA201','Dr. Reed','E-204','Computer Science','Dr. Vance','A'),
 (2,'Ben Cohen','ben@ex.com','CS101','Dr. Reed','E-204','Computer Science','Dr. Vance','B'),
 (3,'Chloe Tan','chloe@ex.com','MA201, PH110','Dr. Osei','S-118','Mathematics','Dr. Ling','A'),
 (4,'Diego Silva','diego@ex.com','CS101','Dr. Reed','E-204','Computer Science','Dr. Vance','C');
