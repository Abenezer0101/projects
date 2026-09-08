USE hr;

-- VIEW 1: current salary per employee. Encapsulates the versioning rule
-- (effective_to IS NULL) so no query has to remember it.
CREATE OR REPLACE VIEW v_current_salary AS
SELECT s.employee_id, s.annual_amount, s.effective_from
FROM salaries s
WHERE s.effective_to IS NULL;

-- VIEW 2: the active roster, denormalized for reporting.
CREATE OR REPLACE VIEW v_active_employees AS
SELECT e.id, e.full_name, d.dept_name, j.title, j.job_level,
       m.full_name AS manager, e.hired_at, cs.annual_amount AS salary
FROM employees e
JOIN departments d      ON d.id = e.dept_id
JOIN job_titles  j      ON j.id = e.job_id
LEFT JOIN employees m   ON m.id = e.manager_id
LEFT JOIN v_current_salary cs ON cs.employee_id = e.id
WHERE e.terminated_at IS NULL;

-- VIEW 3: department payroll rollup, built on the view above.
CREATE OR REPLACE VIEW v_dept_payroll AS
SELECT dept_name,
       COUNT(*) AS headcount,
       SUM(salary) AS annual_payroll,
       ROUND(AVG(salary),2) AS avg_salary
FROM v_active_employees
GROUP BY dept_name;

-- STORED PROCEDURE: give a raise correctly — close the current salary
-- row and open a new one, atomically. This is the whole point of
-- versioned salary: no UPDATE ever destroys history.
DROP PROCEDURE IF EXISTS give_raise;
DELIMITER $$
CREATE PROCEDURE give_raise(
  IN p_employee_id INT UNSIGNED,
  IN p_new_amount  DECIMAL(10,2),
  IN p_effective   DATE
)
BEGIN
  DECLARE v_current DECIMAL(10,2);

  DECLARE EXIT HANDLER FOR SQLEXCEPTION
  BEGIN
    ROLLBACK;
    RESIGNAL;
  END;

  START TRANSACTION;

    SELECT annual_amount INTO v_current
    FROM salaries
    WHERE employee_id = p_employee_id AND effective_to IS NULL
    FOR UPDATE;

    IF v_current IS NULL THEN
      SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'No active salary row for that employee';
    END IF;

    IF p_new_amount <= v_current THEN
      SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'New salary must exceed the current salary';
    END IF;

    UPDATE salaries
       SET effective_to = p_effective
     WHERE employee_id = p_employee_id AND effective_to IS NULL;

    INSERT INTO salaries (employee_id, annual_amount, effective_from, effective_to)
    VALUES (p_employee_id, p_new_amount, DATE_ADD(p_effective, INTERVAL 1 DAY), NULL);

  COMMIT;
END$$
DELIMITER ;

-- Example: CALL give_raise(4, 105000, '2024-06-30');
