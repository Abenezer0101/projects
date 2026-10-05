"""The z-score has a ceiling, and it is lower than the threshold you use.

A z-score divides by a standard deviation computed from data that includes the
point being tested. An extreme point inflates its own denominator, which caps
how extreme it can appear. The cap is exact:

    with the sample sd (ddof=1):      max |z| = (n - 1) / sqrt(n)
    with the population sd (ddof=0):  max |z| = sqrt(n - 1)

Both are achieved when one point goes to infinity and the rest are equal, and
both are verified numerically below.

The consequence is blunt. Using the sample sd and a threshold of 3, a window
of ten points can never flag ANY single outlier, however large -- the ceiling
there is 2.846. A daily metric reviewed over the last ten days, or an hourly
metric over the last ten hours, is in exactly that regime.
"""

from __future__ import annotations

import math
import statistics


def ceiling_sample_sd(n: int) -> float:
    return (n - 1) / math.sqrt(n)


def ceiling_population_sd(n: int) -> float:
    return math.sqrt(n - 1)


def achieved_max_z(n: int, extreme: float = 1e12, ddof: int = 1) -> float:
    """Put one point at infinity, leave the rest equal, and measure."""
    data = [0.0] * (n - 1) + [extreme]
    mean = statistics.mean(data)
    sd = statistics.stdev(data) if ddof == 1 else statistics.pstdev(data)
    return (data[-1] - mean) / sd


def min_n_for_threshold(threshold: float, ddof: int = 1) -> int:
    """Smallest window in which a single outlier can reach the threshold."""
    n = 3
    while n < 100_000:
        ceiling = ceiling_sample_sd(n) if ddof == 1 else ceiling_population_sd(n)
        if ceiling > threshold:
            return n
        n += 1
    raise ValueError("no such n")


def z_for_k_outliers(n: int, k: int) -> float:
    """Closed form for k identical outliers among n-k identical normal points.

    With k points at value s and n-k at 0, the mean is ks/n and the sample sd
    works out to s*sqrt(k(n-k)/(n(n-1))), so the size s cancels entirely:

        z = sqrt((n - k)(n - 1) / (k * n))

    At k=1 this reduces to (n-1)/sqrt(n), the single-outlier ceiling. That the
    magnitude cancels is the striking part: making the anomalies bigger does
    not help at all.
    """
    return math.sqrt((n - k) * (n - 1) / (k * n))


def masking_window(threshold: float = 3.0) -> list[int]:
    """Window sizes where ONE outlier is flagged but TWO are not."""
    return [n for n in range(3, 400)
            if z_for_k_outliers(n, 1) >= threshold > z_for_k_outliers(n, 2)]


def two_outlier_masking(n: int = 16, size: float = 40.0) -> dict:
    """Two outliers hide each other -- masking proper, measured.

    My first attempt used n=200, where one outlier scores z=14.07 and two
    score 9.92: both still far above 3, so nothing was masked and the demo
    proved nothing. The closed form says why, and says exactly which window
    sizes do mask.
    """
    one = [0.0] * (n - 1) + [size]
    two = [0.0] * (n - 2) + [size, size]
    z_one = abs(one[-1] - statistics.mean(one)) / statistics.stdev(one)
    z_two = abs(two[-1] - statistics.mean(two)) / statistics.stdev(two)
    return {"n": n, "size": size, "z_with_one": z_one, "z_with_two": z_two,
            "predicted_one": z_for_k_outliers(n, 1),
            "predicted_two": z_for_k_outliers(n, 2)}


def main() -> None:
    print("the z-score's hard ceiling, by window size\n")
    print(f"  {'n':>6} {'(n-1)/sqrt(n)':>15} {'measured':>10} "
          f"{'sqrt(n-1)':>11} {'measured':>10}")
    for n in (5, 10, 11, 20, 30, 50, 100):
        print(f"  {n:>6} {ceiling_sample_sd(n):>15.4f} "
              f"{achieved_max_z(n, ddof=1):>10.4f} "
              f"{ceiling_population_sd(n):>11.4f} "
              f"{achieved_max_z(n, ddof=0):>10.4f}")

    print("\nsmallest window in which one outlier can reach the threshold")
    print(f"  {'threshold':>10} {'sample sd':>11} {'population sd':>15}")
    for t in (2.0, 2.5, 3.0, 3.5, 4.0, 5.0):
        print(f"  {t:>10.1f} {min_n_for_threshold(t, 1):>11} "
              f"{min_n_for_threshold(t, 0):>15}")
    print("\n  So at the usual threshold of 3 with the sample sd, a 10-point")
    print("  window cannot flag anything at all: its ceiling is "
          f"{ceiling_sample_sd(10):.3f}.")

    window = masking_window(3.0)
    print(f"\nwindow sizes where one outlier is caught but two are not, at z>3:")
    print(f"  n = {window[0]} to {window[-1]}")

    m = two_outlier_masking()
    print(f"\nmasking, measured at n = {m['n']} (both outliers at {m['size']:.0f})")
    print(f"  one outlier  -> z = {m['z_with_one']:.3f}  "
          f"(closed form {m['predicted_one']:.3f})  FLAGGED at 3.0")
    print(f"  two outliers -> z = {m['z_with_two']:.3f}  "
          f"(closed form {m['predicted_two']:.3f})  NOT flagged")
    print("  Adding a second anomaly hides the one that was already visible.")
    print("  And since the outlier size cancels out of the formula, making")
    print("  them larger does not help: at n=16 two outliers cannot exceed")
    print(f"  {z_for_k_outliers(16, 2):.3f} no matter how extreme they are.")


if __name__ == "__main__":
    main()
