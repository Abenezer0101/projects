/* Account scoring model.
 *
 * The point of this module: every score is DERIVED from financial line items,
 * not assigned. Change a company's revenue growth and its Growth Momentum
 * score moves, its composite moves, and its tier may flip. Nothing is typed in.
 *
 * Each factor maps raw financials onto 0-100 through a documented piecewise
 * curve, then the composite is a weighted blend.
 */

export const WEIGHTS = {
  financial:  0.25,   // can they pay, and is the business sound
  growth:     0.20,   // are they expanding
  marketing:  0.18,   // are they actively spending into demand
  solvency:   0.15,   // can they survive a bad year
  risk:       0.12,   // inverted: how much is flagged against them
  fit:        0.10,   // do they look like our customer
};

export const FACTOR_LABELS = {
  financial: 'Financial Health', growth: 'Growth Momentum',
  marketing: 'Marketing Intensity', solvency: 'Solvency & Liquidity',
  risk: 'Risk Profile', fit: 'Strategic Fit',
};

/** Map a value onto 0-100 through breakpoints: [[input, output], ...] ascending. */
export function curve(value, points) {
  if (value == null || Number.isNaN(value)) return 50;        // unknown -> neutral
  if (value <= points[0][0]) return points[0][1];
  const last = points[points.length - 1];
  if (value >= last[0]) return last[1];
  for (let i = 1; i < points.length; i++) {
    const [x0, y0] = points[i - 1], [x1, y1] = points[i];
    if (value <= x1) return y0 + (value - x0) / (x1 - x0) * (y1 - y0);
  }
  return last[1];
}

const clamp = (n, lo = 0, hi = 100) => Math.max(lo, Math.min(hi, n));

/* ------------------------------------------------------------- factors */

export function financialHealth(f) {
  const gross = curve(f.grossMargin,     [[10,10],[30,40],[50,70],[70,95]]);
  const oper  = curve(f.operatingMargin, [[-20,0],[0,35],[10,65],[25,95]]);
  const fcf   = curve(f.fcfMargin,       [[-15,0],[0,40],[12,75],[25,95]]);
  return clamp(gross * 0.35 + oper * 0.40 + fcf * 0.25);
}

export function growthMomentum(f) {
  const rev  = curve(f.revenueGrowth,  [[-15,0],[0,30],[10,55],[25,80],[45,100]]);
  const keep = curve(f.netRetention,   [[80,10],[100,50],[115,80],[130,100]]);
  const back = curve(f.backlogGrowth,  [[-20,10],[0,45],[20,80],[40,100]]);
  return clamp(rev * 0.50 + keep * 0.30 + back * 0.20);
}

/** Spend into demand is a buying signal: high intensity AND rising. */
export function marketingIntensity(f) {
  const level = curve(f.sgaPctRevenue,  [[5,15],[15,50],[25,80],[40,95]]);
  const trend = curve(f.sgaGrowth,      [[-15,5],[0,40],[15,75],[30,100]]);
  const ad    = curve(f.adSpendGrowth,  [[-20,5],[0,40],[20,80],[40,100]]);
  return clamp(level * 0.35 + trend * 0.35 + ad * 0.30);
}

export function solvency(f) {
  const lev  = curve(-f.debtToEbitda,     [[-6,5],[-4,25],[-2,60],[-1,85],[0,95]]);
  const cov  = curve(f.interestCoverage,  [[0,0],[2,35],[5,70],[12,95]]);
  const cur  = curve(f.currentRatio,      [[0.5,5],[1.0,40],[1.5,75],[2.5,95]]);
  const cash = curve(f.cashRunwayMonths,  [[3,5],[12,45],[24,80],[48,100]]);
  return clamp(lev * 0.30 + cov * 0.30 + cur * 0.20 + cash * 0.20);
}

/** Inverted: more flagged risk means a LOWER score. */
export function riskProfile(f) {
  let s = 100;
  s -= curve(f.riskFactorCount,       [[10,0],[25,20],[45,45],[70,60]]);
  s -= curve(f.customerConcentration, [[5,0],[20,12],[35,28],[60,45]]);
  if (f.goingConcern) s -= 35;
  if (f.materialWeakness) s -= 15;
  if (f.litigationMaterial) s -= 8;
  return clamp(s);
}

