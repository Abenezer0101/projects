"""python3 -m unittest discover -s tests

The differential tests are the backbone: scikit-learn is a second
implementation written by other people for other reasons, so agreement to
machine precision says far more than any assertion about my own arithmetic.

Exact agreement is only expected where the objective has no ties. Where it
does -- and real data is full of them -- the tests check that both answers are
equally optimal, not that they are the same answer.
"""

import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from thicket import leakage, validate
from thicket.gbm import GradientBoosting, sigmoid
from thicket.tree import RegressionTree, _best_split


def smooth(n=300, d=6, seed=0):
    """Continuous features: no tied values, so no ties in the objective."""
    rng = np.random.default_rng(seed)
    X = rng.normal(size=(n, d))
    y = 2 * X[:, 0] - 1.5 * X[:, 1] + 0.5 * X[:, 2] ** 2 + rng.normal(scale=.3, size=n)
    return X, y


class TestTree(unittest.TestCase):
    def test_matches_sklearn_exactly_at_every_depth(self):
        X, y = smooth()
        for depth in (1, 2, 3, 4, 5):
            r = validate.compare_tree(X, y, max_depth=depth)
            self.assertTrue(r["identical"], f"depth {depth}: {r}")
            self.assertEqual(r["leaves_mine"], r["leaves_sklearn"], depth)

    def test_a_constant_target_produces_one_leaf(self):
        X, _ = smooth(80)
        t = RegressionTree(max_depth=4).fit(X, np.full(80, 3.0))
        self.assertEqual(t.n_leaves(), 1)
        self.assertTrue(np.allclose(t.predict(X), 3.0))

    def test_depth_is_respected(self):
        X, y = smooth(200)
        for d in (1, 2, 3):
            self.assertLessEqual(RegressionTree(max_depth=d).fit(X, y).depth(), d)

    def test_min_samples_leaf_is_respected(self):
        X, y = smooth(200)
        t = RegressionTree(max_depth=6, min_samples_leaf=25).fit(X, y)
        counts = {}
        for row in X:
            n = t.root
            while not n.is_leaf:
                n = n.left if row[n.feature] <= n.threshold else n.right
            counts[id(n)] = counts.get(id(n), 0) + 1
        self.assertGreaterEqual(min(counts.values()), 25, counts)

    def test_a_split_never_lands_inside_a_run_of_ties(self):
        """Identical rows must not be sent to opposite sides."""
        X = np.array([[1.0], [1.0], [1.0], [2.0], [2.0], [2.0]])
        y = np.array([0.0, 0.0, 0.0, 1.0, 1.0, 1.0])
        split = _best_split(X, y, 1)
        self.assertIsNotNone(split)
        _, thr = split
        self.assertTrue(1.0 < thr < 2.0, thr)

    def test_a_single_repeated_value_cannot_be_split(self):
        X = np.ones((10, 3))
        self.assertIsNone(_best_split(X, np.arange(10.0), 1))

    def test_mismatched_lengths_are_refused(self):
        with self.assertRaises(ValueError):
            RegressionTree().fit(np.zeros((5, 2)), np.zeros(4))


class TestBoosting(unittest.TestCase):
    def test_regressor_matches_sklearn(self):
        X, y = smooth(300, seed=1)
        r = validate.compare_regressor(X, y)
        self.assertTrue(r["identical"], r)

    def test_classifier_matches_sklearn(self):
        X, y = smooth(300, seed=2)
        yb = (y > np.median(y)).astype(int)
        r = validate.compare_classifier(X, yb)
        self.assertTrue(r["identical"], r)
        self.assertEqual(r["label_agreement"], 1.0)

    def test_more_trees_fit_the_training_data_better(self):
        X, y = smooth(250, seed=3)
        errs = []
        for m in (5, 20, 80):
            g = GradientBoosting("squared_error", n_estimators=m, max_depth=3).fit(X, y)
            errs.append(float(((g.predict(X) - y) ** 2).mean()))
        self.assertEqual(errs, sorted(errs, reverse=True), errs)

    def test_zero_trees_predicts_the_initial_value(self):
        X, y = smooth(100, seed=4)
        g = GradientBoosting("squared_error", n_estimators=0).fit(X, y)
        self.assertTrue(np.allclose(g.predict(X), y.mean()))

    def test_classifier_initial_value_is_the_base_log_odds(self):
        X, y = smooth(200, seed=5)
        yb = (y > np.median(y)).astype(int)
        g = GradientBoosting("log_loss", n_estimators=0).fit(X, yb)
        p = g.predict_proba(X)[:, 1]
        self.assertAlmostEqual(float(p[0]), float(yb.mean()), places=6)

    def test_probabilities_are_valid_and_sum_to_one(self):
        X, y = smooth(200, seed=6)
        yb = (y > np.median(y)).astype(int)
        p = GradientBoosting("log_loss", n_estimators=30).fit(X, yb).predict_proba(X)
        self.assertTrue(np.all((p >= 0) & (p <= 1)))
        self.assertTrue(np.allclose(p.sum(axis=1), 1.0))

    def test_staged_scores_end_where_the_final_one_does(self):
        X, y = smooth(150, seed=7)
        g = GradientBoosting("squared_error", n_estimators=25).fit(X, y)
        last = list(g.staged_decision_function(X))[-1]
        self.assertTrue(np.allclose(last, g.decision_function(X)))

    def test_log_loss_refuses_labels_that_are_not_zero_or_one(self):
        X, y = smooth(60, seed=8)
        with self.assertRaises(ValueError):
            GradientBoosting("log_loss").fit(X, y)

    def test_an_unknown_loss_is_refused(self):
        with self.assertRaises(ValueError):
            GradientBoosting("hinge")

    def test_predict_proba_is_refused_for_regression(self):
        X, y = smooth(60, seed=9)
        g = GradientBoosting("squared_error", n_estimators=5).fit(X, y)
        with self.assertRaises(ValueError):
            g.predict_proba(X)

    def test_the_newton_step_changes_the_leaves_not_the_splits(self):
        """Same splits both ways; only the value in each leaf differs."""
        X, y = smooth(300, seed=10)
        yb = (y > np.median(y)).astype(int)
        a = GradientBoosting("log_loss", n_estimators=1, newton_leaves=True).fit(X, yb)
        b = GradientBoosting("log_loss", n_estimators=1, newton_leaves=False).fit(X, yb)
        def structure(node):
            return ([] if node.is_leaf
                    else [(node.feature, node.threshold)]
                         + structure(node.left) + structure(node.right))

        def leaves(node):
            return [node.value] if node.is_leaf else leaves(node.left) + leaves(node.right)

        ta, tb = a.trees_[0].root, b.trees_[0].root
        self.assertEqual(structure(ta), structure(tb))        # identical splits
        # the Newton step only rewrites LEAVES -- root.left is an internal node
        # at max_depth 3, which is why comparing it found no difference
        self.assertNotEqual(leaves(ta), leaves(tb))


