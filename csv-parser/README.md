# The CSV parser nobody writes

CSV looks like a format you can parse with one method call. That belief is why
it gets parsed wrong so often.

This is a character-level state machine — quoted commas, embedded newlines,
doubled quotes, CRLF, lone CR, ragged rows — held to `csv.reader`'s behaviour
by a differential test, with the `line.split(',')` baseline measured beside it
rather than described.

```
python3 difftest.py                     # 50,000 generated documents
python3 failures.py                     # where the naive split breaks, and how often
python3 -m unittest discover -q tests   # 22 tests
```

## Correctness

50,000 generated documents, zero disagreements with `csv.reader`.

The generator is aimed at the grammar, not at random bytes: a fifth of the
characters it emits are quotes, and its alphabet is the tokens that actually
break parsers — `"`, `""`, `"a,b"`, `"a\nb"`, `a"b`, `"ab"c`, bare `\r`.
Random text almost never produces an unbalanced quote followed by a
delimiter; this produces one every few hundred documents.

## What the naive split gets wrong

| cause | adversarial | realistic |
| --- | ---: | ---: |
| newline inside a quoted field split one row into two | 19.2% | 76.9% |
| blank line read as one empty field | 20.4% | — |
| escaped quote not unescaped | 15.3% | 0.4% |
| comma inside a quoted field invented a column | 10.4% | 22.7% |
| field value differs | 8.5% | — |
| quotes left in the value | 4.5% | — |
| **any failure** | **78.3%** | **100.0%** |

Each document is classified by the first cause that applies, so the row says
which feature did the damage rather than just that something did.

**Both those totals are rigged, in opposite directions.** 78.3% comes from a
generator built to break parsers. 100.0% comes from a "realistic" generator
whose free-text column draws from six values, three of which contain a comma
or a newline — if your data is cleaner than that, your failure rate is lower.
Quoting either number as *the* rate would be dishonest.

## The honest number is a curve

What matters is how often a field contains a comma or a newline, because one
mishandled field ruins the whole file. So vary that rate:

| p(field is hazardous) | measured per-file failure | 1−(1−p)^8 |
| ---: | ---: | ---: |
| 0.00 | 0.0% | 0.0% |
| 0.01 | 8.6% | 7.7% |
| 0.02 | 16.1% | 14.9% |
| 0.05 | 33.4% | 33.7% |
| 0.10 | 56.6% | 57.0% |
| 0.25 | 89.7% | 90.0% |
| 0.50 | 99.8% | 99.6% |

Measured tracks the binomial prediction within about a point, which is the
useful result: the per-file rate is not a property of the data mix at all, it
is just compounding. **A 1-in-100 per-field hazard is a 1-in-12 chance of
losing an eight-row file** — and nobody ships an eight-row file. At a thousand
rows, p=0.01 is a certainty.

That is the argument for not splitting on commas, and it does not require any
assumption about how messy your data is.

## One deliberate divergence: the BOM

`csv.reader` does not strip a byte-order mark. It is not supposed to — that is
the file's encoding layer, `encoding='utf-8-sig'`. But the consequence is
specific and nasty:

```python
>>> header = ref("﻿id,name\n")[0]
>>> "id" in header
False
```

The column is there. It is called `﻿id`, so every lookup of `"id"` fails,
and nothing raises. This parser strips a leading BOM by default and
`strip_bom=False` reproduces the `csv` behaviour exactly; both halves are
pinned by tests. A BOM anywhere other than the very start is left alone,
because there it is data.

## Two findings worth keeping

`newline=''` is not optional. Opening a file without it lets Python's
universal-newline translation rewrite CRLF *before* `csv` sees it, which
corrupts any CRLF that was inside a quoted field. The reference function in
`difftest.py` passes it for exactly that reason.

A blank line is a row with **no** fields, not a row with one empty field.
`csv` yields `[]` for a blank line and `['']` for a line holding one empty
quoted field, and code that writes `if not row: continue` depends on the
difference. My first version returned `['']` for both; the spot-check against
`csv` caught it on the sixth case.

## Where it matches `csv` even when `csv` is strange

Malformed input has no right answer, so the reference defines one and this
parser follows it. `a"b` keeps its quote — a quote is only special at the
start of a field. `"ab"c` becomes `abc`, the trailing text appended rather
than rejected. An unterminated quote swallows the rest of the file. None of
those are in RFC 4180; all of them are what `csv.reader` does, and agreeing
with the reference matters more than being principled alone.
