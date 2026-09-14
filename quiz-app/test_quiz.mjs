/* Tests for the quiz generator.  node test_quiz.mjs
 *
 * The generator's dangerous failure is not a crash, it is a plausible-looking
 * question with a wrong or impossible answer. Most of these tests check the
 * answer key against the underlying data rather than against itself.
 */
import fs from 'node:fs';
import { parseCSV, rng, tierFor, buildPool, makeQuiz, isCorrect, summarize, coinFlipShare, TIERS }
  from './quiz.js';

let pass = 0, fail = 0;
const ok = (n, c, x = '') => { c ? (pass++, console.log(`  PASS  ${n}`))
                                 : (fail++, console.log(`  FAIL  ${n} ${x}`)); };

const states = parseCSV(fs.readFileSync(new URL('./data/us_states.csv', import.meta.url), 'utf8'));
const countries = parseCSV(fs.readFileSync(new URL('./data/countries.csv', import.meta.url), 'utf8'));

const POP    = { key: 'Population2020', nameKey: 'State', label: 'population' };
const INCOME = { key: 'MedianHouseholdIncome', nameKey: 'State', label: 'median household income' };
const GDP    = { key: 'gdp_billions_usd', nameKey: 'country', label: 'GDP' };

/* ------------------------------------------------------------- parsing */
ok('parses every state row', states.length === 51, String(states.length));
ok('parses every country row', countries.length === 54, String(countries.length));
ok('header maps to fields', states[0].State === 'Alabama', states[0].State);

/* ------------------------------------------------------------ the pool */
const popPool = buildPool(states, POP);
const incPool = buildPool(states, INCOME);
const gdpPool = buildPool(countries, GDP);

ok('pool is every distinct pair', popPool.length === (51 * 50) / 2, String(popPool.length));

// the answer key is checked against the data, not against itself
ok('every answer key matches the underlying values',
   popPool.every(q => (q.answer === 'a') === (q.a.value > q.b.value)));
ok('same for a second metric',
   incPool.every(q => (q.answer === 'a') === (q.a.value > q.b.value)));

// a tie has no right answer, so it must never reach the user
ok('no question is a tie', [...popPool, ...incPool, ...gdpPool].every(q => q.a.value !== q.b.value));
ok('every gap is a real fraction',
   popPool.every(q => q.gap > 0 && q.gap <= 1 && Number.isFinite(q.gap)));
ok('rows with unusable values are dropped',
   buildPool([{ State: 'X', Population2020: 'n/a' }, { State: 'Y', Population2020: '5' },
              { State: '', Population2020: '9' }], POP).length === 0);

/* ------------------------------------------------------- difficulty */
ok('tiers run easy to brutal', tierFor(0.9) === 'easy' && tierFor(0.2) === 'medium'
   && tierFor(0.05) === 'hard' && tierFor(0.001) === 'brutal');
ok('tier boundaries are inclusive at the floor', tierFor(0.40) === 'easy' && tierFor(0.12) === 'medium');
// tier must be a function of the gap alone, for every real question
ok('every pooled question is in the tier its gap implies',
   [...popPool, ...incPool].every(q => q.tier === tierFor(q.gap)));

/* -------------------------------------------------- the actual finding
 * Income spans far less than population, so far more income pairs are
 * effectively coin flips. This is the claim the README makes; assert it. */
const popFlip = coinFlipShare(popPool), incFlip = coinFlipShare(incPool);
ok('income pairs are closer together than population pairs', incFlip > popFlip * 4,
   `income ${(incFlip*100).toFixed(1)}% vs population ${(popFlip*100).toFixed(1)}%`);
ok('income coin-flip share is ~17%', Math.abs(incFlip - 0.173) < 0.01, (incFlip*100).toFixed(1));
ok('population coin-flip share is ~2%', Math.abs(popFlip - 0.020) < 0.01, (popFlip*100).toFixed(1));

/* ------------------------------------------------------------- quizzes */
const q1 = makeQuiz([popPool, incPool], { n: 12, seed: 42 });
const q2 = makeQuiz([popPool, incPool], { n: 12, seed: 42 });
const q3 = makeQuiz([popPool, incPool], { n: 12, seed: 43 });

ok('a quiz has the requested length', q1.length === 12, String(q1.length));
ok('the same seed rebuilds the same quiz',
   JSON.stringify(q1) === JSON.stringify(q2));
ok('a different seed gives a different quiz', JSON.stringify(q1) !== JSON.stringify(q3));
ok('no question repeats inside a quiz',
   new Set(q1.map(q => `${q.metric.key}|${q.a.name}|${q.b.name}`)).size === 12);
ok('a quiz spans more than one tier', new Set(q1.map(q => q.tier)).size > 1);
ok('answer keys survive the side-shuffle',
   q1.every(q => (q.answer === 'a') === (q.a.value > q.b.value)));
// if the shuffle were broken, 'a' would always be correct
const aShare = makeQuiz([popPool, incPool], { n: 200, seed: 7 }).filter(q => q.answer === 'a').length / 200;
ok('the correct side is not always the same one', aShare > 0.3 && aShare < 0.7, aShare.toFixed(2));
ok('grading agrees with the key', q1.every(q => isCorrect(q, q.answer) && !isCorrect(q, q.answer === 'a' ? 'b' : 'a')));
ok('asking for more than exist still terminates',
   makeQuiz([buildPool(states.slice(0, 3), POP)], { n: 999, seed: 1 }).length === 3);

/* -------------------------------------------------------------- rng */
ok('rng is deterministic', rng(5)() === rng(5)());
ok('rng stays in [0,1)', Array.from({ length: 500 }, (_, i) => rng(i)()).every(v => v >= 0 && v < 1));

/* ------------------------------------------------------------ scoring */
const mk = (correct, confidence, tier = 'easy') => ({ correct, confidence, tier });
const s = summarize([mk(true, 1), mk(false, 1), mk(true, .5), mk(false, .5)]);
ok('counts accuracy', s.accuracy === 0.5);
ok('brier is the mean squared error', Math.abs(s.brier - ((0 + 1 + .25 + .25) / 4)) < 1e-12, String(s.brier));
ok('a perfect confident run scores 0', summarize([mk(true, 1), mk(true, 1)]).brier === 0);
ok('confidently wrong scores 1', summarize([mk(false, 1)]).brier === 1);
ok('always guessing 50% scores .25',
   summarize([mk(true, .5), mk(false, .5)]).brier === 0.25);
ok('empty log does not divide by zero', summarize([]).n === 0 && summarize([]).brier === null);
const t = summarize([mk(true, 1, 'easy'), mk(false, 1, 'hard'), mk(true, 1, 'hard')]);
ok('per-tier accuracy is computed', t.byTier.find(r => r.tier === 'hard').accuracy === 0.5);
ok('tiers with no questions are omitted', t.byTier.length === 2);
ok('calibration groups by stated confidence',
   summarize([mk(true, .75), mk(false, .75), mk(true, 1)]).calibration.length === 2);
ok('calibration reports the observed rate',
   summarize([mk(true, .75), mk(false, .75)]).calibration[0].actual === 0.5);

console.log(`\n${pass}/${pass + fail} passed`);
process.exit(fail ? 1 : 0);
