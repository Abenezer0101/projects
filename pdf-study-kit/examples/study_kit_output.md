# Outline

*Source: database_normalization.pdf — 415 words, 4 sections*

## 1. Introduction to Normalization
*105 words*
- Database normalization is defined as the process of organizing columns and tables of a relational database to minimize data redundancy.
- A poorly normalized schema stores the same fact in many places, which permits those copies to disagree with one another.

## 2. Functional Dependency
*99 words*
- A candidate key is a minimal set of attributes that functionally determines every other attribute in the relation.
- A transitive dependency exists when a non-key attribute depends on another non-key attribute rather than on the key itself.

## 3. The Normal Forms
*89 words*
- First normal form requires that every attribute contain only atomic values, so a column may not hold a list.
- Each successive normal form eliminates a specific class of anomaly, and the forms are cumulative.

## 4. Decomposition and Trade-offs
*100 words*
- Analytical systems frequently denormalize deliberately, accepting redundancy in exchange for avoiding expensive joins at query time.
- Choosing a normal form is therefore an engineering trade-off rather than a rule to be followed blindly.


# Summary

*Source: database_normalization.pdf — 415 words, 4 sections*

- Database normalization is defined as the process of organizing columns and tables of a relational database to minimize data redundancy.
- An insertion anomaly is a situation where a fact cannot be recorded because some unrelated information is not yet known.
- A partial dependency is a dependency on only part of a composite candidate key.
- A transitive dependency exists when a non-key attribute depends on another non-key attribute rather than on the key itself.
- Identifying functional dependencies correctly is the prerequisite for every normalization step that follows.
- Second normal form requires first normal form and the removal of every partial dependency on a composite key.
- Third normal form requires second normal form and the removal of every transitive dependency between non-key attributes.
- Boyce-Codd normal form is a stricter version of third normal form in which every determinant must be a candidate key.

## Key terms

**fact**, **non-key attribute**, **removal**, **candidate key**, **composite key**, **non-key attributes**, **boyce-codd normal**, **stricter version**, **successive normal**, **specific class**, **decomposition**, **anomaly**

# Glossary

*Source: database_normalization.pdf — 415 words, 4 sections*

**deletion anomaly** — loss of one fact as a side effect of deleting another

**functional dependency** — constraint between two sets of attributes in a relation

**Boyce-Codd normal form** — stricter version of third normal form in which every determinant must be a candidate key

**Decomposition** — process of splitting one relation into several smaller relations

**star schema** — denormalized design commonly used in data warehouses


# Flashcards

*Source: database_normalization.pdf — 415 words, 4 sections*

**1.** What is **deletion anomaly**?

> loss of one fact as a side effect of deleting another

---

**2.** What is **functional dependency**?

> constraint between two sets of attributes in a relation

---

**3.** What is **Boyce-Codd normal form**?

> stricter version of third normal form in which every determinant must be a candidate key

---

**4.** What is **Decomposition**?

> process of splitting one relation into several smaller relations

---

**5.** What is **star schema**?

> denormalized design commonly used in data warehouses

---

**6.** A transitive dependency exists when a non-key
attribute depends on another ______ rather than on the key itself.

> non-key attribute

---

**7.** Second normal form requires first normal form and the ______ of every
partial dependency on a composite key.

> removal

---

**8.** A ______ is a minimal set of attributes that functionally
determines every other attribute in the relation.

> candidate key

---

**9.** Third normal form requires second normal form and the
removal of every transitive dependency between ______.

> non-key attributes

---

**10.** Boyce-Codd normal form is
a ______ of third normal form in which every determinant must be a candidate key.

> stricter version

---

**11.** Each ______ form eliminates a specific class of anomaly, and the forms are
cumulative.
4.

> successive normal

---

**12.** Attribute B is ______ on attribute A when each value of A is associated with
exactly one value of B.

> functionally dependent

---


# Practice Quiz

*Source: database_normalization.pdf — 415 words, 4 sections*

**1.** A transitive dependency exists when a non-key
attribute depends on another ______ rather than on the key itself.
   a) minimize data
   b) composite candidate
   c) relational model
   d) non-key attribute

**2.** Second normal form requires first normal form and the ______ of every
partial dependency on a composite key.
   a) key itself
   b) removal
   c) attribute rather
   d) composite candidate

**3.** A ______ is a minimal set of attributes that functionally
determines every other attribute in the relation.
   a) successive normal
   b) functional dependencies
   c) candidate key
   d) poorly normalized

**4.** Second normal form requires first normal form and the removal of every
partial dependency on a ______.
   a) non-key attributes
   b) minimize data
   c) composite key
   d) dependencies correctly

**5.** Third normal form requires second normal form and the
removal of every transitive dependency between ______.
   a) non-key attributes
   b) composite key
   c) relational database
   d) transitive dependency

**6.** ______ form is
a stricter version of third normal form in which every determinant must be a candidate key.
   a) attribute rather
   b) boyce-codd normal
   c) identifying functional
   d) composite key

**7.** Boyce-Codd normal form is
a ______ of third normal form in which every determinant must be a candidate key.
   a) dependencies correctly
   b) successive normal
   c) normalization step
   d) stricter version

**8.** Each ______ form eliminates a specific class of anomaly, and the forms are
cumulative.
4.
   a) identifying functional
   b) data redundancy
   c) successive normal
   d) removal

---

### Answer key

1. d  2. b  3. c  4. c  5. a  6. b  7. d  8. c