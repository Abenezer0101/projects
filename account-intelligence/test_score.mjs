/* Tests for the scoring model. Run: node test_score.mjs */
import { COMPANIES } from './data.js';
import { scoreCompany, signals, curve, tierOf, WEIGHTS, DEFAULT_PROFILE,
         financialHealth, growthMomentum, riskProfile, solvency } from './score.js';

let pass=0, fail=0;
const ok=(n,c,x='')=>{c?(pass++,console.log(`  PASS  ${n}`)):(fail++,console.log(`  FAIL  ${n} ${x}`));};
const base = COMPANIES[0];
const S = f => scoreCompany(f).score;

// weights
const total = Object.values(WEIGHTS).reduce((a,b)=>a+b,0);
ok('weights sum to 1', Math.abs(total-1) < 1e-9, `sum=${total}`);

// curve
ok('curve clamps below range', curve(-999,[[0,10],[10,90]])===10);
ok('curve clamps above range', curve(999,[[0,10],[10,90]])===90);
ok('curve interpolates midpoint', curve(5,[[0,0],[10,100]])===50);
ok('curve handles null as neutral', curve(null,[[0,0],[10,100]])===50);
ok('curve handles NaN as neutral', curve(NaN,[[0,0],[10,100]])===50);
ok('curve hits exact breakpoints', curve(10,[[0,0],[10,70],[20,100]])===70);

// tiers
ok('tier boundary at 70', tierOf(70)==='pursue' && tierOf(69.9)==='watch');
ok('tier boundary at 50', tierOf(50)==='watch' && tierOf(49.9)==='avoid');

// MONOTONICITY — the property that makes it a model rather than a lookup
ok('more revenue growth never lowers the score',
   S({...base, revenueGrowth:40}) >= S({...base, revenueGrowth:5}));
ok('higher gross margin never lowers the score',
   S({...base, grossMargin:75}) >= S({...base, grossMargin:30}));
ok('more debt never raises the score',
   S({...base, debtToEbitda:6}) <= S({...base, debtToEbitda:1}));
ok('more risk factors never raise the score',
   S({...base, riskFactorCount:70}) <= S({...base, riskFactorCount:12}));
ok('going concern lowers the score',
   S({...base, goingConcern:true}) < S({...base, goingConcern:false}));
ok('material weakness lowers the score',
   S({...base, materialWeakness:true}) < S({...base, materialWeakness:false}));
ok('longer cash runway never lowers the score',
   S({...base, cashRunwayMonths:60}) >= S({...base, cashRunwayMonths:6}));

// factor isolation
ok('risk score is inverted', riskProfile({...base, riskFactorCount:70, customerConcentration:60,
   goingConcern:true, materialWeakness:true, litigationMaterial:true}) <
   riskProfile({...base, riskFactorCount:5, customerConcentration:2,
   goingConcern:false, materialWeakness:false, litigationMaterial:false}));
ok('all factors stay within 0-100', COMPANIES.every(c=>{
   const f=scoreCompany(c).factors;
   return Object.values(f).every(v=>v>=0 && v<=100);}));
ok('composite stays within 0-100', COMPANIES.every(c=>{
   const s=scoreCompany(c).score; return s>=0 && s<=100;}));

// a tier can actually flip from data alone
const weak = {...base, revenueGrowth:-10, grossMargin:20, operatingMargin:-15, fcfMargin:-12,
              debtToEbitda:6, interestCoverage:0.5, currentRatio:0.7, cashRunwayMonths:5,
              riskFactorCount:70, goingConcern:true, materialWeakness:true};
ok('degrading the inputs flips pursue -> avoid',
   scoreCompany(base).tier==='pursue' && scoreCompany(weak).tier==='avoid',
   `${scoreCompany(base).tier} / ${scoreCompany(weak).tier}`);

// strategic fit responds to the buyer profile, not just the company
const offProfile = { targetSectors:['Hospitality'], adjacentSectors:[] };
ok('fit depends on the buyer profile',
   scoreCompany(base, offProfile).factors.fit < scoreCompany(base).factors.fit);

// signals must agree with the data that produced them
ok('going-concern company gets the going-concern signal',
   signals(COMPANIES.find(c=>c.goingConcern)).some(s=>/going-concern/i.test(s.text)));
ok('healthy company gets no going-concern signal',
   !signals(base).some(s=>/going-concern/i.test(s.text)));
ok('contracting revenue reads as negative',
   signals({...base, revenueGrowth:-8}).some(s=>s.kind==='neg' && /contracting/.test(s.text)));
ok('growing revenue reads as positive',
   signals({...base, revenueGrowth:30}).some(s=>s.kind==='pos' && /Revenue \+30%/.test(s.text)));
ok('every signal has a kind and text',
   COMPANIES.every(c=>signals(c).every(s=>['pos','neg','neu'].includes(s.kind) && s.text.length>5)));

// determinism
ok('scoring is deterministic', S(base)===S(base) && S(base)===S({...base}));

// the dataset itself carries no scores — they are all derived
ok('input data contains no score fields',
   COMPANIES.every(c=>!('score' in c) && !('factors' in c) && !('tier' in c)));

console.log(`\n${pass}/${pass+fail} passed`);
process.exit(fail?1:0);
