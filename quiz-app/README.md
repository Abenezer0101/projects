# Calibration Quiz

A quiz where the questions are generated from real data rather than written by
hand, and the score measures how well you know what you know.

**[Play it →](https://abenezer0101.github.io/projects/quiz-app/)**

## Questions nobody wrote

Every question is a comparison drawn from a dataset: two US states on
population or median household income, two countries on population or GDP. The
data supplies the answer key, so the key cannot drift out of sync with reality
the way a hand-typed one does.

That trade buys correctness and introduces a different failure. A generator
will happily emit a question with **no** right answer — two rows whose values
are identical — and ship it looking exactly like every other question. Ties are
dropped at pool construction, and the test suite asserts against the source
data rather than against the generator's own output, because a generator that
is confidently wrong agrees with itself.

## Difficulty is measured, not labelled

A question's tier comes from the relative gap between the two real values, so
"hard" is a fact about the data instead of a judgement someone typed:

| Tier | Gap between the two values |
| --- | --- |
| easy | 40% or more |
| medium | 12–40% |
| hard | 2–12% |
| brutal | under 2% |

This produces the project's actual finding. **A metric's dynamic range decides
how hard its questions are.** Across all 1,275 pairs of US states:

| Metric | Range | Max ÷ min | Median gap | Pairs within 5% |
| --- | --- | --- | --- | --- |
| Population | 576,851 – 39,538,223 | 68.5× | 65.1% | **2.0%** |
| Median household income | \$52,719 – \$101,722 | 1.9× | 15.6% | **17.3%** |

Income questions are roughly eight times more likely to be a coin flip, and not
because incomes are obscure — because American incomes genuinely sit close
together. Population spans two orders of magnitude; income barely spans one
doubling. Two tests pin those percentages so the claim above cannot quietly rot.

## Scoring: accuracy is the boring half

After choosing, you state how sure you are (50%, 75%, 100%). That turns the
result into a **Brier score** — the mean squared error of your stated
confidence:

- 0.000 — every answer right and you said so
- 0.250 — what you get for answering "guessing" to everything
- 1.000 — certain, and wrong, every time

Confident-and-wrong is penalised four times harder than unsure-and-wrong, which
is the whole point: it costs something to claim certainty.

One design bug came out of this and was only visible on screen. The question
card originally displayed the tier and the gap **before** you answered — which
tells you how close the two values are, changing the confidence you report.
That silently corrupts the only thing the app measures. Difficulty is now
revealed after you commit.

## Verification

```
node test_quiz.mjs                # 36 unit tests
node e2e_quiz.js /tmp/out         # 18 browser tests (serve the repo on :8094)
```

The browser tests play two full quizzes by reading the answer key from the
page's own state — one answering everything correctly at full confidence, one
answering everything wrong at full confidence — and assert the reported Brier
score is exactly 0 and exactly 1. Anything wrong in the wiring between the
grader and the display moves those numbers off their end points.

## Data

`data/us_states.csv` — 51 rows, 2020 census population and median household
income. `data/countries.csv` — 54 rows, population and GDP. Both are the same
files used by other projects in this repo.
