# Anomaly detection, and what no detector can see

Six detectors on 1,438 hours of bike-trip counts. Two closed-form results
about why the z-score fails, and one about a limit that holds whatever
algorithm you pick.

```
python3 masking.py         # the z-score's hard ceiling
python3 evaluate.py        # precision/recall on injected anomalies
python3 detectability.py   # what cannot be detected at all
python3 -m unittest discover -q tests   # 31 tests
```

The series is hourly trip counts from the Day 13 project's committed CSV.
Those rides are generated — that project's README says so — but the daily
cycle is structure the file genuinely contains: mean trips peak at 9.57 at
08:00 and bottom out at 0.53 at 03:00, an 18.8× swing. Day 29 showed the
*daily* totals have no weekly structure at all; the *hourly* series does, and
that cycle is what the detectors have to cope with.

## 1. The z-score has a ceiling below your threshold

A z-score divides by a standard deviation computed from data that includes the
point being tested, so an extreme point inflates its own denominator. The cap
is exact, and both forms are verified against measurement to six decimals:

| | max \|z\| for one outlier |
| --- | --- |
| sample sd (ddof=1) | **(n−1)/√n** |
| population sd (ddof=0) | **√(n−1)** |

| n | 5 | 10 | 11 | 20 | 50 | 100 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| ceiling | 1.789 | **2.846** | 3.015 | 4.249 | 6.930 | 9.900 |

At the usual threshold of 3, **a ten-point window can never flag anything**.
Its ceiling is 2.846, however extreme the outlier. A daily metric reviewed
over the last ten days sits exactly there.

## 2. Two anomalies hide each other

For k identical outliers among n−k identical normal points, the z-score of
each is

```
z = sqrt((n - k)(n - 1) / (k * n))
```

which reduces to (n−1)/√n at k=1. The outlier *magnitude cancels entirely* —
making the anomaly bigger does not help at all.

At n=16 one outlier scores 3.750 and is flagged; two score 2.562 and are not.
Adding a second anomaly hides the first. The window sizes where that happens
at z>3 are exactly **n = 11 to 20**.

My first attempt at this demo used n=200, where one outlier scores 14.07 and
two score 9.92 — both far above 3, nothing masked, the demo proved nothing.
The closed form is what identified the window where masking actually bites.

## 3. Detectors blind to the cycle flag the cycle

Share of each detector's flags that land on a rush hour (07–09, 16–18):

| detector | flags | rush-hour share |
| --- | ---: | ---: |
| z-score | 10 | **90%** |
| modified z (MAD) | 76 | 84% |
| IQR fence | 28 | 89% |
| seasonal + MAD (centre only) | 152 | 63% |
| seasonal, per-phase scale | 86 | **0%** |

Centring each hour on its own median is not enough. These are counts, so the
variance is seasonal too — the 08:00 per-phase scale is 4.45 against a pooled
residual scale of 1.483. Pooling one scale across all 24 phases
under-estimates the spread at the peaks, and that detector flags **more**
points than the raw z-score did. A seasonal adjustment has to cover both
moments.

## 4. Scored on injected anomalies

36 injected anomalies in 1,438 points: 12 global spikes, 12 contextual spikes
(12 trips at 03:00 — ordinary at 08:00), 12 dropouts (zero trips at 08:00 —
ordinary at 03:00).

| detector | flags | precision | recall | F1 |
| --- | ---: | ---: | ---: | ---: |
| z-score | 12 | 100.0% | 33.3% | 0.500 |
| modified z (MAD) | 97 | 24.7% | 66.7% | 0.361 |
| IQR fence | 38 | 31.6% | 33.3% | 0.324 |
| seasonal + MAD | 152 | 23.7% | 100.0% | 0.383 |
| seasonal, per-phase scale | 106 | 22.6% | 66.7% | 0.338 |
| **seasonal, Poisson scale** | 36 | **75.0%** | **75.0%** | **0.750** |

Recall by kind:

| detector | global | contextual | dropout |
| --- | ---: | ---: | ---: |
| z-score | 12/12 | 0/12 | 0/12 |
| modified z (MAD) | 12/12 | 12/12 | 0/12 |
| IQR fence | 12/12 | 0/12 | 0/12 |
| seasonal + MAD | 12/12 | 12/12 | 12/12 |
| seasonal, per-phase scale | 12/12 | 12/12 | 0/12 |
| seasonal, Poisson scale | 12/12 | 12/12 | 3/12 |

**A caution about F1.** The z-score places second on F1 while missing
two-thirds of the anomalies, because perfect precision on the easy third beats
broad coverage. If what you care about is a dropout — a payment outage, a
dead ingest pipeline — the z-score's F1 of 0.500 is worthless: it finds none
of them, at any threshold.

**And a real trade-off, not a bug.** Per-phase scaling eliminates rush-hour
false alarms and simultaneously goes blind to dropouts *at those same hours*,
because the scale it earns there (4.45) puts a zero only 2.36 away instead of
7.08. Silencing the false alarms and seeing the dropout are the same knob
turned in opposite directions.

## 5. The limit no detector escapes

The Poisson detector's 3-of-12 dropout recall is not a tuning failure. For
event counts at rate μ, a complete outage sits exactly

```
μ / sqrt(μ) = sqrt(μ)
```

standard deviations below the mean. So a total outage is visible at k sigma
only when **μ ≥ k²** — at k=3, nine events per interval.

In this series exactly **one hour of twenty-four** clears that bar: 08:00, at
9.57 trips an hour. Twenty-three hours a day, an hour-long complete outage is
mathematically inside the noise, and no choice of algorithm recovers it.

Aggregate to a day and the rate is 96.9 trips, so a full day of outage is
√96.9 = **9.8 sigma** — trivially visible.

Choosing the aggregation window is the actual design decision. Picking a
cleverer detector at the wrong window cannot recover information that is not
in the bucket.

## A bug my own tests caught

The empty-input test crashed every MAD-based detector: `statistics.median([])`
raises. Guarding `mad()` and each `flag()` against short input fixed it. Worth
noting because every one of these detectors had already produced a full,
plausible results table before anyone passed it an empty list.

Stdlib only.
