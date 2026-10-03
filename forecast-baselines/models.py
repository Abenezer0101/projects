"""Forecasters. Every one sees only the history passed to it.

Each is a function `(history) -> next value`, which makes leakage structurally
hard: there is no argument through which the future could arrive. The fitted
models re-fit their parameters on each call, on that history alone -- fitting
alpha once on the whole series and then "walking forward" is the most common
way a backtest flatters itself.
"""

from __future__ import annotations

SEASON = 7


def naive(history: list[float]) -> float:
    """Tomorrow looks like today."""
    return history[-1]


def seasonal_naive(history: list[float]) -> float:
    """Tomorrow looks like the same weekday last week."""
    return history[-SEASON] if len(history) >= SEASON else history[-1]


def historical_mean(history: list[float]) -> float:
    """Tomorrow looks like the average so far. The forecaster people skip
    straight past, and the one to beat when a series has no structure."""
    return sum(history) / len(history)


def drift(history: list[float]) -> float:
    """Extend the straight line between the first and last observation."""
    if len(history) < 2:
        return history[-1]
    slope = (history[-1] - history[0]) / (len(history) - 1)
    return history[-1] + slope


def linear_trend(history: list[float]) -> float:
    """Least-squares line on the index, extrapolated one step."""
    n = len(history)
    if n < 2:
        return history[-1]
    mean_x = (n - 1) / 2
    mean_y = sum(history) / n
    sxx = sum((i - mean_x) ** 2 for i in range(n))
    if sxx == 0:
        return mean_y
    sxy = sum((i - mean_x) * (y - mean_y) for i, y in enumerate(history))
    slope = sxy / sxx
    return mean_y + slope * (n - mean_x)


def _ses_forecast(history: list[float], alpha: float) -> float:
    level = history[0]
    for value in history[1:]:
        level = alpha * value + (1 - alpha) * level
    return level


def _ses_insample_mae(history: list[float], alpha: float) -> float:
    level = history[0]
    total, n = 0.0, 0
    for value in history[1:]:
        total += abs(value - level)
        n += 1
        level = alpha * value + (1 - alpha) * level
    return total / n if n else float("inf")


ALPHAS = [i / 20 for i in range(1, 20)]


def ses(history: list[float]) -> float:
    """Simple exponential smoothing, alpha re-fitted on this history only.

    alpha near 1 is the naive forecast; alpha near 0 is the historical mean.
    What the fit chooses is therefore a direct read on whether the series has
    any momentum worth following.
    """
    if len(history) < 3:
        return history[-1]
    best = min(ALPHAS, key=lambda a: _ses_insample_mae(history, a))
    return _ses_forecast(history, best)


def fitted_alpha(history: list[float]) -> float:
    """The alpha ses() would pick, exposed so the README can report it."""
    if len(history) < 3:
        return 1.0
    return min(ALPHAS, key=lambda a: _ses_insample_mae(history, a))


def holt(history: list[float]) -> float:
    """Exponential smoothing with a trend term, both parameters re-fitted."""
    if len(history) < 4:
        return history[-1]

    def run(alpha: float, beta: float) -> tuple[float, float]:
        level, trend = history[0], history[1] - history[0]
        total, n = 0.0, 0
        for value in history[1:]:
            prediction = level + trend
            total += abs(value - prediction)
            n += 1
            new_level = alpha * value + (1 - alpha) * (level + trend)
            trend = beta * (new_level - level) + (1 - beta) * trend
            level = new_level
        return total / n, level + trend

    grid = [(a, b) for a in (0.1, 0.3, 0.5, 0.7, 0.9) for b in (0.05, 0.1, 0.3, 0.5)]
    return min((run(a, b) for a, b in grid), key=lambda pair: pair[0])[1]


MODELS = {
    "naive": naive,
    "seasonal naive (lag 7)": seasonal_naive,
    "historical mean": historical_mean,
    "drift": drift,
    "linear trend": linear_trend,
    "exp. smoothing (fitted)": ses,
    "Holt linear (fitted)": holt,
}
