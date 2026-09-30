# Searching the Python standard library

An inverted index with BM25 over every public function and class docstring in
the standard library — 2,077 documents from 186 modules, 676,341 characters —
scored against the substring search it is supposed to beat.

```
python3 corpus.py      # harvest the corpus (committed, so results reproduce)
python3 evaluate.py    # the scores below
python3 sweep.py       # the parameter curve
```

The corpus is real text nobody wrote for a benchmark, and relevance is
checkable: if you ask for "read a zip archive" and `zipfile.ZipFile` is not in
the top ten, the search is wrong and there is nothing to argue about.

## Result

Sixteen hand-labelled queries, 60 relevance judgements:

| engine | p@10 | r@10 | MRR |
| --- | ---: | ---: | ---: |
| bm25 (b=0.25) | 0.194 | 0.559 | **0.625** |
| LIKE '%term%' | 0.181 | 0.509 | 0.480 |
| bm25 (b=0.75, textbook default) | 0.156 | 0.487 | 0.466 |

MRR is the number a developer feels — nobody reads past the first result that
works. BM25 puts a correct answer at rank 1 for nine of the sixteen queries
against the baseline's six, and scores 0 on four where it returns nothing
relevant at all.

## BM25 with its own default settings loses

That third row is the finding. With the parameters every tutorial hands you,
k1=1.5 and **b=0.75**, BM25 is worse than substring matching on all three
metrics. I did not expect that and went looking for the bug. There isn't one.

`b` controls how hard long documents are penalised. The premise is that length
means padding. In API documentation it means the opposite: the longest
docstrings are the thorough ones. At b=0.75 the ranker put
`argparse.Action` above `argparse.ArgumentParser` for "parse command line
arguments", because `ArgumentParser` documents every keyword argument and
gets taxed for it.

The whole curve, k1 fixed at 1.5:

| b | p@10 | r@10 | MRR |
| ---: | ---: | ---: | ---: |
| 0.00 | 0.175 | 0.520 | 0.622 |
| 0.25 | 0.194 | 0.559 | 0.625 |
| 0.50 | 0.175 | 0.521 | 0.511 |
| 0.75 | 0.156 | 0.487 | 0.466 |
| 1.00 | 0.144 | 0.466 | 0.393 |

Monotone decline from 0.25 onward, MRR falling 37% across the range. k1 barely
matters by comparison — anywhere from 0.5 to 1.5 gives the same answer.

**The honest caveat:** b was tuned on the same sixteen queries the result is
reported on, so 0.625 is optimistic and the peak's exact location is not
trustworthy. The monotone shape either side of it, and the mechanism behind
it, are. The defensible claim is "b=0.75 is wrong for this corpus", not
"b=0.25 is right".

## Where it still loses

Per-query, BM25 returns nothing relevant for four of the sixteen:

```
                                             bm25   LIKE
substitute text with a regular expression    0/2    0/2
iterate over every combination of items      0/4    0/4
spread work over multiple processes          0/4    0/4
sort using a custom comparison function      0/3    0/3
show the difference between two sequences    2/7    4/7
```

The first four are vocabulary mismatch, and no amount of parameter tuning
reaches them. `re.sub` says "replacing" where the query says "substitute";
`itertools.combinations` says "combinations" where the query says
"combination". A stemmer would close the second and an alias list the first.
The index has neither, and the baseline fails these too — this is a corpus
problem, not a ranking one.

The fifth is worth admitting separately: both put a correct answer first, but
the baseline retrieves twice as many of them, because "diff" is a substring of
`difflib` and substring matching gets partial-word matches for free where a
token index cannot.

## The corpus fought back

Three things the harvester got wrong, all caught by an assertion that every
labelled document exists in the corpus rather than by reading output:

`inspect.isfunction` silently drops half the interesting standard library.
`random.sample` is a bound method of a module-level `Random` instance and
`functools.cmp_to_key` is a C builtin; neither is a function. `isroutine`
catches all three kinds.

`concurrent.futures.ProcessPoolExecutor` is not in `vars(concurrent.futures)`
at all. The module resolves it lazily through `__getattr__`, so it does not
exist until something asks for it.

`multiprocessing.Pool` has a 29-character docstring and `cmp_to_key` has 45,
both under the 60-character floor. They are legitimately absent, so they were
removed from the judgement set rather than counted as misses the ranker could
never have scored.

Without the validation step all three would have shown up as the ranker
failing, and the conclusion would have been wrong in a way no amount of
staring at precision numbers would reveal.
