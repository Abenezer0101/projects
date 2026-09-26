"""Gradient boosting: fit trees to the gradient of the loss, one at a time.

Two losses, and they differ in a way that is easy to get subtly wrong.

Squared error is the simple case. The negative gradient IS the residual, and a
tree that predicts the mean residual in each leaf already takes the optimal
step, so no leaf correction is needed.

Log loss is not. The negative gradient is (y - p), and fitting a tree to that
gives the right SPLITS but the wrong leaf VALUES -- the mean residual is not
the step that minimises logistic loss. The leaves have to be replaced with a
Newton step, sum(g) / sum(h) where h = p(1-p). Skipping that still trains and
still improves, which is exactly why it survives in a lot of hand-rolled
implementations: it looks like it works, it is just slower and worse than it
should be, and nothing says so.

`newton_leaves=False` keeps the wrong version available so the cost can be
measured rather than asserted.
"""

from __future__ import annotations

import numpy as np

from .tree import RegressionTree

EPS = 1e-12


def sigmoid(z):
    return 1.0 / (1.0 + np.exp(-np.clip(z, -500, 500)))


def _leaf_ids(tree, X):
    """Which leaf each row lands in, as the id of the node object."""
    out = np.empty(len(X), dtype=np.int64)
    for i, row in enumerate(X):
        node = tree.root
        while not node.is_leaf:
            node = node.left if row[node.feature] <= node.threshold else node.right
        out[i] = id(node)
    return out


class GradientBoosting:
    """loss='squared_error' for regression, 'log_loss' for binary."""

    def __init__(self, loss="squared_error", n_estimators=100, learning_rate=0.1,
                 max_depth=3, min_samples_leaf=1, newton_leaves=True):
        if loss not in ("squared_error", "log_loss"):
            raise ValueError("loss must be 'squared_error' or 'log_loss'")
        self.loss = loss
        self.n_estimators = n_estimators
        self.learning_rate = learning_rate
        self.max_depth = max_depth
        self.min_samples_leaf = min_samples_leaf
        self.newton_leaves = newton_leaves
        self.trees_ = []
        self.init_ = 0.0

    # ------------------------------------------------------------------ fit

    def fit(self, X, y):
        X = np.asarray(X, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64)
        if len(X) != len(y):
            raise ValueError(f"X has {len(X)} rows, y has {len(y)}")
        self.trees_ = []

        if self.loss == "squared_error":
            self.init_ = float(y.mean())
        else:
            if not set(np.unique(y)) <= {0.0, 1.0}:
                raise ValueError("log_loss needs y in {0, 1}")
            p = float(np.clip(y.mean(), EPS, 1 - EPS))
            self.init_ = float(np.log(p / (1 - p)))

        F = np.full(len(y), self.init_, dtype=np.float64)

        for _ in range(self.n_estimators):
            if self.loss == "squared_error":
                grad = y - F
            else:
                grad = y - sigmoid(F)

            tree = RegressionTree(max_depth=self.max_depth,
                                  min_samples_leaf=self.min_samples_leaf).fit(X, grad)

            if self.loss == "log_loss" and self.newton_leaves:
                self._newton_update(tree, X, grad, F)

            F += self.learning_rate * tree.predict(X)
            self.trees_.append(tree)
        return self

    def _newton_update(self, tree, X, grad, F):
        """Replace each leaf's mean residual with sum(g) / sum(h).

        The tree chose its splits by squared error on the gradient, which is
        correct. Only the value it puts in each leaf is wrong for log loss.
        """
        p = sigmoid(F)
        hess = p * (1.0 - p)
        ids = _leaf_ids(tree, X)

        sums = {}
        for leaf_id, g, h in zip(ids, grad, hess):
            s = sums.setdefault(leaf_id, [0.0, 0.0])
            s[0] += g
            s[1] += h

        def walk(node):
            if node.is_leaf:
                g, h = sums.get(id(node), (0.0, 0.0))
                node.value = g / h if h > EPS else 0.0
                return
            walk(node.left)
            walk(node.right)

        walk(tree.root)

    # -------------------------------------------------------------- predict

    def decision_function(self, X):
        X = np.asarray(X, dtype=np.float64)
        F = np.full(len(X), self.init_, dtype=np.float64)
        for tree in self.trees_:
            F += self.learning_rate * tree.predict(X)
        return F

    def predict(self, X):
        F = self.decision_function(X)
        return F if self.loss == "squared_error" else (F > 0).astype(int)

    def predict_proba(self, X):
        if self.loss != "log_loss":
            raise ValueError("predict_proba is only defined for log_loss")
        p = sigmoid(self.decision_function(X))
        return np.column_stack([1 - p, p])

    def staged_decision_function(self, X):
        """The score after each tree, for early-stopping experiments."""
        X = np.asarray(X, dtype=np.float64)
        F = np.full(len(X), self.init_, dtype=np.float64)
        for tree in self.trees_:
            F += self.learning_rate * tree.predict(X)
            yield F.copy()
