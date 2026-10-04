# Recommender evaluation: what a random split actually costs

Three recommenders, three split protocols, and a controlled experiment showing
that leaking the future does not merely inflate the score — **it changes which
model you would ship.**

```
python3 evaluate.py    # the three protocols, and why they are not comparable
python3 controlled.py  # the controlled leak experiment and the drift sweep
python3 -m unittest discover -q tests   # 27 tests
```

## The data is generated, and here is why that is the right call

The repository's real ratings table holds 24 rows, and no public interaction
dataset is reachable from this environment. But the claim under test is about
an evaluation *protocol*, not about a catalogue — so a generator is better
than a borrowed dataset, because it exposes a dial for the one ingredient
responsible: how much item popularity moves over time.

At drift = 0 the catalogue is stationary and the leak has nothing to leak.
That is the control, and without it "the random split inflates scores" would be
an assertion rather than a mechanism.

Tuning that dial took two tries. With a strict Zipf appeal (`1/rank^1.1`) the
head items are ~350× the tail, so no drift setting moved the chart at all —
the top-ten overlap between the first and last quarter stayed at 9/10 for
every value. Flattening the exponent to 0.5 and sweeping the bump multiplier
gave a dial rather than a switch: overlap runs **9, 9, 6, 1, 0** for drift
0, 0.5, 1, 2, 4.

## First: the comparison everyone makes does not work

| protocol | popularity | recent popularity | item-item CF |
| --- | ---: | ---: | ---: |
| random | 0.100 | 0.100 | 0.097 |
| leave-last-out | 0.036 | 0.034 | 0.038 |
| temporal | **0.149** | 0.142 | 0.133 |

Read naively this says the temporal split is *easiest*, which would make the
leak beneficial. It is not. The three protocols pose three different tasks:

| protocol | relevant items per test user | cold-start test users |
| --- | ---: | ---: |
| random | 4.47 | 0% |
| leave-last-out | 1.00 | 0% |
| temporal | 16.67 | **58%** |

Recall@10 against one relevant item is a much easier number than recall@10
against seventeen, and a model facing 58% users it has never seen is not doing
the same job. Comparing recall across these rows measures the protocols'
bookkeeping, not the leak. Papers do this.

## The controlled experiment

Change one thing. The test set is a random quarter of the post-cutoff
interactions and never moves. Training is either everything before the cutoff
(**honest**, verified to contain zero test-period rows) or a sample of **the
same size** that may also draw on the rest of the test period (**leaky**,
15.9% contemporaneous rows). Same test items, same training volume, same
model, same metric.

| model | honest | leaky | inflation |
| --- | ---: | ---: | ---: |
| popularity (global) | 0.138 | 0.159 | 1.16× |
| popularity (recent 14d) | 0.131 | 0.165 | **1.25×** |
| item-item CF | 0.131 | 0.148 | 1.13× |

And the mechanism check — inflation against the drift dial:

| drift | popularity | recent popularity | item-item CF |
| ---: | ---: | ---: | ---: |
| 0.0 | 1.07× | 1.00× | 1.02× |
| 0.5 | 1.08× | 1.23× | 1.04× |
| 1.0 | 1.16× | 1.25× | 1.13× |
| 2.0 | 1.22× | 1.14× | 1.34× |
| 4.0 | **1.60×** | 1.14× | **1.64×** |

At zero drift the inflation is gone. That is the control passing: the leak only
pays when there is temporal structure to leak.

## The result that matters

Inflation that lifted every model equally would be harmless — you would still
pick the same one. It does not.

Over 25 seeds at drift = 1, the honest and leaky protocols **choose different
winners 15 times (60%)**.

```
honest protocol would ship:  global popularity 20,  recent popularity  5
leaky  protocol would ship:  recent popularity 14,  global popularity 11
```

The bias has a direction and a reason. The leaked signal *is* recency
information, so it rewards whichever model is best positioned to exploit
recency — here, the 14-day popularity window. Evaluate on a random split and
you will systematically prefer the recency-sensitive model, deploy it, and
watch it underperform the boring global baseline it beat offline.

## A negative result

**Item-item collaborative filtering never wins.** Not under the honest
protocol, not under the leaky one, at no drift setting. On a catalogue this
dense (3.6%) with this many cold-start users, co-occurrence has little to add
over counting. That is pinned by a test so it does not quietly disappear if
the numbers shift.

The honest reading is that this says more about the generator than about CF —
a log built from popularity-weighted sampling has no latent taste structure
for CF to find. Which is itself the caveat to carry: a benchmark can only
reward a model for exploiting structure the data actually contains.

## Two bugs worth recording

**The first leaky training set did not leak.** I built it by sampling
everything *except* the test rows — which deletes the test period's other
rows, precisely the thing a random split leaks. It reported inflation of
1.00× at every drift setting. A measurement of exactly 1.00 across five
settings is not a finding, it is a broken harness.

**The drift dial did nothing**, for the Zipf reason above, and the first
version of the sweep would have reported "drift has no effect on inflation"
with a straight face.

Both were caught by having a control to check against. Neither would have been
caught by the tests passing.

Stdlib only.
