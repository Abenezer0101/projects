/* A focus timer, and the reason it is not a for-loop over seconds.
 *
 * The obvious implementation counts ticks: setInterval(() => left -= 1000, 1000).
 * It is wrong, and wrong quietly. setInterval does not promise 1000ms -- it
 * promises "not sooner than", browsers clamp background tabs to about one fire
 * per minute, and a suspended tab may not fire at all. A tick-counter treats
 * every fire as exactly one second no matter how long it really was, so a timer
 * backgrounded for two minutes comes back believing two SECONDS passed.
 *
 * Everything here derives time from wall-clock timestamps instead. `now` is a
 * parameter rather than a call to Date.now(), which is what makes the whole
 * state machine testable without waiting in real time.
 */

export const PHASES = {
  focus:      { label: 'Focus',       ms: 25 * 60 * 1000 },
  shortBreak: { label: 'Short break', ms:  5 * 60 * 1000 },
  longBreak:  { label: 'Long break',  ms: 15 * 60 * 1000 },
};

export const LONG_BREAK_EVERY = 4;

/** A session records WHEN it started, never how much is left. */
export function start(phase, now, durationMs = null) {
  if (!PHASES[phase]) throw new Error(`unknown phase: ${phase}`);
  return {
    phase,
    durationMs: durationMs ?? PHASES[phase].ms,
    startedAt: now,
    bankedMs: 0,        // time already served across earlier run stretches
    resumedAt: now,     // when the current stretch began; null while paused
  };
}

export function elapsedMs(s, now) {
  const live = s.resumedAt === null ? 0 : Math.max(0, now - s.resumedAt);
  return s.bankedMs + live;
}

export function remainingMs(s, now) {
  return Math.max(0, s.durationMs - elapsedMs(s, now));
}

export const isRunning  = s => s.resumedAt !== null;
export const isComplete = (s, now) => remainingMs(s, now) === 0;

export function pause(s, now) {
  if (!isRunning(s)) return s;
  return { ...s, bankedMs: elapsedMs(s, now), resumedAt: null };
}

export function resume(s, now) {
  if (isRunning(s)) return s;
  return { ...s, resumedAt: now };
}

/** Progress through the cycle: every 4th focus block earns the long break. */
export function nextPhase(phase, completedFocus) {
  if (phase !== 'focus') return 'focus';
  // completedFocus is 0 when the very first block is abandoned, and 0 % 4 is 0 --
  // without the guard, giving up immediately earns a 15-minute long break
  return completedFocus > 0 && completedFocus % LONG_BREAK_EVERY === 0 ? 'longBreak' : 'shortBreak';
}

export function formatClock(ms) {
  const total = Math.max(0, Math.ceil(ms / 1000));
  const m = Math.floor(total / 60), s = total % 60;
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

/* ------------------------------------------------------ the comparison
 * Both of these are driven by the SAME sequence of timer fires. The only
 * difference is what they believe a fire means. This is what the tests and
 * the README measure. */

/** The naive version: every fire is assumed to be exactly one interval. */
export function tickCounter(durationMs, fires, intervalMs = 1000) {
  let left = durationMs;
  for (let i = 0; i < fires.length && left > 0; i++) left -= intervalMs;
  return durationMs - left;          // what it THINKS has elapsed
}

/** The clock version: a fire is only a prompt to re-read the clock. */
export function clockReader(durationMs, fires, startedAt = 0) {
  if (!fires.length) return 0;
  const now = fires[fires.length - 1];
  return Math.min(durationMs, Math.max(0, now - startedAt));
}

/* ------------------------------------------------------------- session log */

/** A finished-or-abandoned stretch of work, as recorded when it ends. */
export const logEntry = (s, now, completed) => ({
  phase: s.phase,
  startedAt: s.startedAt,
  endedAt: now,
  servedMs: elapsedMs(s, now),
  durationMs: s.durationMs,
  completed,
});

const dayKey = ts => new Date(ts).toISOString().slice(0, 10);

/** Stats are computed from the log. Nothing here is stored pre-computed. */
export function summarize(log, now = Date.now()) {
  const focus = log.filter(e => e.phase === 'focus');
  const done  = focus.filter(e => e.completed);

  const byHour = Array.from({ length: 24 }, (_, h) => ({ hour: h, ms: 0, sessions: 0 }));
  for (const e of done) {
    const h = new Date(e.startedAt).getHours();
    byHour[h].ms += e.servedMs;
    byHour[h].sessions++;
  }

  const days = [...new Set(done.map(e => dayKey(e.startedAt)))].sort();
  let longest = 0, run = 0, prev = null;
  for (const d of days) {
    const gap = prev === null ? null : (Date.parse(d) - Date.parse(prev)) / 86400000;
    run = gap === 1 ? run + 1 : 1;
    longest = Math.max(longest, run);
    prev = d;
  }
  // a streak is only current if it reaches today or yesterday
  const today = dayKey(now);
  const yesterday = dayKey(now - 86400000);
  const current = days.length && (days.at(-1) === today || days.at(-1) === yesterday) ? run : 0;

  const focusMs = done.reduce((t, e) => t + e.servedMs, 0);
  const best = byHour.filter(h => h.sessions > 0).sort((a, b) => b.ms - a.ms)[0] || null;

  return {
    startedCount: focus.length,
    completedCount: done.length,
    completionRate: focus.length ? done.length / focus.length : null,
    focusMs,
    abandonedMs: focus.filter(e => !e.completed).reduce((t, e) => t + e.servedMs, 0),
    avgCompletedMs: done.length ? focusMs / done.length : null,
    byHour,
    bestHour: best ? best.hour : null,
    activeDays: days.length,
    currentStreak: current,
    longestStreak: longest,
  };
}
