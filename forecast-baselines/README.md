# Forecasting with baselines that are allowed to win

Seven forecasters on 60 days of daily bike trips, evaluated walk-forward, one
step ahead, 46 forecasts each. The simplest baseline wins, and because the
generating process is known the margin can be checked against the best score
any forecaster could possibly achieve.

```
python3 walkforward.py     # the ranking, and whether the margins are real
python3 seasonality.py     # is the weekday pattern real?
python3 floor.py           # the irreducible error, in closed form
python3 -m unittest discover -q tests   # 31 tests
```

## Provenance, before any result

The roadmap asked for a real series. I could not get one. The external source
this repo already uses, Open-Meteo's historical archive, is refused by this
environment's network policy (`connect_rejected`), and the two real-ish series
already committed here are 15 and 21 points long — too short for a
walk-forward evaluation with a weekly lag.

So the series is `bikeshare-data-cleaning/data/trips_clean.csv`, whose own
README states: *"the defects are real patterns, the rides are generated."*
**This is synthetic data and no conclusion here transfers to real bike
traffic.**

It does buy something real data cannot. The generating process is one readable
line, so the irreducible error has a closed form, and "the mean wins" stops
being an observation about 60 days and becomes a fact with a proof.

## The ranking

| model | MAE | RMSE | MASE |
| --- | ---: | ---: | ---: |
| **historical mean** | **17.16** | 18.64 | **0.748** |
| linear trend | 18.10 | 19.61 | 0.789 |
| exp. smoothing (fitted) | 18.83 | 20.51 | 0.821 |
| seasonal naive (lag 7) | 20.07 | 24.87 | 0.875 |
| Holt linear (fitted) | 21.70 | 26.87 | 0.946 |
| naive | 22.93 | 27.67 | 1.000 |
| drift | 23.36 | 28.24 | 1.018 |

The average of everything so far beats every fitted model, and the two models
that extrapolate a trend — drift and Holt — are the only two that fail to beat
doing nothing at all.

The fitted exponential smoothing reaches the same conclusion by itself. Its α
is re-fitted on each step's history, and on the full series it picks **α =
0.1**: α near 1 is the naive forecast, α near 0 is the historical mean, so the
fit is quietly trying to become the mean and getting most of the way there.

## Why: the closed form

The generator is `random.randint(70, 130)` — i.i.d. draws, with no reference
to the previous day, the weekday, or the date. With N = 61 possible values and
mean 100:

```
best possible (constant 100)   E|X-100|      = 930/61   = 15.2459
naive forecast                 E|X₁-X₂|      = 3720/183 = 20.3279
ratio                                                   = exactly 4/3
```

Both confirmed by 400,000 simulated draws to 15.268 and 20.390. Nothing — no
ARIMA, no gradient boosting, no neural network — gets below 15.2459 on this
series, because below that is noise.

The historical mean measured 17.16 against a floor of 15.25. That gap is not
model error; it is the cost of estimating the mean from 60 samples when the
sample mean happens to be 97.18 rather than 100.

Naive measured 22.93 where theory says 20.33. Over 46 forecasts the sampling
distribution of that statistic has sd 2.29 and a 90% interval of
[16.65, 24.15], so 22.93 sits +1.14 sd from the predicted mean — comfortably
inside. Theory and measurement agree; the ranking is not an artifact of these
particular 60 days.

## The weekday pattern that is not there

| Mon | Tue | Wed | Thu | Fri | Sat | Sun |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 104.0 | 89.4 | 99.4 | 103.6 | 99.8 | 81.0 | 102.1 |

A 23-trip spread, with the weekend low exactly where a commuting story would
predict it. It is noise. A permutation test over 20,000 shuffles of the
weekday labels gives **p = 0.086**, and the generator confirms it: the weekday
*shape of trips within a day* is seasonal, the daily *total* is not.

Worth being precise about the strength of that evidence: p = 0.086 does not
clear 0.05, but it is not far off, and on this alone a careful analyst might
still be tempted. What settles it is reading the generator. Without that line
of code, this series would support a plausible, wrong, seasonal story — which
is roughly how such stories get published.

The control matters too: planting a +40 weekend effect and rerunning the same
test gives p < 0.01, so the test can find an effect when there is one.

## What is *not* established

The mean beats naive, drift, linear trend, exponential smoothing and Holt with
95% paired-bootstrap intervals that exclude zero. Against **seasonal naive**
it does not:

| opponent | MAE difference | 95% CI | P(mean better) |
| --- | ---: | ---: | ---: |
| naive | −5.78 | [−10.18, −1.29] | 99.4% |
| drift | −6.20 | [−10.75, −1.57] | 99.6% |
| Holt linear | −4.54 | [−8.82, −0.30] | 98.2% |
| exp. smoothing | −1.67 | [−2.94, −0.48] | 99.7% |
| linear trend | −0.94 | [−1.68, −0.20] | 99.3% |
| **seasonal naive** | **−2.91** | **[−7.51, +1.74]** | **88.9%** |

We *know* the mean must beat seasonal naive — the generator leaves no weekly
signal for the lag-7 model to exploit. Forty-six forecasts cannot show it.
Known truth and demonstrated truth are different things, and 88.9% is not a
result; a test asserts that this interval still spans zero, so nobody later
rounds it up into one.

## Method

Expanding window, one step ahead: at each step the forecaster receives the
history and returns one number, which is then scored and appended. Every model
is a function of its history alone, so there is no argument through which the
future could arrive — and a spy forecaster in the tests records the exact
history lengths it was handed (14 through 29 on a 30-point series, never 30).

Fitted parameters are re-fitted at every step on that step's history. Fitting
α once on the whole series and then "walking forward" is the most common way a
backtest flatters itself.

Comparisons between models are paired. The models forecast the same points, so
their errors are correlated and two independent confidence intervals would
understate the evidence; the bootstrap resamples per-point differences and
keeps the pairing.

Stdlib only.
