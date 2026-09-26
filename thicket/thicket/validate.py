"""Checking this implementation against scikit-learn.

The same trick as testing a SQL engine by running every query through SQLite
as well: a second implementation that was written by other people, for other
reasons, and that fails differently. Agreement to machine precision is a much
stronger statement than any assertion I could write about my own arithmetic.

Exact agreement is only a fair expectation because both sides do an exact
greedy split search with no subsampling and no histogram binning. Turn on
`subsample` or swap in `HistGradientBoosting` and the right test becomes
"close", not "identical".
"""

from __future__ import annotations

import numpy as np


def compare_tree(X, y, max_depth=3, min_samples_leaf=1):
    from sklearn.tree import DecisionTreeRegressor

    from .tree import RegressionTree
    mine = RegressionTree(max_depth=max_depth, min_samples_leaf=min_samples_leaf).fit(X, y)
    ref = DecisionTreeRegressor(max_depth=max_depth, min_samples_leaf=min_samples_leaf,
                                random_state=0).fit(X, y)
    pm, pr = mine.predict(X), ref.predict(X)
    return {"max_abs_diff": float(np.abs(pm - pr).max()),
            "leaves_mine": mine.n_leaves(), "leaves_sklearn": int(ref.get_n_leaves()),
            "identical": bool(np.allclose(pm, pr, atol=1e-9))}


def compare_regressor(X, y, n_estimators=60, learning_rate=0.1, max_depth=3):
    from sklearn.ensemble import GradientBoostingRegressor

    from .gbm import GradientBoosting
    mine = GradientBoosting("squared_error", n_estimators=n_estimators,
                            learning_rate=learning_rate, max_depth=max_depth).fit(X, y)
    ref = GradientBoostingRegressor(n_estimators=n_estimators, learning_rate=learning_rate,
                                    max_depth=max_depth, subsample=1.0,
                                    random_state=0).fit(X, y)
    pm, pr = mine.predict(X), ref.predict(X)
    return {"max_abs_diff": float(np.abs(pm - pr).max()),
            "identical": bool(np.allclose(pm, pr, atol=1e-8))}


def compare_classifier(X, y, n_estimators=60, learning_rate=0.1, max_depth=3):
    from sklearn.ensemble import GradientBoostingClassifier

    from .gbm import GradientBoosting
    mine = GradientBoosting("log_loss", n_estimators=n_estimators,
                            learning_rate=learning_rate, max_depth=max_depth).fit(X, y)
    ref = GradientBoostingClassifier(n_estimators=n_estimators, learning_rate=learning_rate,
                                     max_depth=max_depth, subsample=1.0,
                                     random_state=0).fit(X, y)
    qm = mine.predict_proba(X)[:, 1]
    qr = ref.predict_proba(X)[:, 1]
    return {"max_abs_prob_diff": float(np.abs(qm - qr).max()),
            "label_agreement": float((mine.predict(X) == ref.predict(X)).mean()),
            "identical": bool(np.allclose(qm, qr, atol=1e-6))}


def real_data_check(n_estimators=100, learning_rate=0.1, max_depth=3, test_frac=0.3):
    """Held-out comparison on a real dataset that ships with scikit-learn."""
    from sklearn.datasets import load_breast_cancer
    from sklearn.ensemble import GradientBoostingClassifier
    from sklearn.metrics import log_loss, roc_auc_score

    from .gbm import GradientBoosting
    data = load_breast_cancer()
    X, y = data.data, data.target
    rng = np.random.default_rng(0)
    idx = rng.permutation(len(y))
    cut = int(len(y) * (1 - test_frac))
    tr, te = idx[:cut], idx[cut:]

    mine = GradientBoosting("log_loss", n_estimators=n_estimators,
                            learning_rate=learning_rate, max_depth=max_depth).fit(X[tr], y[tr])
    ref = GradientBoostingClassifier(n_estimators=n_estimators, learning_rate=learning_rate,
                                     max_depth=max_depth, subsample=1.0,
                                     random_state=0).fit(X[tr], y[tr])
    pm = mine.predict_proba(X[te])[:, 1]
    pr = ref.predict_proba(X[te])[:, 1]
    return {"dataset": "breast_cancer", "n_train": len(tr), "n_test": len(te),
            "n_features": X.shape[1],
            "auc_mine": float(roc_auc_score(y[te], pm)),
            "auc_sklearn": float(roc_auc_score(y[te], pr)),
            "logloss_mine": float(log_loss(y[te], pm)),
            "logloss_sklearn": float(log_loss(y[te], pr)),
            "max_abs_prob_diff": float(np.abs(pm - pr).max())}
