"""Generate examples/database_normalization.pdf — a realistic lecture handout.

Used as the test fixture and the demo input. Content is written for this
project; the subject matches the repo's other database work.
"""
import pathlib, textwrap
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas

OUT = pathlib.Path(__file__).parent / "database_normalization.pdf"

DOC = [
("1. Introduction to Normalization", """
Database normalization is defined as the process of organizing columns and tables
of a relational database to minimize data redundancy. The technique was introduced
by Edgar Codd as part of his relational model. A poorly normalized schema stores the
same fact in many places, which permits those copies to disagree with one another.
An update anomaly occurs when changing a fact requires updating many rows and one is
missed. An insertion anomaly is a situation where a fact cannot be recorded because
some unrelated information is not yet known. A deletion anomaly is the loss of one
fact as a side effect of deleting another.
"""),
("2. Functional Dependency", """
A functional dependency is a constraint between two sets of attributes in a relation.
Attribute B is functionally dependent on attribute A when each value of A is
associated with exactly one value of B. A candidate key is a minimal set of attributes
that functionally determines every other attribute in the relation. A partial
dependency is a dependency on only part of a composite candidate key. A transitive
dependency exists when a non-key attribute depends on another non-key attribute
rather than on the key itself. Identifying functional dependencies correctly is the
prerequisite for every normalization step that follows.
"""),
("3. The Normal Forms", """
First normal form requires that every attribute contain only atomic values, so a
column may not hold a list. Second normal form requires first normal form and the
removal of every partial dependency on a composite key. Third normal form requires
second normal form and the removal of every transitive dependency between non-key
attributes. Boyce-Codd normal form is a stricter version of third normal form in
which every determinant must be a candidate key. Each successive normal form
eliminates a specific class of anomaly, and the forms are cumulative.
"""),
("4. Decomposition and Trade-offs", """
Decomposition is the process of splitting one relation into several smaller relations.
A decomposition is lossless when the original relation can be reconstructed exactly by
joining the pieces back together. A dependency-preserving decomposition is one where
every functional dependency can still be enforced without performing a join.
Normalization optimizes for write correctness, not read speed. Analytical systems
frequently denormalize deliberately, accepting redundancy in exchange for avoiding
expensive joins at query time. The star schema is a denormalized design commonly used
in data warehouses. Choosing a normal form is therefore an engineering trade-off
rather than a rule to be followed blindly.
"""),
]

c = canvas.Canvas(str(OUT), pagesize=LETTER)
W, H = LETTER
y = H - 72
c.setFont("Helvetica-Bold", 16)
c.drawString(72, y, "Database Normalization")
y -= 20
c.setFont("Helvetica-Oblique", 10)
c.drawString(72, y, "CIS 3730 — Lecture Handout")
y -= 34

for heading, body in DOC:
    if y < 130:
        c.showPage(); y = H - 72
    c.setFont("Helvetica-Bold", 12)
    c.drawString(72, y, heading); y -= 18
    c.setFont("Helvetica", 10.5)
    for line in textwrap.wrap(" ".join(body.split()), 92):
        if y < 72:
            c.showPage(); y = H - 72; c.setFont("Helvetica", 10.5)
        c.drawString(72, y, line); y -= 14
    y -= 14

c.save()
print(f"wrote {OUT.name} ({OUT.stat().st_size:,} bytes)")
