/* Logic tests — run with: node test_app.mjs   (no browser needed) */
import { load, save, validate, normalize, totals, byMonth, budgetStatus,
         toCSV, fromCSV, CATEGORIES } from './app.js';

let pass = 0, fail = 0;
const ok = (name, cond, extra='') => { cond ? (pass++, console.log(`  PASS  ${name}`))
                                            : (fail++, console.log(`  FAIL  ${name} ${extra}`)); };

/* a minimal localStorage stand-in */
const mem = () => { const m = new Map(); return {
  getItem: k => m.has(k) ? m.get(k) : null,
  setItem: (k, v) => m.set(k, v), removeItem: k => m.delete(k), _m: m }; };

const good = { date:'2026-03-04', description:'Kroger', category:'Groceries', amount:42.5 };

// validation
ok('rejects zero amount',      !validate({...good, amount:0}).ok);
ok('rejects negative amount',  !validate({...good, amount:-5}).ok);
ok('rejects absurd amount',    !validate({...good, amount:1e9}).ok);
ok('rejects bad date',         !validate({...good, date:'04/03/2026'}).ok);
ok('rejects impossible date',  !validate({...good, date:'2026-13-45'}).ok);
ok('rejects blank description',!validate({...good, description:'   '}).ok);
ok('rejects unknown category', !validate({...good, category:'Yacht'}).ok);
ok('accepts a good expense',   validate(good).ok);

// normalize
const n = normalize({...good, amount: 10.005, description: '  Trim me  '});
ok('rounds money to 2dp',      n.amount === 10.01, `got ${n.amount}`);
ok('trims description',        n.description === 'Trim me');
ok('assigns an id',            typeof n.id === 'string' && n.id.length > 4);
ok('ids are unique',           normalize(good).id !== normalize(good).id);

// totals
const set = [ {...good, amount:10}, {...good, amount:20}, {...good, category:'Dining', amount:5.5} ].map(normalize);
const t = totals(set);
ok('sums total',               t.total === 35.5, `got ${t.total}`);
ok('groups by category',       t.byCategory.Groceries === 30 && t.byCategory.Dining === 5.5);
ok('float-safe sums',          totals([{amount:0.1},{amount:0.2}]).total === 0.3,
                               `got ${totals([{amount:0.1},{amount:0.2}]).total}`);

// months
const m = byMonth([{date:'2026-01-05',amount:10},{date:'2026-01-20',amount:5},{date:'2026-02-01',amount:7}]);
ok('groups by month',          m['2026-01'] === 15 && m['2026-02'] === 7);

// budgets
const bs = budgetStatus(set, { Groceries: 25, Dining: 100, Transport: 0 });
ok('flags over budget',        bs.find(r=>r.category==='Groceries').state === 'over');
ok('flags under budget',       bs.find(r=>r.category==='Dining').state === 'under');
ok('ignores zero budgets',     !bs.find(r=>r.category==='Transport'));
ok('sorts worst first',        bs[0].category === 'Groceries');
const near = budgetStatus([normalize({...good, amount:85})], { Groceries: 100 });
ok('flags near budget at 80%', near[0].state === 'near', `got ${near[0].state}`);

// persistence
const s1 = mem();
save({ expenses: set, budgets: { Groceries: 25 } }, s1);
const reloaded = load(s1);
ok('round-trips expenses',     reloaded.expenses.length === 3);
ok('round-trips budgets',      reloaded.budgets.Groceries === 25);
ok('empty storage is safe',    load(mem()).expenses.length === 0);
const corrupt = mem(); corrupt.setItem('expense-tracker', '{not json');
ok('corrupt storage is safe',  load(corrupt).expenses.length === 0);
const v1 = mem(); v1.setItem('expense-tracker', JSON.stringify(set));   // old bare-array schema
ok('migrates v1 array schema', load(v1).expenses.length === 3);
const dirty = mem();
dirty.setItem('expense-tracker', JSON.stringify({ expenses:[good, {amount:-1}], budgets:{} }));
ok('drops invalid rows on load', load(dirty).expenses.length === 1);
const blocked = { getItem: () => null, setItem: () => { throw new Error('quota'); } };
ok('survives storage failure', save({expenses:[],budgets:{}}, blocked) === false);

// CSV
const csv = toCSV(set);
ok('csv has header',           csv.split('\n')[0] === 'date,description,amount');
ok('csv writes negatives',     csv.includes('-10.00'), csv.split('\n')[1]);
const quoted = toCSV([normalize({...good, description:'Cafe, "The Spot"'})]);
ok('csv escapes quotes+commas', quoted.includes('"Cafe, ""The Spot"""'), quoted);
const back = fromCSV(csv);
ok('csv round-trips count',    back.added.length === 3, `got ${back.added.length}`);
ok('csv import takes abs()',   back.added.every(e => e.amount > 0));
const badcsv = fromCSV('foo,bar\n1,2');
ok('csv rejects bad header',   badcsv.added.length === 0 && !!badcsv.error);
const partial = fromCSV('date,description,amount\n2026-01-01,ok,-5\nnotadate,bad,-5');
ok('csv counts skipped rows',  partial.added.length === 1 && partial.skipped === 1);

console.log(`\n${pass}/${pass+fail} passed`);
process.exit(fail ? 1 : 0);
