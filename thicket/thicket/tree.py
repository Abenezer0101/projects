"""A regression tree, written to be checked rather than trusted.

Gradient boosting fits trees to gradients, so the weak learner only ever solves
one problem: given a vector of targets and a design matrix, find the split that
most reduces squared error, recurse, and average the leaves.

The split search is exact rather than histogram-binned. That is slower and it
is the point -- an exact tree can be compared against scikit-learn's exact
tree and expected to agree, which is how the rest of this library is validated.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class Node:
    value: float = 0.0
    feature: int = -1
    threshold: float = 0.0
    left: "Node" = None
    right: "Node" = None

    @property
    def is_leaf(self) -> bool:
        return self.left is None


def _best_split(X, g, min_samples_leaf):
    """The split minimising the sum of squared error of the two children.

    SSE for a group is  sum(y^2) - sum(y)^2 / n, so sweeping a sorted feature
    needs only running sums. Comparing total SSE is equivalent to maximising
    the usual variance-reduction gain, without the extra arithmetic.
    """
    n, n_features = X.shape
    if n < 2 * min_samples_leaf:
        return None

    total_sum = g.sum()
    best = None

    for f in range(n_features):
        order = np.argsort(X[:, f], kind="mergesort")
        xs, gs = X[order, f], g[order]
        csum = np.cumsum(gs)

        # a split is only legal between two DIFFERENT feature values; splitting
        # inside a run of ties would put identical rows on opposite sides
        left_n = np.arange(1, n)
        legal = xs[1:] != xs[:-1]
        legal &= left_n >= min_samples_leaf
        legal &= (n - left_n) >= min_samples_leaf
        if not legal.any():
            continue

        left_sum = csum[:-1]
        right_sum = total_sum - left_sum
        right_n = n - left_n
        # the part of SSE that varies with the split
        score = (left_sum ** 2) / left_n + (right_sum ** 2) / right_n
        score = np.where(legal, score, -np.inf)

        i = int(np.argmax(score))
        if not np.isfinite(score[i]):
            continue
        if best is None or score[i] > best[0]:
            thr = (xs[i] + xs[i + 1]) / 2.0
            best = (float(score[i]), f, float(thr))

    return None if best is None else best[1:]


class RegressionTree:
    def __init__(self, max_depth=3, min_samples_leaf=1, min_samples_split=2):
        self.max_depth = max_depth
        self.min_samples_leaf = min_samples_leaf
        self.min_samples_split = min_samples_split
        self.root = None

    def fit(self, X, y):
        X = np.asarray(X, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64)
        if X.ndim != 2:
            raise ValueError("X must be 2-d")
        if len(X) != len(y):
            raise ValueError(f"X has {len(X)} rows, y has {len(y)}")
        self.root = self._build(X, y, depth=0)
        return self

    def _build(self, X, y, depth):
        node = Node(value=float(y.mean()) if len(y) else 0.0)
        if (depth >= self.max_depth or len(y) < self.min_samples_split
                or np.all(y == y[0])):
            return node

        split = _best_split(X, y, self.min_samples_leaf)
        if split is None:
            return node
        f, thr = split
        mask = X[:, f] <= thr
        if mask.all() or (~mask).any() is False:
            return node

        node.feature, node.threshold = f, thr
        node.left = self._build(X[mask], y[mask], depth + 1)
        node.right = self._build(X[~mask], y[~mask], depth + 1)
        return node

    def predict(self, X):
        X = np.asarray(X, dtype=np.float64)
        return np.array([self._walk(self.root, row) for row in X])

    def _walk(self, node, row):
        while not node.is_leaf:
            node = node.left if row[node.feature] <= node.threshold else node.right
        return node.value

    def depth(self) -> int:
        def d(n):
            return 0 if n.is_leaf else 1 + max(d(n.left), d(n.right))
        return d(self.root) if self.root else 0

    def n_leaves(self) -> int:
        def c(n):
            return 1 if n.is_leaf else c(n.left) + c(n.right)
        return c(self.root) if self.root else 0
