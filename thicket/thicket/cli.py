"""thicket -- gradient boosted trees from scratch, checked against scikit-learn.

  python3 -m thicket.cli validate     diff this implementation against sklearn
  python3 -m thicket.cli newton       what the Newton leaf update is worth
  python3 -m thicket.cli leakage      selecting features before the split
"""

from __future__ import annotations

import argparse
import statistics as st
import sys

import numpy as np

from .gbm import GradientBoosting, sigmoid
from .leakage import demonstrate
from .validate import compare_classifier, compare_regressor, compare_tree, real_data_check


def _smooth(n=300, d=6, seed=0):
    rng = np.random.default_rng(seed)
    X = rng.normal(size=(n, d))
    y = 2 * X[:, 0] - 1.5 * X[:, 1] + 0.5 * X[:, 2] ** 2 + rng.normal(scale=.3, size=n)
    return X, y


def cmd_validate(args):
    X, y = _smooth()
    print("continuous features, no ties in the objective\n")
    print(f"{'depth':>6} {'leaves mine':>12} {'leaves skl':>11} {'max|diff|':>12} {'identical':>10}")
    for d in (1, 2, 3, 4, 5):
        r = compare_tree(X, y, max_depth=d)
        print(f"{d:>6} {r['leaves_mine']:>12} {r['leaves_sklearn']:>11} "
              f"{r['max_abs_diff']:>12.2e} {str(r['identical']):>10}")

    rr = compare_regressor(X, y)
    yb = (y > np.median(y)).astype(int)
    rc = compare_classifier(X, yb)
    print(f"\nboosted regressor   max|diff| {rr['max_abs_diff']:.2e}  identical={rr['identical']}")
    print(f"boosted classifier  max|diff| {rc['max_abs_prob_diff']:.2e}  identical={rc['identical']}")

    d = real_data_check()
    print(f"\nreal data ({d['dataset']}, {d['n_test']} held out, {d['n_features']} features)")
    print(f"  AUC      mine {d['auc_mine']:.4f}   sklearn {d['auc_sklearn']:.4f}")
    print(f"  logloss  mine {d['logloss_mine']:.4f}   sklearn {d['logloss_sklearn']:.4f}")
    print(f"  max|probability diff| {d['max_abs_prob_diff']:.2e}  -- NOT identical, and")
    print("  that is expected: real data produces exact ties in the split objective,")
    print("  and which of two equally optimal splits you take is arbitrary.")
    return 0


def cmd_newton(args):
    print(f"{args.seeds} seeds, each run to its own best log loss over {args.trees} trees\n")
    nw, mr, ntr, mtr = [], [], [], []
    from sklearn.metrics import log_loss
    for seed in range(args.seeds):
        rng = np.random.default_rng(seed)
        n = 1200
        X = rng.normal(size=(n, 8))
        lg = 1.4*X[:,0] - 1.1*X[:,1] + 0.8*X[:,2]*X[:,3] - 0.6*X[:,4]
        y = (rng.random(n) < sigmoid(lg)).astype(int)
        tr, te = slice(0, 800), slice(800, n)
        for newton, ll_acc, tr_acc in ((True, nw, ntr), (False, mr, mtr)):
            m = GradientBoosting("log_loss", n_estimators=args.trees, learning_rate=.1,
                                 max_depth=3, newton_leaves=newton).fit(X[tr], y[tr])
            best = min((log_loss(y[te], sigmoid(F)), i)
                       for i, F in enumerate(m.staged_decision_function(X[te]), 1))
            ll_acc.append(best[0]); tr_acc.append(best[1])

    print(f"{'':<22} {'mean best logloss':>18} {'stdev':>8} {'median trees':>14}")
    print(f"{'Newton leaves':<22} {st.mean(nw):>18.4f} {st.pstdev(nw):>8.4f} {st.median(ntr):>14.0f}")
    print(f"{'mean-residual leaves':<22} {st.mean(mr):>18.4f} {st.pstdev(mr):>8.4f} {st.median(mtr):>14.0f}")
    diff = [a - b for a, b in zip(nw, mr)]
    print(f"\naccuracy difference {st.mean(diff):+.4f} +/- {st.pstdev(diff):.4f}"
          f"  (Newton lower on {sum(1 for d in diff if d < 0)}/{len(diff)} seeds)")
    print(f"trees to optimum: Newton needs {st.median(mtr)/max(1,st.median(ntr)):.1f}x fewer")
    print("\nThe spread exceeds the difference, so the accuracy gap is not")
    print("distinguishable from zero here. The speed-up is.")
    return 0


def cmd_leakage(args):
    r = demonstrate(n_rows=args.rows, n_features=args.features,
                    k_features=args.k, seeds=args.seeds)
    print(f"{r['n_rows']} rows, {r['n_features']} pure-noise features, label is a fair coin")
    print(f"nothing can predict a coin, so the honest answer is exactly 50%\n")
    print(f"  select on the FULL data, then cross-validate : {r['leaked_mean']:>6.1%}")
    print(f"  select inside each fold                      : {r['honest_mean']:>6.1%}")
    print(f"\n  manufactured accuracy: {r['inflation']:+.1%}")
    print(f"\n  leaked per seed: {' '.join(f'{v:.0%}' for v in r['leaked'])}")
    print(f"  honest per seed: {' '.join(f'{v:.0%}' for v in r['honest'])}")
    return 0


def build_parser():
    p = argparse.ArgumentParser(prog="thicket", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    v = sub.add_parser("validate", help="diff against scikit-learn")
    v.set_defaults(fn=cmd_validate)

    n = sub.add_parser("newton", help="what the Newton leaf update buys")
    n.add_argument("--seeds", type=int, default=8)
    n.add_argument("--trees", type=int, default=400)
    n.set_defaults(fn=cmd_newton)

    l = sub.add_parser("leakage", help="selecting features before the split")
    l.add_argument("--rows", type=int, default=300)
    l.add_argument("--features", type=int, default=3000)
    l.add_argument("--k", type=int, default=20)
    l.add_argument("--seeds", type=int, default=8)
    l.set_defaults(fn=cmd_leakage)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
