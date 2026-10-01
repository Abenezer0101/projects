"""A regular expression engine that cannot backtrack.

Python's `re`, like Perl's and Java's and JavaScript's, is a backtracking
engine: it tries one path through the pattern and unwinds when it fails. That
buys lookahead and backreferences, and it costs exponential time on patterns
that look entirely ordinary.

This is the other construction, from Thompson 1968. The pattern becomes an NFA
and the NFA is simulated over the input while keeping the *set* of states
currently reachable. The set never exceeds the number of states in the machine,
so one pass over an n-character input through an m-state machine is O(nm) and
no input makes it worse.

Supported: literals, `.`, `*`, `+`, `?`, `|`, grouping, `[abc]`, `[^abc]`,
`[a-z]`, and backslash escapes. Not supported, by construction rather than by
omission: backreferences and lookaround, neither of which is regular.

Semantics are `re.fullmatch`, which makes the differential test unambiguous.
"""

from __future__ import annotations

from dataclasses import dataclass, field

CONCAT = "\x00"  # an explicit operator for an implicit one


@dataclass
class CharClass:
    """A literal, a dot, or a bracket set -- anything that consumes one char."""

    chars: frozenset[str] = frozenset()
    negated: bool = False
    any_char: bool = False

    def matches(self, ch: str) -> bool:
        if self.any_char:
            return True
        return (ch in self.chars) != self.negated


def _parse_class(pattern: str, i: int) -> tuple[CharClass, int]:
    """Read a [...] starting at the '['. Returns the class and the next index."""
    i += 1
    negated = False
    if i < len(pattern) and pattern[i] == "^":
        negated, i = True, i + 1
    chars: set[str] = set()
    first = True
    while i < len(pattern) and (pattern[i] != "]" or first):
        first = False
        if pattern[i] == "\\" and i + 1 < len(pattern):
            chars.add(pattern[i + 1])
            i += 2
            continue
        # a '-' is a range only between two characters, never at either end
        if (pattern[i] == "-" and chars and i + 1 < len(pattern)
                and pattern[i + 1] != "]"):
            lo, hi = sorted(chars)[-1], pattern[i + 1]
            chars.update(chr(c) for c in range(ord(lo), ord(hi) + 1))
            i += 2
            continue
        chars.add(pattern[i])
        i += 1
    if i >= len(pattern):
        raise ValueError("unterminated character class")
    return CharClass(frozenset(chars), negated), i + 1


def tokenize(pattern: str) -> list:
    """Split into tokens and insert the implicit concatenation operator."""
    out: list = []
    i = 0
    prev_is_value = False  # was the last token something concat can follow?
    while i < len(pattern):
        ch = pattern[i]
        if ch == "[":
            cls, i = _parse_class(pattern, i)
            token, is_value = cls, True
        elif ch == "\\":
            if i + 1 >= len(pattern):
                raise ValueError("trailing backslash")
            token, is_value, i = CharClass(frozenset(pattern[i + 1])), True, i + 2
        elif ch == ".":
            token, is_value, i = CharClass(any_char=True), True, i + 1
        elif ch in "*+?":
            # A quantifier directly after a quantifier is `re`'s lazy (`a+?`)
            # or possessive (`a*+`) form, and neither belongs here. Lazy is
            # harmless -- it changes which span is captured, never whether a
            # full match exists -- but possessive is not a regular language at
            # all: re.fullmatch('a*+a', 'aa') is None even though 'aa' is in
            # a*a. Parsing them as two stacked operators would silently mean
            # something else, so they are refused by name.
            if out and isinstance(out[-1], str) and out[-1] in "*+?":
                raise ValueError(
                    f"stacked quantifier {out[-1]}{ch!s} at position {i}: "
                    "lazy and possessive quantifiers are not supported"
                )
            token, is_value, i = ch, True, i + 1
        elif ch == "|":
            token, is_value, i = ch, False, i + 1
        elif ch == "(":
            token, is_value, i = ch, False, i + 1
        elif ch == ")":
            token, is_value, i = ch, True, i + 1
        else:
            token, is_value, i = CharClass(frozenset(ch)), True, i + 1

        starts_value = isinstance(token, CharClass) or token == "("
        if prev_is_value and starts_value:
            out.append(CONCAT)
        out.append(token)
        prev_is_value = is_value
    return out


