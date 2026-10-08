# A portfolio that checks itself

One command re-derives every number this repository claims and exits non-zero
if any of them has stopped being true.

```
python3 check.py                        # all 31 claims, ~30 seconds
python3 check.py --project ab-test      # one project
python3 check.py --quiet                # failures and the summary only
python3 -m unittest discover -q tests   # 15 tests, on the checker itself
```

```
31 of 31 claims reproduce
```

## Why two checks per claim

Every claim is verified twice, and both must pass:

**PROSE** — the claimed string is still present in that project's README.
**CODE** — running a registered snippet still prints exactly that string.

Each catches a different rot. Code drifting away from documentation that was
never updated is the obvious one. The other is a README edited to a number the
code never produced — which a test suite cannot catch, because the prose is
not code, and which no amount of `assert` in the project itself would notice.

A claim is therefore three things: the project, the exact substring as it
appears in the README, and a snippet that recomputes it.

## What it checks

31 claims across 12 projects:

| project | claims checked |
| --- | ---: |
| anomaly-detection | 4 |
| integer-programming | 4 |
| ab-test | 3 |
| docstring-search | 3 |
| forecast-baselines | 3 |
| nearest-neighbour | 3 |
| record-linkage | 3 |
| rate-limiter | 2 |
| recommender-eval | 2 |
| regex-nfa | 2 |
| assay | 1 |
| csv-parser | 1 |

These are the load-bearing numbers — the ones a reader would quote. The
z-score ceiling of 2.846 at n=10. The 2.00× a fixed-window rate limiter
admits. The 627.50 LP bound against the 635.00 integer optimum and the 16.54%
cost of rounding between them. New York to London at 5570.2 km. The 23.7%
pair completeness that a first-letter blocking key silently leaves you with.

## What it deliberately does not check

Six claims are excluded, each with its reason recorded in `SKIPPED` so the
gaps are a stated decision rather than a silence:

| claim | why not |
| --- | --- |
| regex-nfa, 12,072× faster than `re` | wall-clock ratio: a property of this machine, not of the code |
| nearest-neighbour, 375.4× speedup | wall-clock timings; the operation counts would be checkable, the times are not |
| sqlite-concurrency-lab, 2.9× WAL throughput | races against real disk and scheduler; the loss figure varies by run |
| query-planner-lab, +39% regression | wall-clock query times |
| thicket, 5.1× fewer trees | requires scikit-learn, not installed in this checkout |
| bikeshare-data-cleaning, 14× station spread | pandas pipeline, not importable without pandas |

Pinning a timing would produce a check that fails for reasons having nothing
to do with the code, and a suite that cries wolf gets switched off. The
honest move is to exclude them by name and say so.

## Subprocesses, not imports

Each snippet runs in its own subprocess with its project directory as the
working directory. That is not a workaround. These projects import each other's
modules by bare name — `series`, `models`, `evaluate`, `detectors` and `lp`
each exist in more than one of them — so loading them into one interpreter
would collide. Forty independent packages that were never designed to share a
`sys.path` cannot be made to.

They run in parallel, eight at a time, because the whole thing is only worth
having if it is quick enough to run before a commit. 31 claims in about 30
seconds.

## Testing the tester

A verifier that cannot fail is worse than none — it prints a green line that
means nothing. So most of the 15 tests construct claims that *should* fail and
assert that they do: a wrong number, a snippet whose output has drifted, a
README edited away from correct code, a snippet that raises, a project that
does not exist. Plus registry hygiene: no duplicate claims, every project has
a README, every exclusion names a real directory and gives a reason, and no
claim is a string so short it would match prose by accident.

The checker found a failure on its very first run. It was my own bug — an
over-escaped regex in the `assay` snippet, which counts that project's tests —
not a rotted claim. Still the right first result: the mechanism reported a
discrepancy rather than quietly passing.

Stdlib only.
