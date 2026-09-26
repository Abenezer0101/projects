"""What preprocessing before the split does to a cross-validation score.

The setup is deliberately one where the correct answer is known exactly:
features are pure noise and the label is a fair coin, so NOTHING can predict
it and honest accuracy is 50%. Any score above that is manufactured.

The mistake is ordinary. Pick the most promising features by looking at how
they correlate with the target, then cross-validate the model on those
features. The selection has seen every row, including the ones each fold is
about to be tested on, so the folds are no longer held out -- they helped
choose the inputs.

It does not throw, it does not warn, and the resulting number is the kind that
gets put in a slide.
"""

from __future__ import annotations

import numpy as np

from .gbm import GradientBoosting


def noise_dataset(n_rows=300, n_features=3000, seed=0):
    """Pure noise, fair coin. Any honest model scores 50%."""
    rng = np.random.default_rng(seed)
    X = rng.normal(size=(n_rows, n_features))
    y = rng.integers(0, 2, size=n_rows)
    return X, y


def select_by_correlation(X, y, k):
    """Indices of the k features most correlated with the target."""
    yc = y - y.mean()
    Xc = X - X.mean(axis=0)
    denom = np.sqrt((Xc ** 2).sum(axis=0) * (yc ** 2).sum())
    denom[denom == 0] = 1e-12
    corr = np.abs((Xc * yc[:, None]).sum(axis=0) / denom)
    return np.argsort(-corr)[:k]


def _folds(n, k, seed=0):
    idx = np.arange(n)
    np.random.default_rng(seed).shuffle(idx)
    return np.array_split(idx, k)


def cv_score(X, y, k_features, folds=5, select_inside=True, seed=0, **model_kw):
    """Cross-validated accuracy.

    select_inside=True  -- features chosen inside each fold, using training
                           rows only. Honest.
    select_inside=False -- features chosen once on the whole dataset, then
                           cross-validated. The leak.
    """
    n = len(y)
    parts = _folds(n, folds, seed)
    model_kw = {"n_estimators": 40, "learning_rate": 0.1, "max_depth": 2, **model_kw}

    chosen_once = None if select_inside else select_by_correlation(X, y, k_features)

    scores = []
    for i in range(folds):
        test_idx = parts[i]
        train_idx = np.concatenate([parts[j] for j in range(folds) if j != i])
        cols = (select_by_correlation(X[train_idx], y[train_idx], k_features)
                if select_inside else chosen_once)
        m = GradientBoosting("log_loss", **model_kw).fit(X[train_idx][:, cols],
                                                         y[train_idx])
        pred = m.predict(X[test_idx][:, cols])
        scores.append(float((pred == y[test_idx]).mean()))
    return float(np.mean(scores)), scores


def demonstrate(n_rows=300, n_features=3000, k_features=20, seeds=10, folds=5):
    leaked, honest = [], []
    for s in range(seeds):
        X, y = noise_dataset(n_rows, n_features, seed=s)
        leaked.append(cv_score(X, y, k_features, folds, select_inside=False, seed=s)[0])
        honest.append(cv_score(X, y, k_features, folds, select_inside=True, seed=s)[0])
    return {"truth": 0.5,
            "leaked_mean": float(np.mean(leaked)), "leaked": leaked,
            "honest_mean": float(np.mean(honest)), "honest": honest,
            "inflation": float(np.mean(leaked) - 0.5),
            "n_rows": n_rows, "n_features": n_features, "k_features": k_features,
            "seeds": seeds, "folds": folds}
