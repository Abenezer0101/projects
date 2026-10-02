"""A CSV parser that handles the cases `line.split(",")` gets wrong.

CSV looks like a format you can parse with one method call, which is why it is
parsed wrong so often. The actual grammar (RFC 4180, plus what real producers
emit) has four features that defeat splitting:

  * a comma inside quotes is data, not a delimiter
  * a newline inside quotes is data, not a row boundary
  * "" inside a quoted field is one literal quote
  * line endings are CRLF, LF, or inconsistent within one file

This is a character-level state machine, so embedded newlines fall out of it
rather than needing a special case. Semantics follow `csv.reader` with its
default dialect, which is what `difftest.py` holds it to.
"""

from __future__ import annotations

from enum import Enum, auto

BOM = "﻿"


class _State(Enum):
    FIELD_START = auto()
    UNQUOTED = auto()
    QUOTED = auto()
    QUOTE_IN_QUOTED = auto()  # just saw " inside a quoted field: escape or close?


def parse(text: str, *, delimiter: str = ",", quotechar: str = '"',
          strip_bom: bool = True) -> list[list[str]]:
    """Parse CSV text into rows of fields.

    `strip_bom` removes a leading byte-order mark. The `csv` module does not do
    this -- it expects the file to have been opened with encoding='utf-8-sig'
    -- so a BOM reaches it as part of the first field name and silently breaks
    every lookup of that column. Handling it here is a deliberate divergence,
    documented in the README and pinned by a test.
    """
    if strip_bom and text.startswith(BOM):
        text = text[len(BOM):]

    rows: list[list[str]] = []
    row: list[str] = []
    field: list[str] = []
    state = _State.FIELD_START

    def end_field() -> None:
        row.append("".join(field))
        field.clear()

    def end_row() -> None:
        # A blank line is a row with NO fields, not a row with one empty
        # field. The csv module yields [] for it and [''] for a line holding
        # a single empty quoted field, and code that checks `if not row:` to
        # skip blanks depends on that distinction.
        if state is _State.FIELD_START and not row and not field:
            rows.append([])
            return
        end_field()
        rows.append(row.copy())
        row.clear()

    i, n = 0, len(text)
    while i < n:
        ch = text[i]

        if state is _State.FIELD_START:
            if ch == quotechar:
                state = _State.QUOTED
            elif ch == delimiter:
                end_field()
            elif ch == "\r":
                # a bare CR, or the CR of a CRLF: either way the row ends here
                end_row()
                if i + 1 < n and text[i + 1] == "\n":
                    i += 1
            elif ch == "\n":
                end_row()
            else:
                field.append(ch)
                state = _State.UNQUOTED

        elif state is _State.UNQUOTED:
            if ch == delimiter:
                end_field()
                state = _State.FIELD_START
            elif ch == "\r":
                end_row()
                if i + 1 < n and text[i + 1] == "\n":
                    i += 1
                state = _State.FIELD_START
            elif ch == "\n":
                end_row()
                state = _State.FIELD_START
            else:
                # A quote in the middle of an unquoted field is literal. The
                # csv module does the same; nothing in the grammar makes a
                # quote special once the field has started unquoted.
                field.append(ch)

        elif state is _State.QUOTED:
            if ch == quotechar:
                state = _State.QUOTE_IN_QUOTED
            else:
                # newlines included: inside quotes they are data
                field.append(ch)

        elif state is _State.QUOTE_IN_QUOTED:
            if ch == quotechar:
                field.append(quotechar)  # "" is one literal quote
                state = _State.QUOTED
            elif ch == delimiter:
                end_field()
                state = _State.FIELD_START
            elif ch == "\r":
                end_row()
                if i + 1 < n and text[i + 1] == "\n":
                    i += 1
                state = _State.FIELD_START
            elif ch == "\n":
                end_row()
                state = _State.FIELD_START
            else:
                # Text after a closing quote, as in "ab"c -- malformed, and
                # the csv module appends it rather than raising. Matching that
                # is the point of a differential test: the reference defines
                # the behaviour, including where it is strange.
                field.append(ch)
                state = _State.UNQUOTED

        i += 1

    # A file ending without a newline still has a final row; one ending WITH a
    # newline does not have a trailing empty row.
    if state is not _State.FIELD_START or row or field:
        end_row()
    return rows


def naive(text: str) -> list[list[str]]:
    """What people actually write. Kept here so the comparison is concrete."""
    return [line.split(",") for line in text.splitlines()]
