"""Parsing and comparison of semantic version strings (https://semver.org)."""

from __future__ import annotations

import re
from functools import total_ordering
from typing import Tuple, Union

# Straight from the semver.org spec's own suggested regex (FAQ section),
# with named groups. Anchored on both ends so partial matches don't slip
# through.
_VERSION_RE = re.compile(
    r"^"
    r"(?P<major>0|[1-9]\d*)\."
    r"(?P<minor>0|[1-9]\d*)\."
    r"(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<prerelease>"
    r"(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)"
    r"(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*"
    r"))?"
    r"(?:\+(?P<buildmetadata>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?"
    r"$"
)

_IDENTIFIER_RE = re.compile(r"^(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)$")

_IdentifierKey =Tuple[int, Union[int, str]]


class InvalidVersionError(ValueError):
    """Raised when a string does not conform to the semver grammar."""


def _prerelease_sort_key(identifiers: Tuple[str, ...]) -> Tuple[_IdentifierKey, ...]:
    # Per spec: numeric identifiers compare numerically and always sort
    # before alphanumeric ones, which compare as ASCII strings. The leading
    # int (0 vs 1) is what lets a bare number and a lettered string be
    # compared without a TypeError from mixing int and str.
    key = []
    for ident in identifiers:
        if ident.isdigit():
            key.append((0, int(ident)))
        else:
            key.append((1, ident))
    return tuple(key)


@total_ordering
class Version:
    """An immutable semantic version: major.minor.patch[-prerelease][+build].

    Two versions that differ only in build metadata compare as equal, per
    the spec, even though their string forms differ.
    """

    __slots__ = ("major", "minor", "patch", "prerelease", "build")

    def __init__(
        self,
        major: int,
        minor: int,
        patch: int,
        prerelease: str = "",
        build: str = "",
    ) -> None:
        object.__setattr__(self, "major", major)
        object.__setattr__(self, "minor", minor)
        object.__setattr__(self, "patch", patch)
        object.__setattr__(self, "prerelease", prerelease)
        object.__setattr__(self, "build", build)

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError(f"Version is immutable; cannot set {name!r}")

    @classmethod
    def parse(cls, text: str) -> "Version":
        match = _VERSION_RE.match(text.strip())
        if match is None:
            raise InvalidVersionError(f"not a valid semantic version: {text!r}")
        return cls(
            major=int(match.group("major")),
            minor=int(match.group("minor")),
            patch=int(match.group("patch")),
            prerelease=match.group("prerelease") or "",
            build=match.group("buildmetadata") or "",
        )

    def bump(self, part: str, prerelease_id: str = "") -> "Version":
        """Return the next version after bumping ``part``.

        ``part`` is "major", "minor", "patch" or "prerelease". Build metadata
        is always dropped, since it describes one specific build. Bumping a
        prerelease toward its own release (1.0.0-rc.1 -> major) just strips
        the prerelease instead of skipping a number, matching how npm's
        ``semver inc`` behaves.

        For "prerelease", ``prerelease_id`` names the series (e.g. "rc").
        A plain release moves to the next patch with ``<id>.0``; an existing
        prerelease in the same series has its last numeric identifier
        incremented; a different series restarts at ``<id>.0``.
        """
        if part not in ("major", "minor", "patch", "prerelease"):
            raise ValueError(f"unknown version part: {part!r}")
        if prerelease_id and part != "prerelease":
            raise ValueError("prerelease_id only applies to a prerelease bump")

        if part == "major":
            if self.is_prerelease and (self.minor, self.patch) == (0, 0):
                return Version(self.major, 0, 0)
            return Version(self.major + 1, 0, 0)
        if part == "minor":
            if self.is_prerelease and self.patch == 0:
                return Version(self.major, self.minor, 0)
            return Version(self.major, self.minor + 1, 0)
        if part == "patch":
            if self.is_prerelease:
                return Version(self.major, self.minor, self.patch)
            return Version(self.major, self.minor, self.patch + 1)

        series: Tuple[str, ...] = ()
        if prerelease_id:
            series = tuple(prerelease_id.split("."))
            for ident in series:
                if _IDENTIFIER_RE.match(ident) is None:
                    raise InvalidVersionError(
                        f"not a valid prerelease identifier: {prerelease_id!r}"
                    )

        current = self.prerelease_identifiers
        if not current:
            idents = series + ("0",)
            return Version(self.major, self.minor, self.patch + 1, ".".join(idents))
        if series and current[: len(series)] != series:
            idents = series + ("0",)
        else:
            idents = list(current)
            for i in range(len(idents) - 1, -1, -1):
                if idents[i].isdigit():
                    idents[i] = str(int(idents[i]) + 1)
                    break
            else:
                idents.append("0")
        return Version(self.major, self.minor, self.patch, ".".join(idents))

    @property
    def prerelease_identifiers(self) -> Tuple[str, ...]:
        return tuple(self.prerelease.split(".")) if self.prerelease else ()

    @property
    def is_prerelease(self) -> bool:
        return bool(self.prerelease)

    def _comparison_key(self):
        # A version with no prerelease outranks one with a prerelease, hence
        # the leading bool (False < True puts "has no prerelease" first).
        return (
            self.major,
            self.minor,
            self.patch,
            not self.is_prerelease,
            _prerelease_sort_key(self.prerelease_identifiers),
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        return self._comparison_key() == other._comparison_key()

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        # Both sides carry the "has no prerelease" flag inverted, so a
        # release always sorts after any of its own prereleases and the
        # tuple comparison falls through to identifiers only when needed.
        mine, theirs = self._comparison_key(), other._comparison_key()
        if mine[:3] != theirs[:3]:
            return mine[:3] < theirs[:3]
        if mine[3] != theirs[3]:
            # not is_prerelease: True (no prerelease) sorts after False.
            return mine[3] < theirs[3]
        return mine[4] < theirs[4]

    def __hash__(self) -> int:
        return hash(self._comparison_key())

    def __str__(self) -> str:
        text = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            text += f"-{self.prerelease}"
        if self.build:
            text += f"+{self.build}"
        return text

    def __repr__(self) -> str:
        return f"Version.parse({str(self)!r})"
