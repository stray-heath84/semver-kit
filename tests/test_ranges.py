import unittest

from semverkit import InvalidRangeError, Range, Version, satisfies

# (range, [versions that satisfy it], [versions that don't])
RANGE_CASES = [
    (
        "^1.2.3",
        ["1.2.3", "1.2.4", "1.9.9", "1.2.3+build"],
        ["1.2.2", "2.0.0", "0.9.9"],
    ),
    (
        # inside 0.x, caret only tolerates patch bumps once minor is nonzero.
        "^0.2.3",
        ["0.2.3", "0.2.9"],
        ["0.2.2", "0.3.0", "1.0.0"],
    ),
    (
        # and once minor is also zero, caret tolerates nothing but patch itself.
        "^0.0.3",
        ["0.0.3"],
        ["0.0.2", "0.0.4", "0.1.0"],
    ),
    (
        "~1.2.3",
        ["1.2.3", "1.2.9"],
        ["1.2.2", "1.3.0", "2.0.0"],
    ),
    (
        ">=1.2.3 <2.0.0",
        ["1.2.3", "1.9.9"],
        ["1.2.2", "2.0.0"],
    ),
    (
        "1.2.3 || 2.0.0",
        ["1.2.3", "2.0.0"],
        ["1.2.4", "1.9.9"],
    ),
    (
        "1.2.3",
        ["1.2.3", "1.2.3+build.9"],
        ["1.2.4", "1.2.3-alpha"],
    ),
    (
        ">1.2.3",
        ["1.2.4", "2.0.0"],
        ["1.2.3", "1.2.2"],
    ),
    (
        "<=1.2.3",
        ["1.2.3", "1.0.0"],
        ["1.2.4"],
    ),
]

# A prerelease only satisfies a range if some comparator in the matching set
# is pinned to the exact same major.minor.patch and is itself a prerelease.
PRERELEASE_CASES = [
    ("^1.2.3", "1.3.0-alpha", False),
    ("^1.2.3", "2.0.0-alpha", False),
    ("^1.2.3-alpha.1", "1.2.3-alpha.5", True),
    ("^1.2.3-alpha.1", "1.2.3-alpha.0", False),
    (">=1.2.3-alpha", "1.2.3-beta", True),
]


class RangeMatchTests(unittest.TestCase):
    def test_ranges_match_expected_versions(self) -> None:
        for range_text, matching, non_matching in RANGE_CASES:
            parsed = Range.parse(range_text)
            for text in matching:
                with self.subTest(range=range_text, version=text, expect=True):
                    self.assertTrue(parsed.matches(text))
                    self.assertTrue(satisfies(text, range_text))
            for text in non_matching:
                with self.subTest(range=range_text, version=text, expect=False):
                    self.assertFalse(parsed.matches(text))
                    self.assertFalse(satisfies(text, range_text))

    def test_matches_accepts_version_instance(self) -> None:
        parsed = Range.parse("^1.2.3")
        self.assertTrue(parsed.matches(Version.parse("1.2.4")))
        self.assertFalse(parsed.matches(Version.parse("2.0.0")))

    def test_contains_operator(self) -> None:
        parsed = Range.parse("^1.2.3")
        self.assertIn(Version.parse("1.2.4"), parsed)
        self.assertNotIn(Version.parse("2.0.0"), parsed)

    def test_prerelease_pinning_rule(self) -> None:
        for range_text, version_text, expected in PRERELEASE_CASES:
            with self.subTest(range=range_text, version=version_text):
                self.assertEqual(satisfies(version_text, range_text), expected)


class RangeParseErrorTests(unittest.TestCase):
    def test_empty_range_is_rejected(self) -> None:
        with self.assertRaises(InvalidRangeError):
            Range.parse("")

    def test_empty_comparator_set_is_rejected(self) -> None:
        with self.assertRaises(InvalidRangeError):
            Range.parse("1.2.3 || ")

    def test_repr_round_trips_through_parse(self) -> None:
        r = Range.parse("^1.2.3")
        self.assertEqual(str(eval(repr(r), {"Range": Range})), str(r))


if __name__ == "__main__":
    unittest.main()
