/* Tests for the markdown renderer.  node test_markdown.mjs
 *
 * The XSS section is the reason this file exists. A markdown renderer is an
 * injection hole by default: it takes untrusted text and puts it in innerHTML.
 * Every payload below is a real technique, and each asserts that the dangerous
 * construct does NOT survive into the output.
 */
import { render, escapeHTML, safeUrl, stats, deriveTitle } from './markdown.js';

let pass = 0, fail = 0;
const ok = (n, c, x = '') => { c ? (pass++, console.log(`  PASS  ${n}`))
                                 : (fail++, console.log(`  FAIL  ${n} ${x}`)); };

/* ------------------------------------------------------------ structure */
ok('h1', render('# Title') === '<h1>Title</h1>');
ok('h6', render('###### Deep') === '<h6>Deep</h6>');
ok('seven hashes are not a heading', !render('####### x').includes('<h7'));
ok('paragraph', render('Hello world') === '<p>Hello world</p>');
ok('paragraph joins wrapped lines', render('one\ntwo') === '<p>one two</p>');
ok('blank line splits paragraphs', render('a\n\nb') === '<p>a</p>\n<p>b</p>');
ok('bold', render('**x**') === '<p><strong>x</strong></p>');
ok('italic', render('*x*') === '<p><em>x</em></p>');
ok('bold italic', render('***x***').includes('<strong><em>x</em></strong>'));
ok('strikethrough', render('~~x~~').includes('<del>x</del>'));
ok('inline code', render('`x`') === '<p><code>x</code></p>');
ok('unordered list', render('- a\n- b') === '<ul><li>a</li><li>b</li></ul>');
ok('ordered list', render('1. a\n2. b') === '<ol><li>a</li><li>b</li></ol>');
ok('task list unchecked', render('- [ ] todo').includes('type="checkbox" disabled>'));
ok('task list checked', render('- [x] done').includes('checked'));
ok('blockquote', render('> quoted').includes('<blockquote>'));
ok('nested blockquote content is rendered', render('> **b**').includes('<strong>b</strong>'));
ok('horizontal rule', render('---') === '<hr>');
ok('hr does not eat a list', render('- a').startsWith('<ul>'));
ok('fenced code', render('```\nx\n```') === '<pre><code>x</code></pre>');
ok('fenced code keeps language', render('```js\nx\n```').includes('language-js'));
ok('table renders head and body',
   render('| a | b |\n| --- | --- |\n| 1 | 2 |').includes('<th>a</th>') &&
   render('| a | b |\n| --- | --- |\n| 1 | 2 |').includes('<td>1</td>'));
ok('empty input yields empty output', render('') === '');
ok('null input is safe', render(null) === '');

/* --------------------------------------------------------------- links */
ok('http link', render('[a](https://x.com)').includes('href="https://x.com"'));
ok('links open safely', render('[a](https://x.com)').includes('rel="noopener noreferrer"'));
ok('mailto allowed', render('[m](mailto:a@b.com)').includes('href="mailto:a@b.com"'));
ok('anchor allowed', render('[a](#section)').includes('href="#section"'));
ok('image renders', render('![alt](https://x.com/i.png)').includes('<img src="https://x.com/i.png"'));

/* ----------------------------------------------------------------- XSS
 * Each of these is a real payload. The assertion is always the same shape:
 * the executable construct must not appear in the output. */

/* Assertions inspect the tags the renderer actually EMITS. Searching the raw
 * string for "onerror=" gives false alarms, because escaped text like
 * &lt;img onerror=&quot;..&quot;&gt; contains that substring while being inert. */
const emittedTags = html => [...String(html).matchAll(/<([a-z][a-z0-9]*)\b([^>]*)>/gi)]
  .map(m => ({ tag: m[1].toLowerCase(), attrs: m[2] }));
