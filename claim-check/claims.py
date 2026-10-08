"""The claim registry: every number this repository asserts, and how to re-derive it.

A claim is three things:

  the project it belongs to
  the exact string as it appears in that project's README
  a snippet that recomputes it from the code

Both halves are checked. The string must still be present in the README, and
the snippet must still print it. That catches the two ways a claim rots: the
code changes and the prose does not, or the prose is edited and the code never
agreed.

Each snippet runs in a SUBPROCESS with its own project directory as the
working directory. These projects import each other's modules by bare name --
`series`, `models`, `evaluate`, `detectors`, `lp` all exist in more than one
of them -- so importing them into one interpreter would collide. Subprocesses
are not a workaround here; they are the only correct way to run forty
independent packages that were never designed to coexist on one sys.path.

WHAT IS DELIBERATELY NOT HERE: wall-clock timings and speedups. A README that
says "375x faster" is reporting a measurement of one machine on one day, and
pinning it would produce a check that fails for reasons having nothing to do
with the code. Those claims are listed in SKIPPED with the reason, so their
absence is a decision on the record rather than an oversight.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Claim:
    project: str
    claimed: str          # the literal substring that must appear in the README
    snippet: str          # python that prints the value
    note: str = ""


CLAIMS: list[Claim] = [
    # ---- rate-limiter -------------------------------------------------------
    Claim("rate-limiter", "2.00×",
          "from audit import replay, worst_window\n"
          "from limiter import FixedWindow\n"
          "from tests.test_limiter import boundary_attack\n"
          "lim = FixedWindow(100, 60.0, window_start=540.0)\n"
          "n, _ = worst_window(replay(lim, boundary_attack()), 60.0)\n"
          "print(f'{n/100:.2f}×')",
          "fixed window admits exactly double the stated limit"),
    Claim("rate-limiter", "1.00×",
          "from audit import replay, worst_window\n"
          "from limiter import SlidingLog\n"
          "from tests.test_limiter import boundary_attack\n"
          "n, _ = worst_window(replay(SlidingLog(100, 60.0), boundary_attack()), 60.0)\n"
          "print(f'{n/100:.2f}×')",
          "sliding log is exact"),

    # ---- docstring-search ---------------------------------------------------
    Claim("docstring-search", "2,077 documents",
          "from search import load\n"
          "print(f'{len(load()):,} documents')"),
    Claim("docstring-search", "0.625",
          "from search import load, Bm25Index\n"
          "from evaluate import score\n"
          "from judgments import JUDGEMENTS\n"
          "print(f\"{score(Bm25Index(load()), JUDGEMENTS)['mrr']:.3f}\")",
          "tuned MRR"),
    Claim("docstring-search", "0.480",
          "from search import load, LikeBaseline\n"
          "from evaluate import score\n"
          "from judgments import JUDGEMENTS\n"
          "print(f\"{score(LikeBaseline(load()), JUDGEMENTS)['mrr']:.3f}\")",
          "LIKE baseline MRR"),

    # ---- regex-nfa ----------------------------------------------------------
    Claim("regex-nfa", "76,744",
          "from difftest import run\n"
          "checked, skipped, failures = run()\n"
          "print(f'{checked:,}')"),
    Claim("regex-nfa", "814",
          "from difftest import run\n"
          "checked, skipped, failures = run()\n"
          "print(skipped)",
          "patterns skipped as invalid or lazy/possessive"),

    # ---- csv-parser ---------------------------------------------------------
    Claim("csv-parser", "78.3%",
          "from failures import random_csv\n"
          "from difftest import reference\n"
          "from parser import naive\n"
          "import random\n"
          "rng = random.Random(1)\n"
          "bad = sum(1 for _ in range(20000)\n"
          "          if (lambda t: naive(t) != reference(t))(random_csv(rng)))\n"
          "print(f'{bad/20000:.1%}')",
          "naive split failure rate on adversarial input"),

    # ---- ab-test ------------------------------------------------------------
    Claim("ab-test", "22.0%",
          "from peeking import false_positive_rate, DAYS\n"
          "rate, _ = false_positive_rate(list(range(1, DAYS + 1)))\n"
          "print(f'{rate:.1%}')",
          "false positives from daily peeking"),
    Claim("ab-test", "18.2%",
          "from peeking import false_positive_rate, DAYS\n"
          "_, hits = false_positive_rate(list(range(1, DAYS + 1)))\n"
          "print(f'{sum(abs(h.observed_lift) for h in hits)/len(hits):.1%}')",
          "mean absolute lift among false positives"),
    Claim("ab-test", "2.594",
          "from sequential import calibrate\n"
          "from peeking import DAYS\n"
          "print(f'{calibrate(list(range(1, DAYS + 1))):.3f}')",
          "calibrated sequential boundary"),

    # ---- forecast-baselines -------------------------------------------------
    Claim("forecast-baselines", "17.16",
          "from series import daily_counts\n"
          "from walkforward import table\n"
          "print(f'{table(daily_counts()[1])[0][1]:.2f}')",
          "winning MAE"),
    Claim("forecast-baselines", "0.748",
          "from series import daily_counts\n"
          "from walkforward import table\n"
          "print(f'{table(daily_counts()[1])[0][3]:.3f}')",
          "winning MASE"),
    Claim("forecast-baselines", "15.2459",
          "import floor\n"
          "print(f'{floor.CONSTANT_MAE:.4f}')",
          "closed-form irreducible error"),

    # ---- nearest-neighbour --------------------------------------------------
    Claim("nearest-neighbour", "5570.2 km",
          "from geo import haversine_km\n"
          "print(f'{haversine_km(40.7128, -74.0060, 51.5074, -0.1278):.1f} km')",
          "New York to London"),
    Claim("nearest-neighbour", "1947.4 km",
          "from geo import haversine_km\n"
          "print(f'{haversine_km(33.7490, -84.3880, 39.7392, -104.9903):.1f} km')",
          "Atlanta to Denver"),
    Claim("nearest-neighbour", "474 km",
          "from geo import haversine_km\n"
          "from tests.test_nn import TestTheLatLonMistake as T\n"
          "best = min(T.PACIFIC, key=lambda p: haversine_km(-14.0, 179.5, p[1], p[2]))\n"
          "print(f'{haversine_km(-14.0, 179.5, best[1], best[2]):.0f} km')",
          "true nearest distance in the antimeridian case"),

    # ---- recommender-eval ---------------------------------------------------
    Claim("recommender-eval", "4.47",
          "from collections import defaultdict\n"
          "from simulate import generate\n"
          "from evaluate import random_split\n"
          "_, test = random_split(generate(drift=1.0))\n"
          "by = defaultdict(set)\n"
          "[by[i.user].add(i.item) for i in test]\n"
          "print(f'{sum(len(v) for v in by.values())/len(by):.2f}')",
          "relevant items per user under a random split"),
    Claim("recommender-eval", "16.67",
          "from collections import defaultdict\n"
          "from simulate import generate\n"
          "from evaluate import temporal_split\n"
          "_, test = temporal_split(generate(drift=1.0))\n"
          "by = defaultdict(set)\n"
          "[by[i.user].add(i.item) for i in test]\n"
          "print(f'{sum(len(v) for v in by.values())/len(by):.2f}')",
          "relevant items per user under a temporal split"),

    # ---- anomaly-detection --------------------------------------------------
    Claim("anomaly-detection", "2.846",
          "import masking\n"
          "print(f'{masking.ceiling_sample_sd(10):.3f}')",
          "z-score ceiling in a ten-point window"),
    Claim("anomaly-detection", "3.750",
          "import masking\n"
          "print(f\"{masking.two_outlier_masking(n=16)['z_with_one']:.3f}\")",
          "one outlier at n=16"),
    Claim("anomaly-detection", "2.562",
          "import masking\n"
          "print(f\"{masking.two_outlier_masking(n=16)['z_with_two']:.3f}\")",
          "two outliers mask each other"),
    Claim("anomaly-detection", "9.57",
          "from detectability import per_hour_rates\n"
          "print(f'{per_hour_rates()[8]:.2f}')",
          "the one hour whose rate can show a full outage"),

    # ---- record-linkage -----------------------------------------------------
    Claim("record-linkage", "0.944",
          "from similarity import jaro\n"
          "print(f\"{jaro('MARTHA','MARHTA'):.3f}\")",
          "published Jaro reference value"),
    Claim("record-linkage", "23.7%",
          "from records import records, true_pairs\n"
          "from blocking import assess, first_letter_raw\n"
          "r = records()\n"
          "print(f\"{assess(r, true_pairs(r), first_letter_raw)['completeness']:.1%}\")",
          "pair completeness of the raw first-letter block"),
    Claim("record-linkage", "0.883",
          "from harder import build, true_pairs\n"
          "from blocking import no_blocking\n"
          "from evaluate import sweep\n"
          "items, tm = build()\n"
          "print(f'{max(s[\"f1\"] for _, s in sweep(items, true_pairs(items, tm), no_blocking)):.3f}')",
          "best unblocked F1 on the harder set"),

    # ---- integer-programming ------------------------------------------------
    Claim("integer-programming", "627.50",
          "from ip import branch_and_bound\n"
          "from problems import instance_sizing\n"
          "c, cons, up, _ = instance_sizing()\n"
          "print(f'{float(branch_and_bound(c, cons, up).lp_bound):.2f}')",
          "LP relaxation"),
    Claim("integer-programming", "635.00",
          "from ip import branch_and_bound\n"
          "from problems import instance_sizing\n"
          "c, cons, up, _ = instance_sizing()\n"
          "print(f'{float(branch_and_bound(c, cons, up).cost):.2f}')",
          "integer optimum"),
    Claim("integer-programming", "740.00",
          "from ip import round_up_relaxation\n"
          "from problems import instance_sizing\n"
          "c, cons, up, _ = instance_sizing()\n"
          "print(f'{float(round_up_relaxation(c, cons, up).cost):.2f}')",
          "cost of rounding the relaxation up"),
    Claim("integer-programming", "16.54%",
          "from ip import branch_and_bound, round_up_relaxation\n"
          "from problems import instance_sizing\n"
          "c, cons, up, _ = instance_sizing()\n"
          "exact = branch_and_bound(c, cons, up).cost\n"
          "rounded = round_up_relaxation(c, cons, up).cost\n"
          "print(f'{float((rounded - exact)/exact):.2%}')",
          "overpayment from rounding"),

    # ---- assay --------------------------------------------------------------
    Claim("assay", "58 tests",
          "import subprocess, sys\n"
          "out = subprocess.run([sys.executable,'-m','unittest','discover','tests'],\n"
          "                     capture_output=True, text=True).stderr\n"
          "line = next(l for l in out.splitlines() if l.startswith('Ran '))\n"
          "print(line.split()[1] + ' tests')",
          "the suite still has the number the README advertises"),
]

# Claims that are real but not checkable here, with the reason. Listed so the
# gaps in coverage are a stated decision rather than a silence.
SKIPPED: list[tuple[str, str, str]] = [
    ("regex-nfa", "12,072× faster than re",
     "wall-clock ratio: a property of this machine, not of the code"),
    ("nearest-neighbour", "375.4× speedup, crossover at n=50",
     "wall-clock timings; the operation counts would be checkable, the times are not"),
    ("sqlite-concurrency-lab", "2.9× WAL throughput, 95% writes lost",
     "races against real disk and scheduler; the loss figure varies by run"),
    ("query-planner-lab", "+39% regression, 26.34ms vs 16.76ms",
     "wall-clock query times"),
    ("thicket", "5.1× fewer trees",
     "requires scikit-learn, not installed in this checkout"),
    ("bikeshare-data-cleaning", "14× station spread, 231 rides recovered",
     "pandas pipeline, not importable without pandas"),
]
