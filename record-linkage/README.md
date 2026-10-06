# Record linkage: the normaliser you should try first

Jaro-Winkler from the definitions, blocking, and a hand-labelled truth set —
and the uncomfortable finding that on real messy data the similarity score
contributes nothing.

```
python3 evaluate.py                     # blocking, the rule, the sweep
python3 -m unittest discover -q tests   # 31 tests
```

## The data

44 distinct spellings of 10 stations — the actual values of
`start_station`/`end_station` in `bikeshare-data-cleaning/data/trips_raw.csv`.
The rides there are generated, but the corruption patterns are the ones that
project documents as real: inconsistent case, padded whitespace, and
abbreviations (`Pk`, `St.`).

The truth map is written by hand, by reading all 44 strings. Deriving it by
normalising would score the matcher against its own normaliser, which is no
test at all. `validate()` asserts the map covers exactly the strings the file
contains, so a new spelling fails loudly instead of vanishing from the
denominator.

## Jaro-Winkler contributes nothing here

```
normalisation alone, no similarity score at all:
  precision 1.000   recall 1.000   F1 1.000
```

Lowercase, collapse whitespace, strip punctuation, expand abbreviations — and
the 44 spellings collapse to exactly 10 groups, one per station, none mixing
two stations. There is no residual error for a fuzzy matcher to reduce.

This is the finding I'd lead with. The corruption in this data is
**systematic**, and systematic corruption is fixed by rules. Reaching for a
similarity threshold first means tuning a parameter to approximate something a
four-line function does exactly.

## Blocking sets a ceiling on recall

Blocking only compares records sharing a cheap key. Two numbers describe it,
and reporting only the first is the standard mistake:

| scheme | pairs | reduction | pair completeness |
| --- | ---: | ---: | ---: |
| none (all pairs) | 946 | 0.0% | 100.0% |
| **first letter, raw** | 77 | **91.9%** | **23.7%** |
| first letter, normalised | 116 | 87.7% | 100.0% |
| first 3 chars, normalised | 76 | 92.0% | 100.0% |
| sorted token initials | 76 | 92.0% | 100.0% |
| length bucket | 224 | 76.3% | 100.0% |

Blocking on the raw first letter saves 91.9% of the comparisons and silently
throws away **76% of the true matches** — `'  Krog Street Market '` starts
with a space, `'KROG STREET MARKET'` with `K`, so they are never compared. The
normalised key gets a *better* reduction with nothing lost.

Pair completeness is a hard ceiling. A true pair that blocking discards cannot
be recovered by any threshold or any matcher, and the recall curve will simply
top out with no indication why. A test asserts that recall never exceeds
completeness across the whole sweep.

## Where the similarity score earns its keep

So a harder set: the same 10 names with single-character typos
(substitution, deletion, insertion, adjacent transposition) plus six **decoy**
entities whose names sit close to a real one — `Grand Park` vs `Grant Park`,
`Ponce City Mall` vs `Ponce City Market`. 55 records, 16 entities, 96 true
pairs. Generated from a fixed seed; the decoys are what make a threshold a
trade-off instead of a free parameter.

```
the same normalisation rule on the harder set:
  precision 0.000   recall 0.000   F1 0.000
```

Rules cannot reach a typo. Now the sweep, with no blocking:

| threshold | pairs | precision | recall | F1 |
| ---: | ---: | ---: | ---: | ---: |
| 0.65 | 288 | 33.3% | 100.0% | 0.500 |
| 0.75 | 144 | 66.7% | 100.0% | 0.800 |
| 0.80 | 124 | 76.6% | 99.0% | 0.864 |
| **0.90** | 110 | 82.7% | 94.8% | **0.883** |
| 0.95 | 75 | **98.7%** | 77.1% | 0.865 |
| 1.00 | 0 | 0.0% | 0.0% | 0.000 |

That is the trade-off, stated in the form a decision needs: 0.75 finds every
duplicate and one in three of its matches is wrong; 0.95 is right 98.7% of the
time and misses a quarter of them. Which you want depends on whether a missed
duplicate or a wrong merge costs more — and a wrong merge is usually harder to
undo.

## Blocking on the harder set, and what it costs

| scheme | pairs | reduction | pair completeness |
| --- | ---: | ---: | ---: |
| first letter, normalised | 192 | 87.1% | 100.0% |
| first 3 chars, normalised | 98 | 93.4% | **76.0%** |
| sorted token initials | 86 | 94.2% | **68.8%** |
| length bucket | 353 | 76.2% | 87.5% |

The scheme that was lossless on the real data loses a quarter of the matches
once typos reach the blocking key itself: `Altantic Station` normalises to
`alt…` and `Atlantic Station` to `atl…`, so they never meet.

The cost is measurable. Best F1 with that blocking is **0.774**; with no
blocking, **0.883**. Blocking bought a 93% cut in comparisons for 0.11 of F1.
With the blocking in place the threshold is also inert — F1 is a flat 0.753
from 0.50 all the way to 0.85, because the blocking has already done the
discriminating. A flat sweep is a sign the knob you are turning is not the one
that matters.

## Validation

Jaro and Jaro-Winkler are checked against the standard published values:
MARTHA/MARHTA 0.944 and 0.961, DIXON/DICKSONX 0.767 and 0.813,
JELLYFISH/SMELLYFISH 0.896, DWAYNE/DUANE 0.822 and 0.840, CRATE/TRACE 0.733.
The match window is `floor(max(len)/2) - 1`, not `max(len)/2` — the
off-by-one changes scores on short strings and is the usual implementation
bug.

Stdlib only.
