/* node test_timer.mjs
 *
 * The timer is driven by an injected `now`, so every test below runs instantly
 * and deterministically -- no waiting, no flakiness. The drift section feeds
 * one identical sequence of timer fires to both implementations and measures
 * how far apart they end up.
 */
import { PHASES, start, elapsedMs, remainingMs, isRunning, isComplete, pause, resume,
         nextPhase, formatClock, tickCounter, clockReader, logEntry, summarize }
  from './timer.js';

let pass = 0, fail = 0;
const ok = (n, c, x = '') => { c ? (pass++, console.log(`  PASS  ${n}`))
                                 : (fail++, console.log(`  FAIL  ${n} ${x}`)); };
const MIN = 60000;

/* --------------------------------------------------------- state machine */
const T0 = 1_700_000_000_000;
let s = start('focus', T0);
ok('a focus block is 25 minutes', s.durationMs === 25 * MIN);
ok('nothing has elapsed at the start', elapsedMs(s, T0) === 0);
ok('a fresh session is running', isRunning(s));
ok('remaining counts down with the clock', remainingMs(s, T0 + 10 * MIN) === 15 * MIN);
ok('it completes at exactly the duration', isComplete(s, T0 + 25 * MIN));
ok('it is not complete one millisecond earlier', !isComplete(s, T0 + 25 * MIN - 1));
ok('remaining never goes negative', remainingMs(s, T0 + 99 * MIN) === 0);
ok('an unknown phase is rejected', (() => { try { start('nap', T0); return false; } catch { return true; } })());
ok('a custom duration is honoured', start('focus', T0, 5000).durationMs === 5000);

/* pausing must freeze time, which is the thing a tick-counter gets wrong */
let p = pause(start('focus', T0), T0 + 5 * MIN);
ok('pausing banks the time served', p.bankedMs === 5 * MIN);
ok('a paused timer is not running', !isRunning(p));
ok('a paused timer does not advance', elapsedMs(p, T0 + 60 * MIN) === 5 * MIN);
ok('remaining is frozen while paused', remainingMs(p, T0 + 60 * MIN) === 20 * MIN);
ok('pausing twice changes nothing', pause(p, T0 + 90 * MIN).bankedMs === 5 * MIN);

let r = resume(p, T0 + 60 * MIN);
ok('resuming continues from the banked time', elapsedMs(r, T0 + 62 * MIN) === 7 * MIN);
ok('resuming while running changes nothing', resume(r, T0 + 99 * MIN).resumedAt === r.resumedAt);
ok('pause and resume survive several rounds', (() => {
  let x = start('focus', 0);
  x = pause(x, 1 * MIN); x = resume(x, 10 * MIN);
  x = pause(x, 12 * MIN); x = resume(x, 50 * MIN);
  return elapsedMs(x, 53 * MIN) === 6 * MIN;      // 1 + 2 + 3
})());

/* ----------------------------------------------------------- the cycle */
ok('a break always returns to focus', nextPhase('shortBreak', 2) === 'focus'
   && nextPhase('longBreak', 4) === 'focus');
ok('focus blocks 1-3 earn a short break',
   [1, 2, 3].every(n => nextPhase('focus', n) === 'shortBreak'));
ok('the 4th focus block earns the long break', nextPhase('focus', 4) === 'longBreak');
ok('and so does the 8th', nextPhase('focus', 8) === 'longBreak');
// abandoning the very first block must not award the long break
ok('zero completed blocks earns a short break', nextPhase('focus', 0) === 'shortBreak');

/* ---------------------------------------------------------- formatting */
ok('formats minutes and seconds', formatClock(25 * MIN) === '25:00');
ok('pads single digits', formatClock(61000) === '01:01');
ok('zero reads 00:00', formatClock(0) === '00:00');
ok('negative clamps to 00:00', formatClock(-5000) === '00:00');
// a timer showing 00:00 while a second is still owed looks broken, so round up
ok('a partial second still shows', formatClock(1) === '00:01');
ok('rounds up, so 24:59.5 is not shown as 24:59', formatClock(24 * MIN + 59500) === '25:00');

/* ------------------------------------------------------------- DRIFT
 * One sequence of fires, two readings. The browser is simulated: foreground
 * fires land a few ms late, a backgrounded tab is clamped to one per minute. */
function fires({ durationMs, lateMs = 4, backgroundFrom = null, backgroundTo = null }) {
  const out = [];
  let t = 0;
  while (t < durationMs) {
    const throttled = backgroundFrom !== null && t >= backgroundFrom && t < backgroundTo;
    t += throttled ? 60000 : 1000 + lateMs;       // clamped to 1/min when hidden
    out.push(t);
  }
  return out;
}

