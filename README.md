# semverkit

A small library for parsing and comparing [semantic version](https://semver.org)
strings correctly.

## Why

"Just compare the strings" or "split on dots and compare ints" both fall
apart the moment prerelease tags show up. `1.0.0-alpha` needs to sort before
`1.0.0`, but `1.0.0-alpha.10` needs to sort after `1.0.0-alpha.9` (numeric,
not lexical), and `1.0.0-alpha.beta` needs to sort after `1.0.0-alpha.1`
(alphanumeric identifiers outrank numeric ones at the same position). Build
metadata (the `+...` suffix) is part of the string but must be ignored for
comparison and equality entirely. Sorting a list of git tags or PyPI
releases with `sorted()` on the raw strings gets all of this wrong.

`semverkit` implements the precedence rules from section 11 of the spec
directly, so `Version` objects sort the way the spec says they should.

## Install

Not published anywhere yet. For now, drop the `src/semverkit` package
alongside your code, or install it from a local checkout:

```
pip install -e /path/to/semverkit
```

## Usage

```python
from semverkit import Version, InvalidVersionError

v = Version.parse("2.4.1-rc.1+build.87")
v.major, v.minor, v.patch   # (2, 4, 1)
v.prerelease                # "rc.1"
v.build                     # "build.87"
v.is_prerelease             # True
str(v)                      # "2.4.1-rc.1+build.87"

# Sorting a list of release tags the way semver actually orders them.
tags = ["1.0.0", "1.0.0-rc.1", "1.0.0-alpha", "0.9.9", "1.0.0-alpha.10"]
sorted(Version.parse(t) for t in tags)
# [0.9.9, 1.0.0-alpha, 1.0.0-alpha.10, 1.0.0-rc.1, 1.0.0]

# Build metadata is ignored for equality and ordering.
Version.parse("1.0.0+linux") == Version.parse("1.0.0+darwin")  # True

try:
    Version.parse("1.02.3")  # leading zero in a numeric field
except InvalidVersionError as e:
    print(e)
```

`Version` instances are immutable and hashable, so they work fine as dict
keys or in sets.

### Range matching

```python
from semverkit import Range, satisfies

r = Range.parse("^1.2.3")
r.matches("1.4.0")       # True
r.matches("2.0.0")       # False

satisfies("1.9.9", ">=1.2.3 <2.0.0")   # True
satisfies("2.0.0", "1.2.3 || 2.0.0")   # True
```

Comparators (`=`, `>`, `>=`, `<`, `<=`), caret (`^1.2.3`), and tilde
(`~1.2.3`) are all supported. Space-separated comparators are ANDed
together; `||` separates alternatives that are ORed. There must be no space
between an operator and its version, and every version in a range must be a
full `major.minor.patch` -- partial forms like `~1.2` or x-ranges (`1.x`)
and hyphen ranges (`1.2.3 - 2.3.4`) aren't supported.

Prerelease versions follow the same rule as npm's semver package: a
prerelease only satisfies a range if some comparator in the matching set is
pinned to that exact major.minor.patch and is itself a prerelease. So
`^1.2.3` never matches `1.3.0-alpha`, but `^1.2.3-alpha.1` matches
`1.2.3-alpha.5`.

## What this is not

This library parses, orders, and range-matches version strings. It does not
implement version bumping. That may show up later if the need arises.

## Testing

The test suite is table-driven: each of the awkward precedence cases from
the spec (and a few that trip up naive implementations) lives as a row in a
list, not a one-off assertion. Run it with:

```
python -m unittest discover -s tests
```

## License

MIT, see [LICENSE](LICENSE).
