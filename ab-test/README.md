# An A/B test calculator that refuses to lie

Every experiment simulated here is an A/A test: both arms are drawn from the
same distribution, so there is no effect to find and **every "significant"
result is a false positive**. The nominal rate is 5%.

```
python3 peeking.py                      # what repeated looks cost
python3 sequential.py                   # the fix, calibrated and checked
python3 -m unittest discover -q tests   # 26 tests
```

## Peeking

10% base rate, 1,000 users per arm per day, 14 days, 20,000 simulated
experiments per row. Stop at the first look where p < 0.05.

| stopping rule | looks | false positives |
| --- | ---: | ---: |
| one look, at the end | 1 | 5.1% |
| look on day 7 and day 14 | 2 | 8.2% |
| look every other day | 7 | 16.6% |
| look every day | 14 | **22.0%** |

Checking a dashboard every morning and shipping the first time it goes green
is not a 5% test. It is a test with fourteen chances to be wrong, and it takes
them.

## The part that does the actual damage

Among the 4,402 false positives from daily looks:

```
mean |observed lift|  18.2%   (the true lift is 0)
mean stopping day      4.9    of 14
```

The false positives do not squeak past the line. They report an 18% lift that
does not exist, and they report it on day 5. That is not a coincidence — it is
the mechanism. You stop exactly when noise is at its most flattering, so the
stopping rule selects for overstatement. A result that is both wrong and
impressive is far more likely to get shipped than one that is merely wrong.

## The fix, calibrated rather than quoted

Raise the bar so the whole sequence of looks spends 5% in total instead of 5%
each. One constant z threshold, applied at every look, found by bisection on
simulated false-positive rate:

```
naive threshold      z = 1.960   (5% at one look)
calibrated threshold z = 2.594
```

| | false-positive rate |
| --- | ---: |
| daily looks, naive z, held-out seed | 21.7% |
| daily looks, calibrated z, calibration seed | 4.9% |
| **daily looks, calibrated z, held-out seed** | **5.2%** |
| one look at the end, naive z (reference) | 5.1% |

The held-out row is the only one that counts. A threshold calibrated and
evaluated on the same draws passes by construction, which is why the
calibration seed and the evaluation seed are different numbers.

## Two checks that the method is sound

**Calibrating for a single look returns z = 1.969.** The procedure is told
nothing about 1.96; it bisects on simulated rates. Recovering the analytic
answer it was never given is the evidence that the machinery works.

| looks | calibrated z | naive FPR |
| ---: | ---: | ---: |
| 1 | 1.969 | 5.2% |
| 2 | 2.164 | 8.1% |
| 7 | 2.477 | 16.4% |
| 14 | 2.594 | 22.0% |

**The bar rises steeply, then flattens.** Going from 1 look to 2 costs 0.20 of
z; going from 7 to 14 costs 0.12, despite also being a doubling. So "just peek
less often" buys back much less than the first peek cost you — halving your
looks is close to free for the experimenter and close to useless for the
error rate.

## What the correction costs

A fix that cost nothing would be a fix that did nothing.

| true lift | one look at the end | daily looks, corrected |
| ---: | ---: | ---: |
| 5% | 27.9% | 20.1% |
| 10% | 78.1% | 65.2% |
| 20% | 99.9% | 99.8% |

Power drops by about 13 points at a 10% lift. What you buy is the right to
stop early when the effect is real — the sequential test often concludes well
before day 14, and for a large effect it loses essentially nothing. The trade
is worth making deliberately, which is why both columns are here.

## On the simulation itself

The sampler is exact. Looping over Bernoulli trials would be exact but far too
slow for millions of experiments, and a normal approximation would be fast
while changing the tail behaviour — which is the thing being measured. So
`BinomialSampler` precomputes the binomial CDF once by the pmf recurrence
(`math.comb(1000, 500)` is a 300-digit integer; the ratio form never leaves
float range) and samples by bisecting a uniform. Exact draws, O(log n) each.

`z_score` returns 0.0 rather than raising when both arms have zero
conversions. That is not defensive padding — it is day one of any low-rate
test, and a statistic that divides by zero there is one nobody can run.

Stdlib only.
