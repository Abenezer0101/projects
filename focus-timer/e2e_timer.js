/* node e2e_timer.js <outdir>   (serve the repo on :8095)
 * Uses a short custom block so a full cycle runs in seconds, and checks the
 * timer against real elapsed wall-clock time rather than against itself. */
const { chromium } = require('playwright');
let pass = 0, fail = 0;
const ok = (n, c, x = '') => { c ? (pass++, console.log('  PASS  ' + n))
                                 : (fail++, console.log('  FAIL  ' + n + ' ' + x)); };
const MIN = 60000;
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 740, height: 980 } });
  const errs = []; p.on('pageerror', e => errs.push(e.message));
  await p.goto('http://127.0.0.1:8095/focus-timer/index.html');
  await p.waitForFunction(() => window.__timer);

  ok('loads with no script errors', errs.length === 0, errs.join(' | '));
  ok('opens on a 25:00 focus block', (await p.locator('#clock').textContent()) === '25:00');
  ok('starts paused', (await p.evaluate(() => window.__timer.running)) === false);
  ok('the button invites a start', (await p.locator('#toggle').textContent()) === 'Start');
  ok('no stats before any session', await p.locator('.empty-msg').count() === 1);

  await p.locator('#toggle').click();
  ok('clicking start runs the timer', await p.evaluate(() => window.__timer.running));
  ok('the button becomes Pause', (await p.locator('#toggle').textContent()) === 'Pause');

  const r0 = await p.evaluate(() => window.__timer.remainingMs);
  await p.waitForTimeout(1600);
  const r1 = await p.evaluate(() => window.__timer.remainingMs);
  ok('remaining falls with real time', r0 - r1 >= 1400 && r0 - r1 <= 2200, `${r0 - r1}ms`);
  ok('the displayed clock ticked down', (await p.locator('#clock').textContent()) !== '25:00');

  // pausing must actually stop the clock, not just relabel the button
  await p.locator('#toggle').click();
  ok('the button becomes Resume', (await p.locator('#toggle').textContent()) === 'Resume');
  const pa = await p.evaluate(() => window.__timer.remainingMs);
  await p.waitForTimeout(1200);
  const pb = await p.evaluate(() => window.__timer.remainingMs);
  ok('a paused timer does not advance', pa === pb, `${pa} -> ${pb}`);
  await p.locator('#toggle').click();
  await p.waitForTimeout(700);
  ok('resuming continues counting down',
     (await p.evaluate(() => window.__timer.remainingMs)) < pb);

  // a hidden tab must not lose time -- the whole point of the project
  const before = await p.evaluate(() => window.__timer.remainingMs);
  const wall0 = Date.now();
  await p.evaluate(() => Object.defineProperty(document, 'hidden', { value: true, configurable: true }));
  await p.evaluate(() => document.dispatchEvent(new Event('visibilitychange')));
  await new Promise(r => setTimeout(r, 2500));
  const after = await p.evaluate(() => window.__timer.remainingMs);
  const wall = Date.now() - wall0;
  ok('time spent hidden is still counted', Math.abs((before - after) - wall) < 600,
     `timer ${(before - after)}ms vs wall ${wall}ms`);

  // skip logs an unfinished block and moves to a break
  await p.locator('#skip').click();
  ok('skipping moves to a break',
     (await p.evaluate(() => window.__timer.phase)).endsWith('Break'));
  ok('the skipped block is logged', (await p.evaluate(() => window.__timer.logLength)) === 1);
  ok('a skipped block does not count as completed',
     (await p.evaluate(() => window.__timer.summary.completedCount)) === 0);
  ok('but its time is recorded as abandoned',
     (await p.evaluate(() => window.__timer.summary.abandonedMs)) > 0);

  // seed a realistic history and check the panel reports what the data says
  await p.evaluate(mIN => {
    const day = d => Date.parse(`2026-03-0${d}T09:30:00`);
    const e = (t, served, done, phase = 'focus') =>
      ({ phase, startedAt: t, endedAt: t + served, servedMs: served, durationMs: 25 * mIN, completed: done });
    window.__seed([
      e(day(1), 25 * mIN, true), e(day(1) + 3600000, 25 * mIN, true),
      e(day(2), 25 * mIN, true), e(day(3), 25 * mIN, true), e(day(3) + 7200000, 25 * mIN, true),
      e(day(4), 9 * mIN, false),
    ]);
  }, MIN);
  const s = await p.evaluate(() => window.__timer.summary);
  ok('the seeded history is summarised', s.completedCount === 5, String(s.completedCount));
  ok('completion rate is 5 of 6', Math.abs(s.completionRate - 5 / 6) < 1e-9);
  ok('focus time is 125 minutes', s.focusMs === 125 * MIN, String(s.focusMs / MIN));
  ok('the panel prints the hours it computed',
     (await p.locator('.stats').textContent()).includes('2.1h'),
     await p.locator('.stats').textContent());
  ok('blocks finished is shown', (await p.locator('.stats').textContent()).includes('5'));
  ok('the by-hour chart has 24 bars', await p.locator('.hours div').count() === 24);
  ok('at least one bar is non-empty', await p.locator('.hours div:not(.empty)').count() >= 1);
  ok('the insight names a peak hour',
     (await p.locator('#insight').textContent()).includes('most productive hour'));
  ok('no script errors across the run', errs.length === 0, errs.join(' | '));

  await p.screenshot({ path: process.argv[2] + '/timer.png' });
  await b.close();
  console.log('\n' + pass + '/' + (pass + fail) + ' passed');
  process.exit(fail ? 1 : 0);
})();
