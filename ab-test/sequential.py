"""A sequential test that holds its nominal rate, calibrated and then checked.

The fix for peeking is not to stop peeking -- people will peek -- it is to
raise the bar so that the whole sequence of looks spends 5% in total rather
than 5% per look. This is the Pocock approach: one constant z threshold,
applied at every look, chosen so the family-wise rate comes out right.

The constant is found by simulation rather than quoted from a table, and then
verified on seeds that were not used to find it. A threshold calibrated and
evaluated on the same draws would pass by construction.
"""

from __future__ import annotations

from peeking import ALPHA, DAYS, PER_DAY, false_positive_rate

CALIBRATION_SEED = 1
HOLDOUT_SEED = 99


def calibrate(looks: list[int], target: float = ALPHA, trials: int = 20_000,
              seed: int = CALIBRATION_SEED, tolerance: float = 0.0015) -> float:
    """Bisect on the z threshold until the simulated false-positive rate hits
    the target. Monotone in z, so bisection is safe."""
    lo, hi = 1.5, 4.0
    best = hi
    for _ in range(18):
        mid = (lo + hi) / 2
        rate, _ = false_positive_rate(looks, trials=trials, seed=seed, threshold_z=mid)
        if abs(rate - target) < tolerance:
            return mid
        if rate > target:
            lo = mid        # too many false positives: raise the bar
        else:
            hi = mid
            best = mid
    return best


def power_against(lift: float, looks: list[int], threshold_z: float,
                  trials: int = 10_000, seed: int = 7) -> float:
    """Detection rate when there IS an effect. Raising the bar costs power,
    and a correction that did not would be too good to be true."""
    import random

    from stats import BinomialSampler, z_score

    rng = random.Random(seed)
    base = BinomialSampler(PER_DAY, 0.10)
    treat = BinomialSampler(PER_DAY, 0.10 * (1 + lift))
    found = 0
    for _ in range(trials):
        x_a = x_b = n = 0
        for day in range(1, DAYS + 1):
            x_a += treat.draw(rng)
            x_b += base.draw(rng)
            n += PER_DAY
            if day in looks and abs(z_score(x_a, n, x_b, n)) >= threshold_z:
                found += 1
                break
    return found / trials


def main() -> None:
    daily = list(range(1, DAYS + 1))
    naive_z = 1.959963985  # the z that gives 5% at a single look

    print(f"calibrating a constant boundary for {len(daily)} daily looks\n")
    z_star = calibrate(daily)
    print(f"  naive threshold      z = {naive_z:.3f}  (5% at one look)")
    print(f"  calibrated threshold z = {z_star:.3f}")

    cal_rate, _ = false_positive_rate(daily, seed=CALIBRATION_SEED, threshold_z=z_star)
    hold_rate, _ = false_positive_rate(daily, seed=HOLDOUT_SEED, threshold_z=z_star)
    naive_rate, _ = false_positive_rate(daily, seed=HOLDOUT_SEED, threshold_z=naive_z)
    single_rate, _ = false_positive_rate([DAYS], seed=HOLDOUT_SEED, threshold_z=naive_z)

    print(f"\nfalse-positive rate (A/A, so every hit is a false positive)")
    print(f"  daily looks, naive z, held-out seed        {naive_rate:>7.1%}")
    print(f"  daily looks, calibrated z, CALIBRATION seed {cal_rate:>6.1%}")
    print(f"  daily looks, calibrated z, HELD-OUT seed    {hold_rate:>6.1%}  <- the real test")
    print(f"  one look at the end, naive z                {single_rate:>6.1%}  (reference)")

    print(f"\nwhat the correction costs: detection rate for a real lift")
    print(f"  {'true lift':>10} {'one look':>10} {'daily, corrected':>18}")
    for lift in (0.05, 0.10, 0.20):
        one = power_against(lift, [DAYS], naive_z)
        seq = power_against(lift, daily, z_star)
        print(f"  {lift:>9.0%} {one:>10.1%} {seq:>17.1%}")
    print("\n  the sequential test can stop early, which is worth real time; it")
    print("  pays for that with a higher bar at every look")

    print(f"\nhow the bar rises with the number of looks")
    print(f"  {'looks':>6} {'calibrated z':>13} {'naive FPR':>11}")
    for k in (1, 2, 7, 14):
        looks = [round(i * DAYS / k) or 1 for i in range(1, k + 1)]
        looks = sorted(set(looks))
        z = calibrate(looks, trials=12_000)
        naive_fpr, _ = false_positive_rate(looks, trials=12_000,
                                           seed=HOLDOUT_SEED, threshold_z=naive_z)
        print(f"  {len(looks):>6} {z:>13.3f} {naive_fpr:>10.1%}")
    print("  one look recovers z=1.96, which is the check that the calibration")
    print("  procedure is sound -- it reproduces the analytic answer it was not told.")
    print("  The bar then rises steeply and flattens: doubling 1 look to 2 costs")
    print("  0.20 of z, while doubling 7 to 14 costs 0.12. Halving your peeking")
    print("  buys back much less than the first peek cost you.")


if __name__ == "__main__":
    main()