PRECEDENCE = {"|": 1, CONCAT: 2, "*": 3, "+": 3, "?": 3}


def to_postfix(tokens: list) -> list:
    """Shunting-yard. Postfix removes the parentheses and fixes the order."""
    out: list = []
    stack: list[str] = []
    for token in tokens:
        if isinstance(token, CharClass):
            out.append(token)
        elif token == "(":
            stack.append(token)
        elif token == ")":
            while stack and stack[-1] != "(":
                out.append(stack.pop())
            if not stack:
                raise ValueError("unbalanced )")
            stack.pop()
        else:
            while (stack and stack[-1] != "("
                   and PRECEDENCE[stack[-1]] >= PRECEDENCE[token]):
                out.append(stack.pop())
            stack.append(token)
    while stack:
        op = stack.pop()
        if op == "(":
            raise ValueError("unbalanced (")
        out.append(op)
    return out


@dataclass
class State:
    """Either consumes one character, or branches to up to two states for free."""

    cls: CharClass | None = None
    out: "State | None" = None
    out1: "State | None" = None
    is_match: bool = False
    _id: int = field(default_factory=lambda: State._next())
    _counter = 0

    @classmethod
    def _next(cls) -> int:
        State._counter += 1
        return State._counter


@dataclass
class Fragment:
    start: State
    dangling: list  # (state, attribute name) pairs still needing a destination


def _patch(dangling: list, target: State) -> None:
    for state, attr in dangling:
        setattr(state, attr, target)


def _epsilon() -> Fragment:
    """A fragment that consumes nothing. `a|` and `()` are legal in `re` and
    mean 'or nothing', so an absent operand is empty rather than an error."""
    s = State()
    return Fragment(s, [(s, "out")])


def compile_postfix(postfix: list) -> State:
    stack: list[Fragment] = []

    def pop() -> Fragment:
        return stack.pop() if stack else _epsilon()

    for token in postfix:
        if isinstance(token, CharClass):
            s = State(cls=token)
            stack.append(Fragment(s, [(s, "out")]))
        elif token == CONCAT:
            b, a = pop(), pop()
            _patch(a.dangling, b.start)
            stack.append(Fragment(a.start, b.dangling))
        elif token == "|":
            b, a = pop(), pop()
            s = State(out=a.start, out1=b.start)
            stack.append(Fragment(s, a.dangling + b.dangling))
        elif token == "?":
            a = pop()
            s = State(out=a.start)
            stack.append(Fragment(s, a.dangling + [(s, "out1")]))
        elif token == "*":
            a = pop()
            s = State(out=a.start)
            _patch(a.dangling, s)
            stack.append(Fragment(s, [(s, "out1")]))
        elif token == "+":
            a = pop()
            s = State(out=a.start)
            _patch(a.dangling, s)
            stack.append(Fragment(a.start, [(s, "out1")]))
        else:
            raise ValueError(f"unknown operator {token!r}")
    if not stack:
        # the empty pattern matches only the empty string
        s = State(is_match=True)
        return s
    if len(stack) != 1:
        raise ValueError("malformed pattern")
    frag = stack.pop()
    accept = State(is_match=True)
    _patch(frag.dangling, accept)
    return frag.start


def _add(state: State | None, into: list, seen: set) -> None:
    """Follow free (epsilon) branches, marking states so a loop terminates."""
    if state is None or state._id in seen:
        return
    seen.add(state._id)
    if state.cls is None and not state.is_match:
        _add(state.out, into, seen)
        _add(state.out1, into, seen)
        return
    into.append(state)


class Regex:
    def __init__(self, pattern: str):
        self.pattern = pattern
        self.start = compile_postfix(to_postfix(tokenize(pattern)))

    def fullmatch(self, text: str) -> bool:
        """One pass, carrying the set of reachable states. Never backtracks."""
        current: list[State] = []
        _add(self.start, current, set())
        for ch in text:
            nxt: list[State] = []
            seen: set = set()
            for state in current:
                if state.cls is not None and state.cls.matches(ch):
                    _add(state.out, nxt, seen)
            current = nxt
            if not current:
                return False
        return any(s.is_match for s in current)


def fullmatch(pattern: str, text: str) -> bool:
    return Regex(pattern).fullmatch(text)
