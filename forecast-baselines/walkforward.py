"""Expanding-window, one-step-ahead evaluation.

The only honest way to score a forecaster on a time series: at each step it
sees the past, predicts one point, and that point is then revealed and added
to the history. A random train/test split would let a model learn from
Wednesday to predict Tuesday, which is why the usual cross-validation is
wrong here and why this file exists instead of a call to one.
"""

from __future__ import annotations

import math

from models import MODELS, naive

MIN_TRAIN = 14  # two full weeks, so lag-7 has something to stand on


def evaluate(values: list[float], forecaster, min_train: int = MIN_TRAIN) -> dict:
    errors = []
    for t in range(min_train, len(values)):
        prediction = forecaster(values[:t])
        errors.append(values[t] - prediction)
    mae = sum(abs(e) for e in errors) / len(errors)
    rmse = math.sqrt(sum(e * e for e in errors) / len(errors))
    return {"mae": mae, "rmse": rmse, "n": len(errors), "errors": errors}


def table(values: list[float], min_train: int = MIN_TRAIN) -> list[tuple]:
    """Every model, ranked by MAE, with MASE against naive on the same points."""
    naive_mae = evaluate(values, naive, min_train)["mae"]
    rows = []
    for name, fn in MODELS.items():
        r = evaluate(values, fn, min_train)
        rows.append((name, r["mae"], r["rmse"], r["mae"] / naive_mae))
    return sorted(rows, key=lambda row: row[1])


def paired_bootstrap(values: list[float], a, b, *, trials: int = 20_000,
                     seed: int = 0, min_train: int = MIN_TRAIN) -> dict:
    """Is model `a` really better than model `b`, or is the gap noise?

    The two models forecast the SAME points, so their errors are correlated
    and comparing two independent confidence intervals understates the
    evidence. Resampling the per-point differences keeps the pairing.
    """
    import random

    ea = evaluate(values, a, min_train)["errors"]
    eb = evaluate(values, b, min_train)["errors"]
    diffs = [abs(x) - abs(y) for x, y in zip(ea, eb)]  # negative: a is better
    observed = sum(diffs) / len(diffs)

    rng = random.Random(seed)
    n = len(diffs)
    better = 0
    means = []
    for _ in range(trials):
        sample = [diffs[rng.randrange(n)] for _ in range(n)]
        m = sum(sample) / n
        means.append(m)
        if m < 0:
            better += 1
    means.sort()
    return {
        "mean_diff": observed,
        "p_a_better": better / trials,
        "ci_low": means[int(0.025 * trials)],
        "ci_high": means[int(0.975 * trials)],
    }


def main() -> None:
    from models import historical_mean
    from series import check_contiguous, daily_counts

    dates, values = daily_counts()
    check_contiguous(dates)
    n_eval = len(values) - MIN_TRAIN
    print(f"{len(values)} days ({dates[0]} to {dates[-1]}), "
          f"{n_eval} one-step-ahead forecasts, expanding window\n")
    print(f"{'model':26} {'MAE':>7} {'RMSE':>7} {'MASE':>6}")
    print("-" * 50)
    for name, mae, rmse, mase in table(values):
        print(f"{name:26} {mae:>7.2f} {rmse:>7.2f} {mase:>6.3f}")

    print("\nis the winner's margin real? paired bootstrap, 20,000 resamples")
    print(f"  {'opponent':26} {'MAE diff':>9} {'95% CI':>18} {'P(better)':>10}")
    for name, fn in MODELS.items():
        if fn is historical_mean:
            continue
        r = paired_bootstrap(values, historical_mean, fn)
        ci = f"[{r['ci_low']:+.2f}, {r['ci_high']:+.2f}]"
        flag = "" if r["ci_high"] < 0 else "   <- spans zero"
        print(f"  {name:26} {r['mean_diff']:>+9.2f} {ci:>18} "
              f"{r['p_a_better']:>9.1%}{flag}")


if __name__ == "__main__":
    main()
