/* Browser tests. node e2e_quiz.js  (needs a static server on :8094)
 * The point is to answer questions the way a user does and check that the
 * score the page reports matches the answers actually given. */
const { chromium } = require('playwright');
let pass = 0, fail = 0;
const ok = (n, c, x = '') => { c ? (pass++, console.log('  PASS  ' + n))
                                 : (fail++, console.log('  FAIL  ' + n + ' ' + x)); };
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 760, height: 900 } });
  const errs = [];
  p.on('pageerror', e => errs.push(e.message));
  await p.goto('http://127.0.0.1:8094/quiz-app/index.html');
  await p.waitForFunction(() => window.__quiz === undefined || true);
  await p.waitForSelector('.opt');
  ok('page loads with no script errors', errs.length === 0, errs.join(' | '));
  ok('a question is on screen', (await p.locator('.q').textContent()).startsWith('Which has'));
  ok('two options are offered', await p.locator('.opt').count() === 2);
  ok('option labels come from the data', (await p.locator('.opt').first().textContent()).trim().length > 1);
  ok('confidence is hidden until an answer is picked', await p.locator('#confbox').isHidden());

  // deliberately answer everything CORRECTLY and with full confidence:
  // a perfect confident run must score exactly 0, so any drift shows up
  let answered = 0;
  for (let i = 0; i < 12; i++) {
    // read the right answer from the page's own state, then click it
    const ans = await p.evaluate(() => window.__quiz.question.answer);
    await p.locator(`.opt[data-c="${ans}"]`).click();
    if (i === 0) ok('confidence appears after answering', await p.locator('#confbox').isVisible());
    await p.locator('.lvl[data-p="1"]').click();
    if (i === 0) ok('the correct option is marked right', await p.locator('.opt.right').count() === 1);
    answered++;
    const next = p.locator('#next');
    if (await next.count()) await next.click();
    await p.waitForTimeout(60);
    if (await p.locator('.scores').count()) break;
  }
  ok('twelve questions were asked', answered === 12, String(answered));
  ok('results screen appears', await p.locator('.scores').count() === 1);

  const s = await p.evaluate(() => window.__quiz.summary);
  ok('all twelve were scored', s.n === 12, String(s.n));
  ok('answering correctly every time reads 12/12', s.correct === 12, String(s.correct));
  ok('a perfect confident run has Brier 0', s.brier === 0, String(s.brier));
  ok('the page prints the score it computed',
     (await p.locator('.scores').textContent()).includes('12/12'));
  ok('the per-difficulty table has rows', await p.locator('table').first().locator('tbody tr').count() > 1);

  // now a deliberately overconfident WRONG run: Brier must be 1
  await p.locator('#again').click();
  await p.waitForSelector('.opt');
  for (let i = 0; i < 12; i++) {
    const ans = await p.evaluate(() => window.__quiz.question.answer);
    await p.locator(`.opt[data-c="${ans === 'a' ? 'b' : 'a'}"]`).click();
    await p.locator('.lvl[data-p="1"]').click();
    const next = p.locator('#next');
    if (await next.count()) await next.click();
    await p.waitForTimeout(60);
    if (await p.locator('.scores').count()) break;
  }
  const s2 = await p.evaluate(() => window.__quiz.summary);
  ok('answering wrong every time reads 0 correct', s2.correct === 0, String(s2.correct));
  ok('confident and wrong scores Brier 1', s2.brier === 1, String(s2.brier));
  ok('the page calls that overconfident', (await p.locator('.note').first().textContent()).includes('Overconfident'));

  ok('no script errors across the whole run', errs.length === 0, errs.join(' | '));
  await p.screenshot({ path: process.argv[2] + '/quiz_results.png' });
  await p.locator('#again').click();
  await p.waitForSelector('.opt');
  await p.screenshot({ path: process.argv[2] + '/quiz_question.png' });
  await b.close();
  console.log('\n' + pass + '/' + (pass + fail) + ' passed');
  process.exit(fail ? 1 : 0);
})();
