# thicket

Gradient boosted trees written from scratch, and checked against
scikit-learn the way a SQL engine gets checked against SQLite: a second
implementation, written by other people for other reasons, that fails
differently.

```bash
pip install scikit-learn                 # the reference, not a dependency of the library
python3 -m thicket.cli validate          # diff against sklearn
python3 -m thicket.cli newton            # what the Newton leaf update is worth
python3 -m thicket.cli leakage           # selecting features before the split
python3 -m unittest discover -s tests    # 26 tests
```

The library itself needs only numpy. scikit-learn is used to check it.

## It is bit-identical to scikit-learn — until it isn't

On continuous data, agreement is exact at every depth and for both losses:

| | max abs difference | identical |
| --- | --- | --- |
| regression tree, depths 1–5 | 8.9e-16 | yes |
| boosted regressor, 60 trees | 8.9e-16 | yes |
| boosted classifier, 60 trees | 2.2e-16 | yes |

On **real** data it diverges, and the reason is worth more than the agreement.

Held out on scikit-learn's breast-cancer data: AUC 0.9890 against sklearn's
0.9895 — but max probability difference **0.20**, nowhere near machine
precision. Chasing it down, the root split matches exactly. The divergence
starts one level in, and it is not floating point:

```
right child, 190 rows
  mine:     feature 1  <= 16.110
  sklearn:  feature 21 <= 19.910
  SSE       6.2121727304  vs  6.2121727304   <- exactly equal
  partitions differ on 4 rows
```

Two different features produce **exactly the same** objective value while
placing four rows differently. It is a genuine tie, and which of two equally
optimal splits you take is arbitrary: `argmax` returns the lowest index, and
sklearn's scan lands elsewhere. Boosting then amplifies a four-row difference
across a hundred trees.

So the honest claim is not "matches scikit-learn". It is: identical where the
objective has a unique optimum, equally optimal where it does not. A test
asserts the tie exactly rather than asserting sameness.

## The Newton leaf update is a speed-up, not an accuracy win

Fitting a tree to the gradient `(y - p)` gives the right splits but the wrong
leaf values for log loss — the mean residual is not the step that minimises
it. The fix is a Newton step, `sum(g) / sum(h)` with `h = p(1-p)`. Skipping it
still trains and still improves, which is why it survives in a lot of
hand-rolled implementations.

`newton_leaves=False` keeps the shortcut available so the cost can be measured.
Twelve seeds, each run to its own best log loss over 600 trees:

| | mean best log loss | stdev | median trees to get there |
| --- | --- | --- | --- |
| Newton leaves | 0.5189 | 0.0229 | 52 |
| mean-residual leaves | 0.5220 | 0.0217 | 262 |

Accuracy difference: **−0.0031 ± 0.0044**, Newton lower on 8 of 12 seeds. The
spread is larger than the difference, so on this evidence the two reach the
same place. What is not in doubt is the **5.1× fewer trees**.

I first ran this on one seed, saw Newton win, and wrote down that the shortcut
"lands somewhere Newton never reaches". The next seed said the opposite. One
run of a stochastic procedure is a coin toss dressed as a result.

## 66% accuracy on a coin flip

The headline number, and the reason the rest of this exists.

Take 300 rows of **pure noise** — 3,000 gaussian features, label from a fair
coin. Nothing can predict it. Honest accuracy is exactly 50%.

Now make the ordinary mistake: pick the 20 features most correlated with the
target, then cross-validate on those.

```
  select on the FULL data, then cross-validate : 66.3%
  select inside each fold                      : 51.8%

  manufactured accuracy: +16.3%
```

Sixteen points of accuracy on data with no signal in it whatsoever, consistent
across every seed (65–68%). The selection has seen every row, including the
ones each fold is about to be tested on, so the folds were never held out —
they helped choose the inputs.

It does not throw. It does not warn. It produces exactly the kind of number
that ends up on a slide.

The fix is one line — select inside the fold — and it costs you the 16 points
that were never real.

## Layout

```
thicket/tree.py      exact greedy regression tree
thicket/gbm.py       boosting, squared error and log loss, Newton leaves
thicket/validate.py  differential comparison against scikit-learn
thicket/leakage.py   the noise experiment
thicket/cli.py       validate / newton / leakage
tests/               26 tests
```

Every number above is produced by the code and pinned by a test, including the
exact SSE tie.
