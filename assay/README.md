# assay

A data quality gate that also audits its own rules.

Point it at a CSV and a rule suite: it separates the good rows from the bad,
writes the bad ones to a quarantine file, and exits non-zero so it can stand in
front of a pipeline. That part is ordinary.

The part that isn't: `assay audit` breaks your data on purpose — in the ways
real pipelines actually break — and tells you which corruptions your rules
**fail to notice**.

No dependencies. Python 3.11+, stdlib only, including the TOML parser.

```bash
python3 -m assay.cli check examples/trips.toml
python3 -m assay.cli audit examples/states.toml
```

## Why audit the rules

A rule suite tells you whether the data is bad. Nothing tells you whether the
suite is any good — and a suite that passes on garbage is worse than no suite,
because it manufactures confidence. The failure is silent by construction: the
gate is green, so nobody looks.

So `audit` corrupts a known-good dataset in known ways — a units change
upstream, two columns crossed in a join, a partial load that drops rows, an ETL
that starts emitting blanks — and reports which ones got through.

Run against the rule suite in `examples/states.toml`, written the way suites
usually are, covering problems someone already hit:

```
  caught  duplicate_rows     3% of rows appended again
  caught  drop_rows          20% of rows silently missing
  caught  blank_out          5% of State emptied
  MISSED  pad_whitespace     10% of State padded with spaces
  caught  unknown_category   5% of State set to 'UNSPECIFIED'
  MISSED  truncate_values    4% of State truncated
  MISSED  swap_columns       State and StateCode swapped
  MISSED  blank_out          5% of Population2020 emptied
  MISSED  shift_decimal      4% of Population2020 multiplied by 10
  caught  rescale            all of Population2020 x1.609 (units change)
  caught  inject_outlier     one value in Population2020 x1000
  caught  corrupt_type       3% of Population2020 replaced with text
  caught  swap_columns       Population2020 and MedianHouseholdIncome swapped
  detection score: 62% (8/13)
```

Seven rules, all passing on the real data, and five corruptions walk straight
through.

## The two findings worth the trouble

**A plausible range cannot catch a decimal shift.** The suite bounds state
population to `[100,000, 60,000,000]` — a sensible range that holds for all 51
rows. Shift 4% of the values one decimal place:

| State | Real | ×10 | Inside the range? |
| --- | --- | --- | --- |
| Iowa | 3,190,369 | 31,903,700 | yes |
| Maine | 1,362,359 | 13,623,600 | yes |

Both pass. The national total moves from 331,449,281 to 372,423,853 — **+12.4%**
— and every per-row rule reports clean, because ten times a small state is a
perfectly plausible large state. Per-row checks are structurally blind to any
error that stays individually plausible.

**A column with no `not_null` rule has no coverage against becoming empty.**
Every rule except `not_null` skips nulls on purpose: if `range` flagged empty
cells, every optional column would need a null exemption and the suite would
drown in false positives. The cost is that `population_plausible` and
`population_is_number` both sat there while 5% of populations were emptied, and
neither said a word. That is a structural consequence of a deliberate design
choice, not a bug — which is exactly the kind of thing you do not find by
staring at the rules.

## The audit changing the tool

The decimal-shift miss isn't fixable with a better range. It needs a rule of a
different shape — an aggregate, not a per-row check. So the finding produced
`control_total`, which reconciles a column's sum against a known figure, the
way ETL reconciliation has always worked:

```toml
[[rule]]
id = "population_control_total"
kind = "control_total"
column = "Population2020"
stat = "sum"
expected = 331449281
tolerance = 0.005
```

`examples/states_hardened.toml` adds that plus five rules closing the other
gaps. The score moves **62% → 92%** (8/13 → 12/13), and the hardened suite still
passes cleanly on the real data — the point being that it catches more without
crying wolf. A test asserts both numbers so the claim cannot quietly rot.

The one remaining miss is honest: truncating `State` to "Alabam" goes unnoticed,
because nothing constrains state *names*. Catching it needs a reference list —
`foreign_key` against a dimension table — which is a rule the suite could have
and doesn't.

## Checking real data

`examples/trips.csv` is 6,041 real-shaped bikeshare rows. The gate finds 45
duplicate ride ids and 99 trips that end at the exact second they start, and
quarantines 143 rows:

```bash
python3 -m assay.cli check examples/trips.toml \
    --clean good.csv --quarantine bad.csv
echo $?        # 1
```

That suite scores **71%**, blind to `drop_rows` — 20% of the data vanishing
with nothing to notice, because it has no `row_count` rule.

## Rules

| kind | checks |
| --- | --- |
| `not_null` | the column is never empty (`""`, `NA`, `null`, `-` all count as empty) |
| `unique` | a column or composite key has no repeats |
| `in_set` | the value is one of an allowed list (case-insensitive by default) |
| `range` | numeric, within `min`/`max` |
| `matches` | the **whole** value matches a regex |
| `is_type` | parses as int / float / date / datetime |
| `no_padding` | no leading or trailing whitespace |
| `compare` | two columns in the same row, e.g. `started_at < ended_at` |
| `foreign_key` | the value exists in a reference dataset |
| `row_count` | the table has between `min` and `max` rows |
| `columns_exist` | the named columns are present |
| `control_total` | `sum`/`mean`/`min`/`max`/`count` lands within a tolerance of a known figure |

Rules are `severity = "error"` (fails the run, quarantines the row) or
`"warn"` (reported, never fails a gate). A warning that stops a pipeline is not
a warning, so warnings do not count as catching anything in an audit either.

## Design decisions

**No expression language, no `eval`, no plugin hook.** This runs in CI against
files somebody else wrote. The least interesting way for a data quality gate to
fail is by executing something it read out of a config file.

**Spec errors are fatal, never skipped.** An unknown rule kind, a misspelled
field, a duplicate rule id — all refuse to start. A gate that silently drops a
rule it could not parse reports a clean run over checks that never executed,
which is the same silent-green failure the audit exists to expose.

**Exit codes are the product.** `0` clean, `1` a rule failed, `2` the suite or
the file is broken. `audit --fail-under 0.8` gates on coverage of the rules
themselves.

**Colour off when stdout isn't a terminal**, because ANSI escapes in a captured
CI log are noise.

## Tests

```bash
python3 -m unittest discover -s tests
```

58 tests, stdlib `unittest`. The ones that matter are the ones asserting a rule
does **not** fire — a gate that flags everything is as useless as one that flags
nothing, and false positives are how a team learns to ignore the gate. Also
covered: that mutations never touch the caller's data, that an audit counts a
corruption which *deepens* an existing failure (real data already fails rules at
baseline), and that `drop_rows` is only visible to a table-level rule, since
per-row violations go *down* when rows vanish.

The CLI tests run it as a subprocess and assert the exit codes, because the
exit code is the interface.
