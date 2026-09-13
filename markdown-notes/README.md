# Markdown Notes

A note-taking app with a live preview, built on a Markdown renderer written
from scratch — no library — that is **safe by construction**.

**[Open the app →](https://abenezer0101.github.io/projects/markdown-notes/)**

## The actual problem

Rendering Markdown means taking text you do not control and putting it into
`innerHTML`. That is the definition of an injection hole. Most renderers
handle it by producing HTML and then sanitising it, which means shipping a
blocklist and hoping nobody finds the payload you did not think of.

This one inverts the order. User text is HTML-escaped **first**; markup is
only ever added afterwards, from a fixed set of tags the renderer emits
itself. Raw HTML in the source is never passed through, so there is no
sanitiser to outsmart — the dangerous characters stop being dangerous before
any parsing happens.

Escaping alone is not enough for one case: `[click](javascript:alert(1))` is a
perfectly well-formed link whose *scheme* is the weapon. So URLs get a second
check — control characters and whitespace are stripped (to defeat
`java&#9;script:`), then only `http`, `https`, `mailto`, anchors and relative
paths survive. Anything else renders as plain text rather than as a link.

## Two bugs this caught

Both were found by looking, not by the test suite passing.

The sample note demonstrates XSS payloads, which meant the page source
contained a literal `</script>`. The HTML parser has no concept of JavaScript
string context, so it closed the module there and truncated the file mid-
literal — the same class of confusion the renderer exists to defend against.

More seriously: the renderer was airtight, and the *app around it* was not.
The "no notes match X" empty state interpolated the search box straight into
`innerHTML`. Typing `<img src=x onerror=alert(1)>` into search fired. The
renderer's 40-odd XSS tests all passed the whole time, because the hole was
not in the renderer. Fixed by setting it as `textContent`, and there are now
end-to-end tests that type payloads into the real page and count dialogs.

## Verification

```
node test_markdown.mjs            # 63 unit tests
node e2e_markdown.js              # 19 browser tests (needs a server on :8091)
```

The unit tests assert against the tags the renderer actually **emits**, not
against the output string — searching raw HTML for `onerror=` gives false
alarms, since escaped inert text `&lt;img onerror=...&gt;` contains that
substring. The browser tests open the real page, paste live payloads, and
assert that zero dialogs fired.

## Features

Headings, bold/italic/strikethrough, inline code, fenced code blocks with
language classes, links, images, blockquotes, ordered/unordered/task lists,
tables, and horizontal rules. Notes persist to `localStorage` (corrupt
storage recovers to a seeded note rather than throwing), search filters by
body text, word and reading-time stats are derived live, and notes export
as `.md`. Responsive down to phone width, and theme-aware.