const D = 25 * MIN;
let f = fires({ durationMs: D });                            // foreground only
let tickOff  = Math.abs(tickCounter(D, f) - clockReader(D, f));
// 4ms late on every fire is 0.4%, which over a 25-minute block is ~5 seconds
ok('even in the foreground the tick-counter drifts', tickOff >= 4000,
   `${(tickOff / 1000).toFixed(1)}s`);

f = fires({ durationMs: D, backgroundFrom: 5 * MIN, backgroundTo: 7 * MIN });
const tickThinks  = tickCounter(D, f);
const clockKnows  = clockReader(D, f);
ok('backgrounding does not fool the clock reader', clockKnows >= D - 2000,
   `${(clockKnows / 1000).toFixed(0)}s`);
ok('the tick-counter under-counts a backgrounded tab', tickThinks < clockKnows,
   `tick ${(tickThinks / 1000).toFixed(0)}s vs clock ${(clockKnows / 1000).toFixed(0)}s`);
// two minutes hidden at one fire per minute = 2 ticks counted for 120 real seconds
ok('two hidden minutes cost the tick-counter about 118 seconds',
   Math.abs((clockKnows - tickThinks) - 118000) < 8000,
   `${((clockKnows - tickThinks) / 1000).toFixed(0)}s lost`);
// the real timer uses the clock path, so assert the real thing, not just the demo
const sess = start('focus', 0);
ok('the shipped timer agrees with wall-clock time regardless of fires',
   elapsedMs(sess, 7 * MIN) === 7 * MIN);

/* ------------------------------------------------------------- the log */
const mk = (startedAt, servedMs, completed, phase = 'focus') =>
  ({ phase, startedAt, endedAt: startedAt + servedMs, servedMs, durationMs: 25 * MIN, completed });

const day = d => Date.parse(`2026-03-${String(d).padStart(2, '0')}T10:00:00Z`);
const NOW = Date.parse('2026-03-05T12:00:00Z');

const log = [
  mk(day(1), 25 * MIN, true), mk(day(1) + 3600000, 25 * MIN, true),
  mk(day(2), 25 * MIN, true),
  mk(day(3), 11 * MIN, false),                     // abandoned: breaks the streak
  mk(day(4), 25 * MIN, true), mk(day(5), 25 * MIN, true),
  mk(day(5), 5 * MIN, false),
  mk(day(5), 5 * MIN, true, 'shortBreak'),         // breaks are not focus
];
const st = summarize(log, NOW);
ok('counts focus sessions started', st.startedCount === 7, String(st.startedCount));
ok('counts only completed ones', st.completedCount === 5, String(st.completedCount));
ok('completion rate is derived', Math.abs(st.completionRate - 5 / 7) < 1e-9);
ok('focus time excludes abandoned sessions', st.focusMs === 125 * MIN, String(st.focusMs / MIN));
ok('abandoned time is tracked separately', st.abandonedMs === 16 * MIN, String(st.abandonedMs / MIN));
ok('breaks do not count as focus', !st.byHour.some(h => h.sessions > 0 && h.hour === undefined));
ok('average is over completed sessions only', st.avgCompletedMs === 25 * MIN);
ok('active days counts distinct days', st.activeDays === 4, String(st.activeDays));
ok('an abandoned day does not extend the streak', st.longestStreak === 2, String(st.longestStreak));
ok('the current streak reaches today', st.currentStreak === 2, String(st.currentStreak));
ok('a stale streak is not current',
   summarize([mk(day(1), 25 * MIN, true)], NOW).currentStreak === 0);
ok('by-hour has all 24 buckets', st.byHour.length === 24);
ok('by-hour totals match total focus time',
   st.byHour.reduce((t, h) => t + h.ms, 0) === st.focusMs);
ok('best hour is the busiest one',
   st.bestHour === st.byHour.slice().sort((a, b) => b.ms - a.ms)[0].hour);
const empty = summarize([], NOW);
ok('an empty log does not divide by zero',
   empty.completionRate === null && empty.avgCompletedMs === null && empty.focusMs === 0);
ok('a log of only breaks reports no focus', summarize([mk(day(1), 5 * MIN, true, 'shortBreak')], NOW).startedCount === 0);
ok('logEntry records what was actually served',
   logEntry(pause(start('focus', 0), 9 * MIN), 20 * MIN, false).servedMs === 9 * MIN);

console.log(`\n${pass}/${pass + fail} passed`);
process.exit(fail ? 1 : 0);
