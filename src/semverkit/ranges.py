"""Constraint/range matching against Version objects (npm-style ranges).

Supports the comparator forms most projects actually write: exact versions,
`>`, `>=`, `<`, `<=`, caret (`^1.2.3`), and tilde (`~1.2.3`). Comparators
separated by whitespace are ANDed together ("1.2.3 <=2.0.0" means both must
hold); comparator sets separated by `||` are ORed. There must be no space
between an operator and its version (`>= 1.2.3` is not accepted) and each
version must be a full major.minor.patch, matching what Version.parse
requires -- there is no support for partial versions like `~1.2` or `1.x`.
Hyphen ranges ("1.2.3 - 2.3.4") aren't supported either.
"""

from __future__ import annotations

import re
from typing import Tuple, Union

from .version import Version

_COMPARATOR_RE = re.compile(r"^(?P<op>\^|~|>=|<=|>|<|=)?(?P<version>.+)$")

_OPS = {
    "=": lambda v, bound: v == bound,
    ">": lambda v, bound: v > bound,
    ">=": lambda v, bound: v >= bound,
    "<": lambda v, bound: v < bound,
    "<=": lambda v, bound: v <= bound,
}


class InvalidRangeError(ValueError):
    """Raised when a range string is empty or has an empty comparator set."""


class Comparator:
    """A single operator/version pair, e.g. the `>=1.2.3` half of a range."""

    __slots__ = ("op", "version")

    def __init__(self, op: str, version: Version) -> None:
        self.op = op
        self.version = version

    def matches(self, version: Version) -> bool:
        return _OPS[self.op](version, self.version)

    def __repr__(self) -> str:
        return f"Comparator({self.op!r}, {str(self.version)!r})"


def _expand_caret(version_text: str) -> Tuple[Comparator, Comparator]:
    v = Version.parse(version_text)
    # Caret allows changes that don't touch the leftmost non-zero component,
    # since that's what "won't break me" means once you're inside 0.x.
    if v.major > 0:
        high = Version(v.major + 1, 0, 0)
    elif v.minor > 0:
        high = Version(0, v.minor + 1, 0)
    else:
        high = Version(0, 0, v.patch + 1)
    return (Comparator(">=", v), Comparator("<", high))


def _expand_tilde(version_text: str) -> Tuple[Comparator, Comparator]:
    v = Version.parse(version_text)
    high = Version(v.major, v.minor + 1, 0)
    return (Comparator(">=", v), Comparator("<", high))


def _parse_comparator_group(token: str) -> Tuple[Comparator, ...]:
    match = _COMPARATOR_RE.match(token)
    assert match is not None  # token is non-empty, .+ always matches something
    op = match.group("op") or "="
    version_text = match.group("version")
    if op == "^":
        return _expand_caret(version_text)
    if op == "~":
        return _expand_tilde(version_text)
    return (Comparator(op, Version.parse(version_text)),)


def _same_triple(a: Version, b: Version) -> bool:
    return (a.major, a.minor, a.patch) == (b.major, b.minor, b.patch)


def _set_matches(comparators: Tuple[Comparator, ...], version: Version) -> bool:
    if version.is_prerelease:
        # A prerelease only satisfies a set if the set itself is pinned to
        # that same major.minor.patch via a comparator that also carries a
        # prerelease tag -- otherwise "^1.2.3" would let 2.0.0-alpha sneak
        # in past the "<2.0.0" bound, which is not what anyone means by it.
        pinned = any(
            c.version.is_prerelease and _same_triple(c.version, version)
            for c in comparators
        )
        if not pinned:
            return False
    return all(c.matches(version) for c in comparators)


class Range:
    """A parsed constraint expression that Version objects can be tested against."""

    __slots__ = ("_text", "_sets")

    def __init__(self, text: str, sets: Tuple[Tuple[Comparator, ...], ...]) -> None:
        self._text = text
        self._sets = sets

    @classmethod
    def parse(cls, text: str) -> "Range":
        text = text.strip()
        if not text:
            raise InvalidRangeError("range string is empty")
        sets = []
        for or_part in text.split("||"):
            tokens = or_part.split()
            if not tokens:
                raise InvalidRangeError(
                    f"empty comparator set in range: {text!r}"
                )
            comparators: list = []
            for token in tokens:
                comparators.extend(_parse_comparator_group(token))
            sets.append(tuple(comparators))
        return cls(text, tuple(sets))

    def matches(self, version: Union[str, Version]) -> bool:
        if isinstance(version, str):
            version = Version.parse(version)
        return any(_set_matches(s, version) for s in self._sets)

    def __contains__(self, version: Union[str, Version]) -> bool:
        return self.matches(version)

    def __str__(self) -> str:
        return self._text

    def __repr__(self) -> str:
        return f"Range.parse({self._text!r})"


def satisfies(version: Union[str, Version], range_text: str) -> bool:
    """Return whether `version` satisfies the range described by `range_text`."""
    return Range.parse(range_text).matches(version)


__all__ = ["Range", "Comparator", "InvalidRangeError", "satisfies"]
