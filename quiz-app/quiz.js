/* Quiz generation and scoring, as pure functions.
 *
 * Questions are not authored, they are GENERATED from real datasets: any two
 * rows can be compared on any numeric column, and the dataset itself supplies
 * the correct answer. That removes the usual quiz-app failure -- a hand-typed
 * answer key that drifts out of sync with reality -- but introduces a new one:
 * a generator can happily emit a question with no correct answer (a tie), or
 * one whose two values are so close it is a coin flip. Both are guarded here
 * and tested.
 *
 * Difficulty is likewise derived rather than declared. The relative gap
 * between the two values decides the tier, so "hard" is a property of the
 * data, not a label someone typed.
 */

export function parseCSV(text) {
  const [head, ...rest] = String(text).trim().split(/\r?\n/);
  const cols = head.split(',');
  return rest.filter(l => l.trim()).map(line => {
    const cells = line.split(',');
    return Object.fromEntries(cols.map((c, i) => [c, cells[i]]));
  });
}

/** Deterministic PRNG, so a seed always rebuilds the same quiz. */
export function rng(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6D2B79F5) >>> 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export const TIERS = [
  { name: 'easy',   min: 0.40 },
  { name: 'medium', min: 0.12 },
  { name: 'hard',   min: 0.02 },
  { name: 'brutal', min: 0    },
];

/** Tier from the relative gap between the two values. */
export function tierFor(gap) {
  return (TIERS.find(t => gap >= t.min) || TIERS[TIERS.length - 1]).name;
}

/**
 * Every distinct pair of rows, as a candidate question.
 * Pairs whose values are exactly equal are dropped: they have no right answer,
 * and shipping one would be a question the user cannot get right.
 */
export function buildPool(rows, metric) {
  const { key, nameKey } = metric;
  const clean = rows
    .map(r => ({ name: r[nameKey], value: Number(String(r[key]).replace(/[^0-9.\-]/g, '')) }))
    .filter(r => r.name && Number.isFinite(r.value) && r.value > 0);

  const pool = [];
  for (let i = 0; i < clean.length; i++) {
    for (let j = i + 1; j < clean.length; j++) {
      const a = clean[i], b = clean[j];
      if (a.value === b.value) continue;            // a tie is unanswerable
      const hi = Math.max(a.value, b.value);
      const gap = (hi - Math.min(a.value, b.value)) / hi;
      pool.push({ metric, a, b, gap, tier: tierFor(gap), answer: a.value > b.value ? 'a' : 'b' });
    }
  }
  return pool;
}

/**
 * Draw n questions, spread across tiers so a quiz is never all-easy.
 *
 * Each tier is shuffled once and then drawn from round-robin. An earlier
 * version indexed the tier by how many questions had been picked so far,
 * which stalled forever on an empty tier and quietly returned FEWER
 * questions than the pool could supply. Popping from buckets makes both
 * repeats and that stall impossible by construction.
 */
export function makeQuiz(pools, { n = 10, seed = 1 } = {}) {
  const rand = rng(seed);
  const shuffle = arr => {                    // Fisher-Yates on the seeded rng
    const a = arr.slice();
    for (let i = a.length - 1; i > 0; i--) {
      const j = Math.floor(rand() * (i + 1));
      [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
  };

  const byTier = new Map(TIERS.map(t => [t.name, []]));
  for (const q of pools.flat()) byTier.get(q.tier).push(q);
  const buckets = TIERS.map(t => shuffle(byTier.get(t.name)));

  const picked = [];
  while (picked.length < n && buckets.some(b => b.length)) {
    for (const b of buckets) {
      if (picked.length >= n) break;
      const q = b.pop();
      if (!q) continue;
      // the correct side is shuffled so 'a' is not systematically the answer
      picked.push(rand() < 0.5 ? q : { ...q, a: q.b, b: q.a, answer: q.answer === 'a' ? 'b' : 'a' });
    }
  }
  return picked;
}

export const isCorrect = (q, choice) => choice === q.answer;

/**
 * Scoring. Confidence is the user's stated probability that their own answer
 * is right, so the Brier score measures calibration, not just accuracy:
 * always answering 0.5 scores 0.25, and confident-and-wrong is punished
 * harder than unsure-and-wrong.
 */
export function summarize(log) {
  const n = log.length;
  if (!n) return { n: 0, correct: 0, accuracy: 0, brier: null, byTier: [], calibration: [] };

  const correct = log.filter(e => e.correct).length;
  const brier = log.reduce((s, e) => s + (e.confidence - (e.correct ? 1 : 0)) ** 2, 0) / n;

  const byTier = TIERS.map(t => {
    const rows = log.filter(e => e.tier === t.name);
    return { tier: t.name, n: rows.length,
             accuracy: rows.length ? rows.filter(e => e.correct).length / rows.length : null };
  }).filter(r => r.n > 0);

  const levels = [...new Set(log.map(e => e.confidence))].sort((a, b) => a - b);
  const calibration = levels.map(c => {
    const rows = log.filter(e => e.confidence === c);
    return { confidence: c, n: rows.length,
             actual: rows.filter(e => e.correct).length / rows.length };
  });

  return { n, correct, accuracy: correct / n, brier, byTier, calibration };
}

/** Share of pairs closer together than `within` -- how coin-flippy a metric is. */
export function coinFlipShare(pool, within = 0.05) {
  return pool.length ? pool.filter(q => q.gap < within).length / pool.length : 0;
}
