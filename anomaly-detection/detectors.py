"""Four detectors over the same interface: `flag(values) -> set of indices`.

The z-score is here to fail. The other three are here to show what it costs.
"""

from __future__ import annotations

import math
import statistics

PERIOD = 24

# For a normal distribution, MAD * 1.4826 estimates the standard deviation:
# 1 / 0.6744897501960817, the 75th percentile of the standard normal. Without
# it a MAD-based threshold is not comparable to a z threshold.
MAD_TO_SIGMA = 1.4826


def mad(values: list[float]) -> float:
    if not values:
        return 0.0
    centre = statistics.median(values)
    return statistics.median([abs(v - centre) for v in values])


class ZScore:
    """(x - mean) / sd. Both statistics are computed from data that INCLUDES
    the outlier, which is the whole problem -- see masking.py."""

    name = "z-score"

    def __init__(self, threshold: float = 3.0):
        self.threshold = threshold

    def flag(self, values: list[float]) -> set[int]:
        if len(values) < 2:
            return set()
        mean = statistics.mean(values)
        sd = statistics.stdev(values)
        if sd == 0:
            return set()
        return {i for i, v in enumerate(values)
                if abs(v - mean) / sd >= self.threshold}


class ModifiedZScore:
    """Median and MAD instead of mean and sd.

    The median has a 50% breakdown point: half the sample can be arbitrarily
    corrupted before it moves. The mean has a breakdown point of 0 -- one
    point is enough.
    """

    name = "modified z (MAD)"

    def __init__(self, threshold: float = 3.0):
        self.threshold = threshold

    def flag(self, values: list[float]) -> set[int]:
        if len(values) < 2:
            return set()
        centre = statistics.median(values)
        scale = mad(values) * MAD_TO_SIGMA
        if scale == 0:
            # A MAD of zero means over half the values are identical. Falling
            # back to the sd here would reintroduce exactly the fragility this
            # detector exists to avoid, so flag only exact departures.
            return {i for i, v in enumerate(values) if v != centre}
        return {i for i, v in enumerate(values)
                if abs(v - centre) / scale >= self.threshold}


class IQR:
    """Tukey's fences: below Q1 - k*IQR or above Q3 + k*IQR."""

    name = "IQR fence"

    def __init__(self, k: float = 1.5):
        self.k = k

    def flag(self, values: list[float]) -> set[int]:
        ordered = sorted(values)
        n = len(ordered)
        if n < 4:
            return set()
        q1 = ordered[n // 4]
        q3 = ordered[(3 * n) // 4]
        spread = q3 - q1
        lo, hi = q1 - self.k * spread, q3 + self.k * spread
        return {i for i, v in enumerate(values) if v < lo or v > hi}


class SeasonalMAD:
    """Subtract the per-phase median, then apply a MAD threshold to residuals.

    The decomposition is deliberately crude -- a median per position in the
    cycle, not STL -- because the point is that ANY accounting for the cycle
    beats none. Each phase is centred on its own median, so the 08:00 rush is
    compared against other 08:00s rather than against 03:00.
    """

    name = "seasonal + MAD"

    def __init__(self, threshold: float = 3.0, period: int = PERIOD):
        self.threshold = threshold
        self.period = period

    def flag(self, values: list[float]) -> set[int]:
        if len(values) < 2:
            return set()
        by_phase: dict[int, list[float]] = {}
        for i, v in enumerate(values):
            by_phase.setdefault(i % self.period, []).append(v)
        centres = {phase: statistics.median(vs) for phase, vs in by_phase.items()}

        residuals = [v - centres[i % self.period] for i, v in enumerate(values)]
        scale = mad(residuals) * MAD_TO_SIGMA
        if scale == 0:
            return {i for i, r in enumerate(residuals) if r != 0}
        return {i for i, r in enumerate(residuals)
                if abs(r - statistics.median(residuals)) / scale >= self.threshold}


DETECTORS = [ZScore, ModifiedZScore, IQR, SeasonalMAD]


class SeasonalPerPhase:
    """Per-phase centre AND per-phase scale.

    De-seasonalising only the level is not enough when the variance is
    seasonal too. These are counts, so they are roughly Poisson: variance
    tracks the mean, and the 08:00 rush is genuinely more variable than 03:00.
    Pooling one residual scale across all 24 phases therefore under-estimates
    the spread at the peaks, and `SeasonalMAD` goes on flagging rush hours --
    it flagged 123 of 1438 points, more than the raw z-score did.

    Giving each phase its own MAD fixes it. The lesson is that a seasonal
    adjustment has to cover both moments, not just the first.
    """

    name = "seasonal, per-phase scale"

    def __init__(self, threshold: float = 3.0, period: int = PERIOD):
        self.threshold = threshold
        self.period = period

    def flag(self, values: list[float]) -> set[int]:
        if len(values) < 2:
            return set()
        by_phase: dict[int, list[float]] = {}
        for i, v in enumerate(values):
            by_phase.setdefault(i % self.period, []).append(v)
        centre = {p: statistics.median(vs) for p, vs in by_phase.items()}
        scale = {p: mad(vs) * MAD_TO_SIGMA for p, vs in by_phase.items()}

        flagged = set()
        for i, v in enumerate(values):
            phase = i % self.period
            s = scale[phase]
            if s == 0:
                # a phase with no spread at all: only an exact departure counts
                if v != centre[phase]:
                    flagged.add(i)
            elif abs(v - centre[phase]) / s >= self.threshold:
                flagged.add(i)
        return flagged


DETECTORS = [ZScore, ModifiedZScore, IQR, SeasonalMAD, SeasonalPerPhase]


class SeasonalPoisson:
    """Per-phase expectation with a Poisson scale: (x - mu) / sqrt(mu).

    Neither pooled nor per-phase MAD resolves the tension. A pooled scale
    (1.483) flags a dropout at 08:00 easily but calls every busy hour an
    anomaly; a per-phase scale (4.45 at 08:00) silences the false alarms and
    then cannot see the dropout, which sits only 2.36 scales away.

    The way out is to stop estimating the scale and model it. These are event
    counts, so to first order the variance equals the mean, and the natural
    standardisation is the Pearson residual. mu is the per-phase MEAN here,
    not the median -- it is a Poisson rate, and a median of 0 at 03:00 would
    make the denominator vanish.
    """

    name = "seasonal, Poisson scale"

    def __init__(self, threshold: float = 3.0, period: int = PERIOD):
        self.threshold = threshold
        self.period = period

    def flag(self, values: list[float]) -> set[int]:
        if len(values) < 2:
            return set()
        by_phase: dict[int, list[float]] = {}
        for i, v in enumerate(values):
            by_phase.setdefault(i % self.period, []).append(v)
        # a floor of 1 event keeps sqrt(mu) meaningful for the dead hours
        rate = {p: max(1.0, statistics.mean(vs)) for p, vs in by_phase.items()}
        return {i for i, v in enumerate(values)
                if abs(v - rate[i % self.period]) / math.sqrt(rate[i % self.period])
                >= self.threshold}


DETECTORS = [ZScore, ModifiedZScore, IQR, SeasonalMAD, SeasonalPerPhase,
             SeasonalPoisson]