const noScript  = html => !emittedTags(html).some(t => t.tag === 'script');
const noHandler = html => !emittedTags(html).some(t => /\son\w+\s*=/i.test(t.attrs));
const noJsUrl   = html => !emittedTags(html).some(t =>
  /(href|src)\s*=\s*["']?\s*(javascript|vbscript|data):/i.test(t.attrs));

let h = render('<script>alert(1)</script>');
ok('XSS: raw script tag is escaped', noScript(h) && h.includes('&lt;script&gt;'), h);

h = render('<img src=x onerror="alert(1)">');
ok('XSS: img onerror is escaped', noHandler(h) && h.includes('&lt;img'), h);

h = render('[click](javascript:alert(1))');
ok('XSS: javascript: link is rejected', noJsUrl(h) && !h.includes('<a '), h);

h = render('[click](JaVaScRiPt:alert(1))');
ok('XSS: javascript: is case-insensitive', noJsUrl(h) && !h.includes('<a '), h);

h = render('[click](java\tscript:alert(1))');
ok('XSS: tab-smuggled scheme rejected', noJsUrl(h) && !h.includes('<a '), h);

h = render('![x](javascript:alert(1))');
ok('XSS: javascript: image is rejected', noJsUrl(h) && !h.includes('<img'), h);

h = render('[click](data:text/html,<script>alert(1)</script>)');
ok('XSS: data: url is rejected', !h.includes('href="data:'), h);

h = render('[click](vbscript:msgbox(1))');
ok('XSS: vbscript: is rejected', !h.includes('href="vbscript:'), h);

h = render('<a href="https://x.com" onmouseover="alert(1)">x</a>');
ok('XSS: raw anchor with handler is escaped', noHandler(h) && noScript(h), h);

h = render('**bold** <svg/onload=alert(1)>');
ok('XSS: svg onload is escaped', noHandler(h), h);

h = render('`<script>alert(1)</script>`');
ok('XSS: script inside code span is escaped', noScript(h) && h.includes('&lt;script&gt;'), h);

h = render('```\n<script>alert(1)</script>\n```');
ok('XSS: script inside fence is escaped', noScript(h), h);

h = render('| <script>a</script> | b |\n| --- | --- |\n| c | d |');
ok('XSS: script in a table cell is escaped', noScript(h), h);

h = render('# <script>alert(1)</script>');
ok('XSS: script in a heading is escaped', noScript(h), h);

h = render('> <script>alert(1)</script>');
ok('XSS: script in a blockquote is escaped', noScript(h), h);

h = render('- <script>alert(1)</script>');
ok('XSS: script in a list item is escaped', noScript(h), h);

h = render('[a](https://x.com" onmouseover="alert(1))');
ok('XSS: quote-break in a url cannot add attributes', noHandler(h), h);

h = render("[a](https://x.com' onmouseover='alert(1))");
ok('XSS: single-quote break cannot add attributes', noHandler(h), h);

ok('escapeHTML covers all five characters',
   escapeHTML(`&<>"'`) === '&amp;&lt;&gt;&quot;&#39;');
ok('safeUrl rejects javascript', safeUrl('javascript:alert(1)') === '');
ok('safeUrl rejects empty', safeUrl('   ') === '');
ok('safeUrl keeps https', safeUrl('https://x.com') === 'https://x.com');
ok('safeUrl rejects a bare word', safeUrl('notaurl') === '');

/* ------------------------------------------------------------- helpers */
const s = stats('one two three\nfour');
ok('counts words', s.words === 4, String(s.words));
ok('counts lines', s.lines === 2);
ok('counts characters', s.characters === 18, String(s.characters));
ok('reading time is at least a minute', stats('a').readingMinutes === 1);
ok('empty text counts zero words', stats('').words === 0);

ok('title from heading', deriveTitle('# My Note\n\nbody') === 'My Note');
ok('title from first line when no heading', deriveTitle('Just text\nmore') === 'Just text');
ok('title skips leading blanks', deriveTitle('\n\n# Later') === 'Later');
ok('title falls back', deriveTitle('') === 'Untitled');
ok('title strips list markers', deriveTitle('- item one') === 'item one');
ok('title is truncated', deriveTitle('#' + ' ' + 'x'.repeat(200)).length <= 80);

console.log(`\n${pass}/${pass + fail} passed`);
process.exit(fail ? 1 : 0);
