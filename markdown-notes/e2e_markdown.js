const { chromium } = require('playwright');
let pass=0, fail=0;
const ok=(n,c,x='')=>{c?(pass++,console.log('  PASS  '+n)):(fail++,console.log('  FAIL  '+n+' '+x));};
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage();
  let pwned = 0, errs = [];
  p.on('dialog', async d => { pwned++; await d.dismiss(); });
  p.on('pageerror', e => errs.push(e.message));
  await p.goto('http://127.0.0.1:8091/markdown-notes/index.html');
  await p.waitForFunction(() => window.__notes, null, { timeout: 5000 });
  ok('module executed without errors', errs.length === 0, errs.join(' | '));
  let s = await p.evaluate(() => window.__notes);
  ok('seeds one note', s.count === 1, String(s.count));
  ok('preview renders headings', s.html.includes('<h1>Welcome</h1>'), s.html.slice(0,80));
  ok('sample table renders', s.html.includes('<table>'));
  ok('task checkboxes render', s.html.includes('type="checkbox"'));
  ok('sample XSS shown as text, not tags', s.html.includes('&lt;script&gt;'));

  // paste live payloads into the editor
  const payload = '# Attack\n\n<script>alert(1)</script>\n\n<img src=x onerror=alert(1)>\n\n[click](javascript:alert(1))\n\n<svg/onload=alert(1)>';
  await p.fill('#text', payload);
  await p.waitForTimeout(300);
  s = await p.evaluate(() => window.__notes);
  ok('XSS payloads do not execute', pwned === 0, 'dialogs: ' + pwned);
  ok('no script element in DOM', await p.locator('#preview script').count() === 0);
  ok('no img element from payload', await p.locator('#preview img').count() === 0);
  ok('javascript: link not linkified', await p.locator('#preview a[href^="javascript"]').count() === 0);
  ok('title derives from payload heading', (await p.locator('.note .t').first().textContent()).trim() === 'Attack');

  // stats are derived, not typed
  await p.fill('#text', 'one two three');
  await p.waitForTimeout(250);
  ok('stats update live', (await p.locator('#stats').textContent()).includes('3 words'));

  // new note + persistence
  await p.click('#new');
  await p.waitForTimeout(150);
  ok('new note added', (await p.evaluate(() => window.__notes)).count === 2);
  await p.reload();
  await p.waitForFunction(() => window.__notes, null, { timeout: 5000 });
  ok('notes survive reload', (await p.evaluate(() => window.__notes)).count === 2);

  // search
  await p.fill('#search', 'zzzznomatch');
  await p.waitForTimeout(150);
  ok('search with no match shows empty state', await p.locator('#list .empty').count() === 1);
  // the empty state echoes the search term back into the page
  await p.fill('#search', '<img src=x onerror=alert(1)>');
  await p.waitForTimeout(200);
  ok('search term in empty state does not inject', await p.locator('#list img').count() === 0);
  ok('search term is shown as text', (await p.locator('#list .empty').textContent()).includes('<img src=x'));
  await p.fill('#search', '');
  await p.waitForTimeout(150);
  ok('clearing search restores list', await p.locator('#list .note').count() === 2);

  // corrupt storage must not brick the app
  await p.evaluate(() => localStorage.setItem('markdown-notes', '{not json'));
  await p.reload();
  await p.waitForFunction(() => window.__notes, null, { timeout: 5000 });
  ok('corrupt storage recovers to a seeded note', (await p.evaluate(() => window.__notes)).count === 1);

  await p.screenshot({ path: '/tmp/claude-0/-home-user-Tableau-Dashboard-Project/c922115c-62b5-5afe-a3f5-a2479058bc02/scratchpad/md.png', fullPage: false });
  await b.close();
  console.log('\n' + pass + '/' + (pass+fail) + ' passed');
  process.exit(fail ? 1 : 0);
})();
