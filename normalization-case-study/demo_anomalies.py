"""Demonstrate the three classic anomalies, then show 3NF removing them.

Runs entirely in in-memory SQLite. No setup:  python3 demo_anomalies.py
"""
import sqlite3, pathlib

SQL = pathlib.Path(__file__).parent / "sql"

def load(conn, *files):
    for f in files:
        conn.executescript((SQL / f).read_text())

def rule(t):
    print(f"\n{'='*62}\n{t}\n{'='*62}")

# ---------------------------------------------------------------- 1NF
rule("1NF — atomicity")
c = sqlite3.connect(":memory:"); load(c, "01_unnormalized.sql")
row = c.execute("SELECT student_name, courses FROM enrollment_raw WHERE student_id=1").fetchone()
print(f"  UNF row: {row[0]} -> courses = {row[1]!r}")
print("  Q: 'How many students take MA201?' requires string matching:")
n = c.execute("SELECT COUNT(*) FROM enrollment_raw WHERE courses LIKE '%MA201%'").fetchone()[0]
print(f"     LIKE '%MA201%' -> {n}. Fragile: 'MA2010' would match too.")
c2 = sqlite3.connect(":memory:"); load(c2, "02_first_normal_form.sql")
n2 = c2.execute("SELECT COUNT(*) FROM enrollment_1nf WHERE course_code='MA201'").fetchone()[0]
print(f"  1NF: WHERE course_code='MA201' -> {n2}. Exact, indexable.")

# ------------------------------------------------------- UPDATE anomaly
rule("UPDATE anomaly — one fact stored many times")
c = sqlite3.connect(":memory:"); load(c, "02_first_normal_form.sql")
before = c.execute("SELECT COUNT(*) FROM enrollment_1nf WHERE instructor='Dr. Reed'").fetchone()[0]
print(f"  Dr. Reed's office 'E-204' is duplicated across {before} rows.")
# a partial update: someone forgets the WHERE covers every row
c.execute("UPDATE enrollment_1nf SET instructor_office='E-310' WHERE student_id=1 AND course_code='CS101'")
offices = [r[0] for r in c.execute(
    "SELECT DISTINCT instructor_office FROM enrollment_1nf WHERE instructor='Dr. Reed'")]
print(f"  After updating ONE row, Dr. Reed now has offices: {offices}")
print("  -> The database contradicts itself. No constraint can catch this.")

c3 = sqlite3.connect(":memory:"); load(c3, "04_third_normal_form.sql")
c3.execute("UPDATE instructors SET office='E-310' WHERE full_name='Dr. Reed'")
off = [r[0] for r in c3.execute(
    "SELECT DISTINCT instructor_office FROM v_enrollment_report WHERE instructor='Dr. Reed'")]
print(f"  3NF: office stored once; one UPDATE -> report shows {off}. Impossible to desync.")

# ------------------------------------------------------- INSERT anomaly
rule("INSERT anomaly — can't record a fact without an unrelated one")
c = sqlite3.connect(":memory:"); load(c, "02_first_normal_form.sql")
print("  New course CH100 exists but nobody has enrolled yet.")
print("  In 1NF the PK is (student_id, course_code) -> a row needs a student.")
try:
    c.execute("INSERT INTO enrollment_1nf (student_id, course_code, course_name) "
              "VALUES (NULL,'CH100','General Chemistry')")
    c.commit()
    print("  SQLite allowed NULL in the PK -> a junk row now pollutes every student query.")
    print("  (MySQL rejects NULL in a PRIMARY KEY outright: the course is simply unrecordable.)")
except sqlite3.IntegrityError as e:
    print(f"  Rejected: {e}  -> the course simply cannot be recorded.")

c3 = sqlite3.connect(":memory:"); load(c3, "04_third_normal_form.sql")
c3.execute("INSERT INTO courses VALUES ('CH100','General Chemistry',1,1)")
print(f"  3NF: courses is its own table -> inserted cleanly, "
      f"{c3.execute('SELECT COUNT(*) FROM courses').fetchone()[0]} courses, 0 enrollments needed.")

# ------------------------------------------------------- DELETE anomaly
rule("DELETE anomaly — removing one fact destroys another")
c = sqlite3.connect(":memory:"); load(c, "02_first_normal_form.sql")
print("  Chloe drops PH110 — her only Physics enrollment.")
c.execute("DELETE FROM enrollment_1nf WHERE student_id=3 AND course_code='PH110'")
left = c.execute("SELECT COUNT(*) FROM enrollment_1nf WHERE department='Physics'").fetchone()[0]
print(f"  Rows mentioning Physics now: {left}")
print("  -> PH110, Dr. Ito and the whole Physics department vanished from the database.")

c3 = sqlite3.connect(":memory:"); load(c3, "04_third_normal_form.sql")
c3.execute("DELETE FROM enrollments WHERE student_id=3 AND course_code='PH110'")
course_left = c3.execute(
    "SELECT COUNT(*) FROM courses WHERE course_code=?", ("PH110",)).fetchone()[0]
dept_left = c3.execute(
    "SELECT COUNT(*) FROM departments WHERE dept_name=?", ("Physics",)).fetchone()[0]
print(f"  3NF after the same delete: PH110 still exists ({course_left}), "
      f"Physics dept still exists ({dept_left}).")

# ------------------------------------------------------- lossless check
rule("Lossless decomposition — nothing was lost")
c3 = sqlite3.connect(":memory:"); load(c3, "04_third_normal_form.sql")
c1 = sqlite3.connect(":memory:"); load(c1, "02_first_normal_form.sql")
a = sorted(c1.execute("SELECT student_id,course_code,grade FROM enrollment_1nf"))
b = sorted(c3.execute("SELECT student_id,course_code,grade FROM v_enrollment_report"))
print(f"  1NF rows: {len(a)}   3NF view rows: {len(b)}   identical: {a == b}")
storage = {"1NF": 6*10, "3NF": 3+2+4+3+6}
print(f"  Duplicated fields: 1NF stores ~{storage['1NF']} values; "
      f"3NF stores ~{storage['3NF']} across five tables.")