export function strategicFit(f, profile) {
  const sector = profile.targetSectors.includes(f.sector) ? 100
               : profile.adjacentSectors.includes(f.sector) ? 55 : 20;
  const size = curve(f.revenueMillions, [[50,25],[250,65],[1000,95],[5000,80],[20000,55]]);
  const tech = curve(f.techSpendPctRevenue, [[1,15],[4,55],[8,85],[15,100]]);
  return clamp(sector * 0.45 + size * 0.30 + tech * 0.25);
}

/* ------------------------------------------------------------ composite */

export function scoreCompany(f, profile = DEFAULT_PROFILE) {
  const factors = {
    financial: financialHealth(f),
    growth:    growthMomentum(f),
    marketing: marketingIntensity(f),
    solvency:  solvency(f),
    risk:      riskProfile(f),
    fit:       strategicFit(f, profile),
  };
  let composite = 0;
  for (const k of Object.keys(WEIGHTS)) composite += factors[k] * WEIGHTS[k];
  const rounded = {};
  for (const k of Object.keys(factors)) rounded[k] = Math.round(factors[k]);
  return { ...f, factors: rounded, score: Math.round(composite), tier: tierOf(composite) };
}

export function tierOf(score) {
  return score >= 70 ? 'pursue' : score >= 50 ? 'watch' : 'avoid';
}

export const DEFAULT_PROFILE = {
  targetSectors:   ['Enterprise SaaS', 'Fintech', 'Semiconductors', 'MedTech'],
  adjacentSectors: ['Omnichannel Retail', 'Logistics', 'Media'],
};

/* --------------------------------------------------------------- signals
 * Generated from the numbers, so a signal can never contradict the score
 * that sits beside it -- which is exactly what hand-written signal text does
 * the moment anyone edits the data. */

export function signals(c) {
  const out = [];
  const add = (kind, text) => out.push({ kind, text });

  if (c.revenueGrowth >= 20) add('pos', `Revenue +${c.revenueGrowth}% YoY`);
  else if (c.revenueGrowth < 0) add('neg', `Revenue ${c.revenueGrowth}% YoY — contracting`);
  else add('neu', `Revenue +${c.revenueGrowth}% YoY — modest`);

  if (c.netRetention >= 110) add('pos', `Net retention ${c.netRetention}% — expansion outpaces churn`);
  else if (c.netRetention < 95) add('neg', `Net retention ${c.netRetention}% — churn exceeds expansion`);

  if (c.sgaGrowth >= 15) add('pos', `SG&A +${c.sgaGrowth}% — actively spending into demand`);
  else if (c.sgaGrowth <= -5) add('neg', `SG&A ${c.sgaGrowth}% — cost-cutting, budgets likely frozen`);

  if (c.grossMargin >= 60) add('pos', `Gross margin ${c.grossMargin}% — pricing power`);
  else if (c.grossMargin < 25) add('neg', `Gross margin ${c.grossMargin}% — thin`);

  if (c.goingConcern) add('neg', 'Going-concern language present in the filing');
  if (c.materialWeakness) add('neg', 'Material weakness disclosed in internal controls');
  if (c.debtToEbitda >= 4) add('neg', `Debt/EBITDA ${c.debtToEbitda}× — leveraged`);
  else if (c.debtToEbitda <= 1.5) add('pos', `Debt/EBITDA ${c.debtToEbitda}× — conservative`);

  if (c.interestCoverage < 2) add('neg', `Interest coverage ${c.interestCoverage}× — thin headroom`);
  if (c.customerConcentration >= 30)
    add('neu', `Top-10 customers are ${c.customerConcentration}% of revenue`);
  if (c.cashRunwayMonths < 18)
    add('neg', `Cash runway ~${c.cashRunwayMonths} months`);
  if (c.riskFactorCount >= 40)
    add('neu', `${c.riskFactorCount} risk factors enumerated — dense disclosure`);

  return out;
}
