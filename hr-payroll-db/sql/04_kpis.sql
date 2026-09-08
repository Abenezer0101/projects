USE hr;

-- Q1. Headcount and payroll by department.
SELECT * FROM v_dept_payroll ORDER BY annual_payroll DESC;

-- Q2. Company-wide KPIs.
SELECT COUNT(*) AS headcount,
       SUM(salary) AS total_payroll,
       ROUND(AVG(salary),2) AS avg_salary,
       MAX(salary) AS highest,
       MIN(salary) AS lowest
FROM v_active_employees;

-- Q3. Org chart: each manager and their direct reports.
SELECT m.full_name AS manager, COUNT(e.id) AS direct_reports
FROM employees m
JOIN employees e ON e.manager_id = m.id AND e.terminated_at IS NULL
WHERE m.terminated_at IS NULL
GROUP BY m.id, m.full_name
ORDER BY direct_reports DESC;

-- Q4. Salary band by job level (compression check).
SELECT j.job_level, COUNT(*) AS employees,
       MIN(cs.annual_amount) AS min_pay,
       ROUND(AVG(cs.annual_amount),2) AS avg_pay,
       MAX(cs.annual_amount) AS max_pay
FROM employees e
JOIN job_titles j ON j.id = e.job_id
JOIN v_current_salary cs ON cs.employee_id = e.id
WHERE e.terminated_at IS NULL
GROUP BY j.job_level
ORDER BY j.job_level DESC;

-- Q5. Who has received a raise, and by how much (uses salary history).
SELECT e.full_name,
       old.annual_amount AS previous,
       cur.annual_amount AS current_pay,
       ROUND(100*(cur.annual_amount-old.annual_amount)/old.annual_amount,1) AS pct_increase
FROM employees e
JOIN salaries cur ON cur.employee_id = e.id AND cur.effective_to IS NULL
JOIN salaries old ON old.employee_id = e.id AND old.effective_to IS NOT NULL
ORDER BY pct_increase DESC;

-- Q6. Attrition: employees who left, with tenure in months.
SELECT full_name, hired_at, terminated_at,
       TIMESTAMPDIFF(MONTH, hired_at, terminated_at) AS tenure_months
FROM employees
WHERE terminated_at IS NOT NULL;

-- Q7. Average tenure of active staff, in years.
SELECT ROUND(AVG(TIMESTAMPDIFF(MONTH, hired_at, '2024-03-01'))/12, 2) AS avg_tenure_years
FROM employees WHERE terminated_at IS NULL;
