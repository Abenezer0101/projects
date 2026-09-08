-- HR / payroll database (MySQL 8.0).
-- Employees belong to departments, hold a job title, and accrue payroll
-- runs. Salary history is kept as versioned rows, never overwritten.

DROP DATABASE IF EXISTS hr;
CREATE DATABASE hr CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE hr;

CREATE TABLE departments (
  id        INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  dept_name VARCHAR(60) NOT NULL UNIQUE,
  location  VARCHAR(60) NOT NULL
) ENGINE=InnoDB;

CREATE TABLE job_titles (
  id        INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  title     VARCHAR(80) NOT NULL UNIQUE,
  job_level TINYINT UNSIGNED NOT NULL CHECK (job_level BETWEEN 1 AND 6)
) ENGINE=InnoDB;

CREATE TABLE employees (
  id           INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  full_name    VARCHAR(80)  NOT NULL,
  email        VARCHAR(255) NOT NULL UNIQUE,
  dept_id      INT UNSIGNED NOT NULL,
  job_id       INT UNSIGNED NOT NULL,
  manager_id   INT UNSIGNED DEFAULT NULL,   -- self-reference: org chart
  hired_at     DATE NOT NULL,
  terminated_at DATE DEFAULT NULL,          -- NULL = currently employed
  FOREIGN KEY (dept_id)    REFERENCES departments(id),
  FOREIGN KEY (job_id)     REFERENCES job_titles(id),
  FOREIGN KEY (manager_id) REFERENCES employees(id) ON DELETE SET NULL,
  INDEX idx_emp_dept (dept_id),
  INDEX idx_emp_active (terminated_at)
) ENGINE=InnoDB;

-- Versioned salary: a raise inserts a new row and closes the old one.
-- effective_to NULL = the currently active salary.
CREATE TABLE salaries (
  id            INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  employee_id   INT UNSIGNED NOT NULL,
  annual_amount DECIMAL(10,2) NOT NULL CHECK (annual_amount > 0),
  effective_from DATE NOT NULL,
  effective_to   DATE DEFAULT NULL,
  FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE,
  INDEX idx_sal_current (employee_id, effective_to)
) ENGINE=InnoDB;
