"""How often do random short codes collide?  python3 collision_study.py

The retry loop in store.create_link exists because random codes collide. This
measures that rather than asserting it.

Simulating 62^6 directly is not feasible, so the approach is: verify the
birthday approximation against SHORT alphabets where collisions are easy to
observe, then apply the verified formula to the real code length.
"""

import random
import string

ALPHABET = string.ascii_letters + string.digits      # 62


def draw(length, n, seed):
    """Draw n random codes, return how many were duplicates."""
    rnd = random.Random(seed)
    seen, dupes = set(), 0
    for _ in range(n):
        c = "".join(rnd.choice(ALPHABET) for _ in range(length))
        if c in seen:
            dupes += 1
        else:
            seen.add(c)
    return dupes


def expected(length, n):
    """Birthday approximation: expected duplicates ~ n^2 / 2N."""
    N = len(ALPHABET) ** length
    return n * n / (2 * N)


def main():
    print("Verifying the birthday model against simulation")
    print(f"{'len':>4} {'space':>16} {'drawn':>8} {'observed':>9} {'predicted':>10}")
    trials = 12
    for length, n in ((2, 200), (2, 500), (3, 1000), (3, 3000), (4, 5000), (4, 20000)):
        obs = sum(draw(length, n, s) for s in range(trials)) / trials
        print(f"{length:>4} {len(ALPHABET)**length:>16,} {n:>8,} {obs:>9.1f} {expected(length, n):>10.1f}")

    print("\nApplying the model to the shipped 6-character code")
    N = len(ALPHABET) ** 6
    print(f"key space: {N:,}")
    print(f"{'links stored':>14} {'P(next insert collides)':>24} {'expected dupes so far':>22}")
    for m in (1_000, 100_000, 1_000_000, 10_000_000, 100_000_000, 568_000_000):
        print(f"{m:>14,} {m / N:>23.6%} {expected(6, m):>22,.1f}")

    print("\nA single insert only reaches a 1% collision chance at "
          f"{int(0.01 * N):,} stored links.")
    print("The retry loop is therefore almost never used -- and is still required,")
    print("because the alternative when it does fire is a 500 or a stolen link.")


if __name__ == "__main__":
    main()
