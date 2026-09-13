/* A small Markdown renderer that is safe by construction.
 *
 * The rule that makes it safe: user text is HTML-escaped FIRST, and markup is
 * only ever added afterwards from a fixed set of tags this file emits itself.
 * Raw HTML in the source is never passed through, so there is no sanitiser to
 * outsmart -- the dangerous characters stop being dangerous before any parsing
 * happens.
 *
 * URLs get a second check: only http, https and mailto survive, because
 * [click](javascript:...) is a link that escaping alone cannot defuse.
 */

const ESCAPES = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
export const escapeHTML = s => String(s).replace(/[&<>"']/g, c => ESCAPES[c]);

const SAFE_SCHEME = /^(https?:|mailto:|#|\/|\.\/|\.\.\/)/i;
const SENTINEL = '\uE000';        // private-use area: cannot appear in escaped text

/** Allow only schemes that cannot execute. Everything else becomes inert. */
export function safeUrl(raw) {
  const url = String(raw || '').trim();
  // strip control characters and whitespace used to smuggle "java\nscript:"
  const flat = url.replace(/[\u0000-\u001F\u007F\s]/g, '');
  if (!flat) return '';
  const hasScheme = /^[a-z][a-z0-9+.-]*:/i.test(flat);
  if (hasScheme) return SAFE_SCHEME.test(flat) ? flat : '';
  if (SAFE_SCHEME.test(flat)) return flat;
  return flat.includes('.') ? flat : '';      // bare domain, else reject
}

/* --------------------------------------------------------------- inline */

function inline(text) {
  let s = escapeHTML(text);

  // code spans first: their contents must not be re-formatted
  const spans = [];
  s = s.replace(/`([^`]+)`/g, (_, code) => {
    spans.push(code);
    return SENTINEL + (spans.length - 1) + SENTINEL;
  });

  // images before links (both begin with a bracket)
  s = s.replace(/!\[([^\]]*)\]\(([^)\s]+)(?:\s+"([^"]*)")?\)/g, (m, alt, url, title) => {
    const safe = safeUrl(url);
    if (!safe) return m;
    const t = title ? ' title="' + title + '"' : '';
    return '<img src="' + safe + '" alt="' + alt + '"' + t + ' loading="lazy">';
  });
  s = s.replace(/\[([^\]]+)\]\(([^)\s]+)(?:\s+"([^"]*)")?\)/g, (m, label, url, title) => {
    const safe = safeUrl(url);
    if (!safe) return m;                       // unsafe link stays plain text
    const t = title ? ' title="' + title + '"' : '';
    return '<a href="' + safe + '"' + t + ' rel="noopener noreferrer" target="_blank">' + label + '</a>';
  });

  s = s.replace(/\*\*\*([^*]+)\*\*\*/g, '<strong><em>$1</em></strong>');
  s = s.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  s = s.replace(/(^|[^*])\*([^*\n]+)\*/g, '$1<em>$2</em>');
  s = s.replace(/__([^_]+)__/g, '<strong>$1</strong>');
  s = s.replace(/(^|[^_])_([^_\n]+)_/g, '$1<em>$2</em>');
  s = s.replace(/~~([^~]+)~~/g, '<del>$1</del>');

  const back = new RegExp(SENTINEL + '(\\d+)' + SENTINEL, 'g');
  // spans were captured AFTER escapeHTML ran, so they are already escaped --
  // escaping again would show the user &lt;script&gt; instead of <script>
  s = s.replace(back, (_, i) => '<code>' + spans[Number(i)] + '</code>');
  return s;
}

/* --------------------------------------------------------------- blocks */

export function render(markdown) {
  const lines = String(markdown ?? '').replace(/\r\n?/g, '\n').split('\n');
  const out = [];
  const para = [];
  let i = 0;

  const flush = () => {
    if (para.length) { out.push('<p>' + inline(para.join(' ')) + '</p>'); para.length = 0; }
  };

  while (i < lines.length) {
    const line = lines[i];

    const fence = line.match(/^```\s*([\w+-]*)\s*$/);
    if (fence) {
      flush();
      const body = [];
      i++;
      while (i < lines.length && !/^```\s*$/.test(lines[i])) body.push(lines[i++]);
      i++;                                     // closing fence
      const cls = fence[1] ? ' class="language-' + escapeHTML(fence[1]) + '"' : '';
      out.push('<pre><code' + cls + '>' + escapeHTML(body.join('\n')) + '</code></pre>');
      continue;
    }

    if (/^\s*$/.test(line)) { flush(); i++; continue; }

    const h = line.match(/^(#{1,6})\s+(.*)$/);
    if (h) {
      flush();
      out.push('<h' + h[1].length + '>' + inline(h[2].trim()) + '</h' + h[1].length + '>');
      i++; continue;
    }

    if (/^\s*([-*_])(\s*\1){2,}\s*$/.test(line)) { flush(); out.push('<hr>'); i++; continue; }

    if (/^>\s?/.test(line)) {
      flush();
      const body = [];
      while (i < lines.length && /^>\s?/.test(lines[i])) body.push(lines[i++].replace(/^>\s?/, ''));
      out.push('<blockquote>' + render(body.join('\n')) + '</blockquote>');
      continue;
    }

    if (/^\s*([-*+]|\d+\.)\s+/.test(line)) {
      flush();
      const ordered = /^\s*\d+\./.test(line);
      const items = [];
      while (i < lines.length && /^\s*([-*+]|\d+\.)\s+/.test(lines[i])) {
        const text = lines[i].replace(/^\s*([-*+]|\d+\.)\s+/, '');
        const task = text.match(/^\[([ xX])\]\s+(.*)$/);
        if (task) {
          const done = task[1].toLowerCase() === 'x';
          items.push('<li class="task"><input type="checkbox" disabled' +
                     (done ? ' checked' : '') + '> ' + inline(task[2]) + '</li>');
        } else {
          items.push('<li>' + inline(text) + '</li>');
        }
        i++;
      }
      out.push(ordered ? '<ol>' + items.join('') + '</ol>' : '<ul>' + items.join('') + '</ul>');
      continue;
    }

    if (/^\s*\|.*\|\s*$/.test(line) && /^\s*\|[\s:|-]+\|\s*$/.test(lines[i + 1] || '')) {
      flush();
      const cells = row => row.trim().replace(/^\||\|$/g, '').split('|').map(c => c.trim());
      const head = cells(line);
      i += 2;
      const body = [];
      while (i < lines.length && /^\s*\|.*\|\s*$/.test(lines[i])) body.push(cells(lines[i++]));
      out.push('<table><thead><tr>' + head.map(c => '<th>' + inline(c) + '</th>').join('') +
               '</tr></thead><tbody>' +
               body.map(r => '<tr>' + r.map(c => '<td>' + inline(c) + '</td>').join('') + '</tr>').join('') +
               '</tbody></table>');
      continue;
    }

    para.push(line.trim());
    i++;
  }
  flush();
  return out.join('\n');
}

/* -------------------------------------------------------------- helpers */

export function stats(markdown) {
  const text = String(markdown ?? '');
  const words = text.trim() ? text.trim().split(/\s+/).length : 0;
  return {
    characters: text.length,
    words,
    lines: text ? text.split('\n').length : 0,
    readingMinutes: Math.max(1, Math.round(words / 200)),
  };
}

/** First heading, else first non-empty line, else a placeholder. */
export function deriveTitle(markdown) {
  for (const line of String(markdown ?? '').split('\n')) {
    const h = line.match(/^#{1,6}\s+(.*)$/);
    if (h && h[1].trim()) return h[1].trim().slice(0, 80);
    if (line.trim()) return (line.trim().replace(/^[>*\-+\s]+/, '').slice(0, 80)) || 'Untitled';
  }
  return 'Untitled';
}