class TestRealDataTies(unittest.TestCase):
    """Real data has exact ties in the objective, and tie-breaking is
    implementation-defined. Both answers are optimal; they are not the same."""

    def test_real_data_models_agree_on_quality_if_not_on_structure(self):
        r = validate.real_data_check()
        self.assertAlmostEqual(r["auc_mine"], r["auc_sklearn"], places=2)
        self.assertGreater(r["auc_mine"], 0.95)

    def test_two_features_can_score_identically(self):
        """The concrete tie found in the breast-cancer data: features 1 and 21
        give exactly the same objective and place 4 rows differently."""
        from sklearn.datasets import load_breast_cancer
        X, y = load_breast_cancer(return_X_y=True)
        yf = y.astype(float)
        right = X[:, 20] > 16.795
        v = yf[right]
        a = X[right, 1] <= 16.110
        b = X[right, 21] <= 19.910

        def sse(mask):
            return sum(((v[m] - v[m].mean()) ** 2).sum() for m in (mask, ~mask) if m.any())

        self.assertEqual(sse(a), sse(b))          # exactly equal, not merely close
        self.assertFalse(np.array_equal(a, b))    # yet different partitions


class TestLeakage(unittest.TestCase):
    def test_the_noise_dataset_really_is_noise(self):
        X, y = leakage.noise_dataset(200, 500, seed=0)
        self.assertEqual(X.shape, (200, 500))
        self.assertTrue(set(np.unique(y)) <= {0, 1})

    def test_selecting_before_the_split_invents_accuracy(self):
        """Ground truth is exactly 50%: the label is a coin."""
        X, y = leakage.noise_dataset(300, 2000, seed=1)
        leaked, _ = leakage.cv_score(X, y, 20, select_inside=False, seed=1)
        self.assertGreater(leaked, 0.60, leaked)

    def test_selecting_inside_the_fold_does_not(self):
        X, y = leakage.noise_dataset(300, 2000, seed=1)
        honest, _ = leakage.cv_score(X, y, 20, select_inside=True, seed=1)
        self.assertLess(honest, 0.60, honest)

    def test_the_gap_is_large_and_consistent(self):
        r = leakage.demonstrate(n_rows=250, n_features=1500, k_features=15, seeds=4)
        self.assertGreater(r["leaked_mean"] - r["honest_mean"], 0.08, r)
        self.assertGreater(r["leaked_mean"], 0.60, r)
        self.assertLess(abs(r["honest_mean"] - 0.5), 0.08, r)

    def test_selection_returns_the_requested_number_of_features(self):
        X, y = leakage.noise_dataset(100, 300, seed=2)
        self.assertEqual(len(leakage.select_by_correlation(X, y, 12)), 12)

    def test_selection_finds_a_planted_signal(self):
        """The selector has to actually work, or the demonstration proves
        nothing about selection."""
        rng = np.random.default_rng(3)
        X = rng.normal(size=(400, 200))
        y = (X[:, 7] + 0.3 * rng.normal(size=400) > 0).astype(int)
        self.assertIn(7, leakage.select_by_correlation(X, y, 5))


if __name__ == "__main__":
    unittest.main(verbosity=1)
