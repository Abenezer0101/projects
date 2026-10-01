# A regex engine that cannot backtrack

Python's `re` is a backtracking engine. So are Perl's, Java's, and
JavaScript's. That buys backreferences and lookaround, and it costs
exponential time on patterns that look completely ordinary.

This is the other construction — Thompson 1968. The pattern becomes an NFA,
and the NFA is simulated while carrying the *set* of currently reachable
states. The set can never be larger than the machine, so one pass over an
n-character input through an m-state machine is O(nm) and no input makes it
worse.

```
python3 difftest.py                     # 76,744 pairs against re.fullmatch
python3 bench.py                        # the exponential blowup, timed
python3 -m unittest discover -q tests   # 19 tests
```

## Correctness

`re` is the oracle. 76,744 generated pattern/input pairs, zero disagreements.
814 patterns were skipped — either `re` rejects them, or they use lazy or
possessive quantifiers, which are out of scope for the reason below.

Generated patterns rather than hand-written ones, because hand-written cases
test what the author already thought of.

## Speed

`a?` repeated n times, followed by `a` repeated n times, matched against n
letters `a`. Every `a?` can match or skip, so a backtracker explores 2^n
assignments to discover that exactly one works.

| n | states | re (s) | nfa (s) | ratio |
| ---: | ---: | ---: | ---: | ---: |
| 14 | 43 | 0.000486 | 0.000105 | 5× |
| 18 | 55 | 0.012576 | 0.000220 | 57× |
| 22 | 67 | 0.216342 | 0.000266 | 813× |
| 24 | 73 | 0.555049 | 0.000165 | 3,374× |
| 26 | 79 | 2.722790 | 0.000226 | **12,072×** |
| 28 | 85 | not asked | 0.000185 | |
| 30 | 91 | not asked | 0.000223 | |

`re` quadruples with every +2 and is not asked past n=26. The NFA column does
not move, because 91 states over 30 characters is 2,730 state-steps and that
is all it ever was.

Below n=12 the NFA is slower. Python-level object traversal loses to a C
implementation until the exponent catches up, which it does at n=12.

## Possessive quantifiers are not regular expressions

The differential test found this, and it changed the design.

```python
>>> re.fullmatch("a*+a", "aa")
None
```

"aa" is in the language `a*a`. Any engine answering "is this string in this
language" must say yes. `re` says no, because `a*+` consumes both characters
and is forbidden from giving one back. That is a statement about a
backtracking procedure, not about a regular language, and there is no NFA that
reproduces it.

Lazy quantifiers are different and harmless: `a*?a` and `a*a` accept exactly
the same strings and differ only in which span gets captured. For a boolean
matcher the distinction is invisible.

So this engine refuses `a+?` and `a*+` by name instead of parsing them as two
stacked operators — which is what it did at first, silently answering a
different question and producing 115 disagreements before the rejection was
added.

```
ValueError: stacked quantifier *+ at position 3: lazy and possessive
quantifiers are not supported
```

## Supported

Literals, `.`, `*`, `+`, `?`, `|`, grouping, `[abc]`, `[^abc]`, `[a-z]`, and
backslash escapes. Semantics are `re.fullmatch`.

Not supported, by construction rather than by omission: backreferences and
lookaround. Neither is regular, and neither can be built from an NFA — which
is precisely why the engines that do support them are the ones that blow up.

## Layout

```
nfa.py        tokenize -> shunting-yard -> Thompson construction -> simulate
difftest.py   generate patterns, demand agreement with re
bench.py      the exponential case, timed against re
tests/        19 tests, every case asserted against re rather than a literal
```
