/* Expense tracker — state, persistence, and validation.
   Kept separate from index.html so the logic can be tested directly. */

const STORE_KEY = 'expense-tracker';
const SCHEMA_VERSION = 2;

export const CATEGORIES = ['Groceries','Dining','Transport','Housing','Utilities',
                           'Health','Shopping','Entertainment','Other'];

/* ---------------------------------------------------------------- storage */

/** Read state, migrating older schemas rather than discarding them. */
export function load(storage = localStorage) {
  let raw;
  try { raw = storage.getItem(STORE_KEY); } catch { return fresh(); }
  if (!raw) return fresh();
  let data;
  try { data = JSON.parse(raw); } catch { return fresh(); }   // corrupt -> start clean
  return migrate(data);
}

export function save(state, storage = localStorage) {
  try {
    storage.setItem(STORE_KEY, JSON.stringify({ ...state, version: SCHEMA_VERSION }));
    return true;
  } catch {
    return false;        // private mode / quota: the app keeps working in memory
  }
}

function fresh() {
  return { version: SCHEMA_VERSION, expenses: [], budgets: {} };
}

/** v1 stored a bare array of expenses with no budgets. */
function migrate(data) {
  if (Array.isArray(data)) return { version: SCHEMA_VERSION, expenses: data, budgets: {} };
  if (!data || typeof data !== 'object') return fresh();
  const out = {
    version: SCHEMA_VERSION,
    expenses: Array.isArray(data.expenses) ? data.expenses : [],
    budgets: (data.budgets && typeof data.budgets === 'object') ? data.budgets : {},
  };
  out.expenses = out.expenses.filter(e => validate(e).ok).map(normalize);
  return out;
}

/* ------------------------------------------------------------- validation */

export function validate(e) {
  if (!e || typeof e !== 'object') return { ok: false, error: 'not an expense' };
  const amount = Number(e.amount);
  if (!isFinite(amount) || amount <= 0) return { ok: false, error: 'Amount must be greater than zero' };
  if (amount > 1e7) return { ok: false, error: 'Amount is implausibly large' };
  if (!e.date || !/^\d{4}-\d{2}-\d{2}$/.test(e.date)) return { ok: false, error: 'Pick a valid date' };
  if (Number.isNaN(Date.parse(e.date))) return { ok: false, error: 'Pick a valid date' };
  if (!e.description || !String(e.description).trim()) return { ok: false, error: 'Description is required' };
  if (!CATEGORIES.includes(e.category)) return { ok: false, error: 'Choose a category' };
  return { ok: true };
}

export function normalize(e) {
  return {
    id: e.id || (Date.now().toString(36) + Math.random().toString(36).slice(2, 7)),
    date: e.date,
    description: String(e.description).trim().slice(0, 120),
    category: e.category,
    amount: Math.round(Number(e.amount) * 100) / 100,   // money is 2dp, always
  };
}

/* ---------------------------------------------------------------- derived */

export function totals(expenses) {
  const byCategory = {};
  let total = 0;
  for (const e of expenses) {
    byCategory[e.category] = round2((byCategory[e.category] || 0) + e.amount);
    total = round2(total + e.amount);
  }
  return { total, byCategory };
}

export function monthKey(dateStr) { return dateStr.slice(0, 7); }

export function byMonth(expenses) {
  const out = {};
  for (const e of expenses) out[monthKey(e.date)] = round2((out[monthKey(e.date)] || 0) + e.amount);
  return out;
}

/** Budget status per category. Returns over/near/under plus the ratio. */
export function budgetStatus(expenses, budgets) {
  const { byCategory } = totals(expenses);
  const rows = [];
  for (const cat of Object.keys(budgets)) {
    const limit = Number(budgets[cat]);
    if (!isFinite(limit) || limit <= 0) continue;
    const spent = byCategory[cat] || 0;
    const ratio = spent / limit;
    rows.push({ category: cat, spent, limit, ratio,
                state: ratio > 1 ? 'over' : ratio >= 0.8 ? 'near' : 'under' });
  }
  return rows.sort((a, b) => b.ratio - a.ratio);
}

const round2 = n => Math.round(n * 100) / 100;

/* ------------------------------------------------------------------- CSV */

/** Export in exactly the shape the budget-analyzer project consumes. */
export function toCSV(expenses) {
  const esc = v => /[",\n]/.test(v) ? `"${String(v).replace(/"/g, '""')}"` : String(v);
  const rows = [['date', 'description', 'amount']];
  for (const e of [...expenses].sort((a, b) => a.date.localeCompare(b.date))) {
    rows.push([e.date, esc(e.description), (-e.amount).toFixed(2)]);  // expenses are negative
  }
  return rows.map(r => r.join(',')).join('\n') + '\n';
}

export function fromCSV(text) {
  const lines = text.split(/\r?\n/).filter(l => l.trim());
  if (!lines.length) return { added: [], skipped: 0 };
  const head = lines[0].toLowerCase().split(',').map(s => s.trim());
  const di = head.indexOf('date'), si = head.indexOf('description'), ai = head.indexOf('amount');
  if (di < 0 || ai < 0) return { added: [], skipped: lines.length - 1, error: 'CSV needs date and amount columns' };
  const added = []; let skipped = 0;
  for (const line of lines.slice(1)) {
    const cells = splitCSVLine(line);
    const amt = Math.abs(Number(cells[ai]));
    const cand = { date: (cells[di] || '').trim(),
                   description: (cells[si] || 'Imported').trim() || 'Imported',
                   category: 'Other', amount: amt };
    if (validate(cand).ok) added.push(normalize(cand)); else skipped++;
  }
  return { added, skipped };
}

function splitCSVLine(line) {
  const out = []; let cur = '', q = false;
  for (let i = 0; i < line.length; i++) {
    const c = line[i];
    if (q) { if (c === '"') { if (line[i+1] === '"') { cur += '"'; i++; } else q = false; } else cur += c; }
    else if (c === '"') q = true;
    else if (c === ',') { out.push(cur); cur = ''; }
    else cur += c;
  }
  out.push(cur);
  return out;
}
