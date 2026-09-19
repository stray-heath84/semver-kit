import unittest

from semverkit import InvalidVersionError, Version

VALID_PARSE_CASES = [
    # (input, major, minor, patch, prerelease, build)
    ("1.2.3", 1, 2, 3, "", ""),
    ("0.0.0", 0, 0, 0, "", ""),
    ("10.20.30", 10, 20, 30, "", ""),
    ("1.0.0-alpha", 1, 0, 0, "alpha", ""),
    ("1.0.0-alpha.1", 1, 0, 0, "alpha.1", ""),
    ("1.0.0-0.3.7", 1, 0, 0, "0.3.7", ""),
    ("1.0.0-x.7.z.92", 1, 0, 0, "x.7.z.92", ""),
    ("1.0.0-x-y-z.-", 1, 0, 0, "x-y-z.-", ""),
    ("1.0.0+20130313144700", 1, 0, 0, "", "20130313144700"),
    ("1.0.0-beta+exp.sha.5114f85", 1, 0, 0, "beta", "exp.sha.5114f85"),
    ("1.0.0+21AF26D3---117B344092BD", 1, 0, 0, "", "21AF26D3---117B344092BD"),
    ("  1.2.3  ", 1, 2, 3, "", ""),
]

# Cases that must be rejected, including the ones people get wrong: leading
# zeros in numeric fields, empty identifiers, and stray separators.
INVALID_PARSE_CASES = [
    "",
    "1",
    "1.2",
    "1.2.3.4",
    "01.2.3",
    "1.02.3",
    "1.2.03",
    "1.2.3-",
    "1.2.3+",
    "1.2.3-.",
    "1.2.3-alpha..1",
    "1.2.3-alpha_beta",
    "1.2.3+build..1",
    "-1.2.3",
    "1.-2.3",
    "1.2.-3",
    "v1.2.3",
    "1.2.3 extra",  # trailing garbage that strip() alone won't remove
    "1.2.3-alpha\n1.2.3",
]

# The precedence chain straight out of the semver.org spec (section 11),
# each version strictly less than the next.
SPEC_ORDERING_CHAIN = [
    "1.0.0-alpha",
    "1.0.0-alpha.1",
    "1.0.0-alpha.beta",
    "1.0.0-beta",
    "1.0.0-beta.2",
    "1.0.0-beta.11",
    "1.0.0-rc.1",
    "1.0.0",
]

EQUAL_IGNORING_BUILD_CASES = [
    ("1.0.0+build.1", "1.0.0+build.2"),
    ("1.0.0-alpha+001", "1.0.0-alpha+002"),
    ("1.2.3", "1.2.3+anything"),
]

# (smaller, larger) pairs covering ordering rules beyond the spec chain.
PAIRWISE_ORDERING_CASES = [
    ("1.0.0", "2.0.0"),
    ("2.0.0", "2.1.0"),
    ("2.1.0", "2.1.1"),
    ("1.0.0-alpha", "1.0.0"),
    ("1.0.0-alpha.1", "1.0.0-alpha.2"),
    # numeric identifiers compare numerically, not lexically: "9" < "10".
    ("1.0.0-alpha.9", "1.0.0-alpha.10"),
    # a purely numeric identifier always outranks an alphanumeric one at
    # the same position.
    ("1.0.0-alpha.9", "1.0.0-alpha.a"),
    # fewer identifiers ranks lower when the shared prefix is equal.
    ("1.0.0-alpha", "1.0.0-alpha.1"),
]


class ParseTests(unittest.TestCase):
    def test_valid_versions_parse_into_expected_fields(self) -> None:
        for text, major, minor, patch, prerelease, build in VALID_PARSE_CASES:
            with self.subTest(text=text):
                v = Version.parse(text)
                self.assertEqual(v.major, major)
                self.assertEqual(v.minor, minor)
                self.assertEqual(v.patch, patch)
                self.assertEqual(v.prerelease, prerelease)
                self.assertEqual(v.build, build)

    def test_invalid_versions_are_rejected(self) -> None:
        for text in INVALID_PARSE_CASES:
            with self.subTest(text=text):
                with self.assertRaises(InvalidVersionError):
                    Version.parse(text)

    def test_round_trip_through_str(self) -> None:
        for text, *_ in VALID_PARSE_CASES:
            with self.subTest(text=text):
                normalized = text.strip()
                self.assertEqual(str(Version.parse(text)), normalized)


class OrderingTests(unittest.TestCase):
    def test_spec_precedence_chain_is_strictly_increasing(self) -> None:
        versions = [Version.parse(text) for text in SPEC_ORDERING_CHAIN]
        for earlier, later in zip(versions, versions[1:]):
            with self.subTest(earlier=str(earlier), later=str(later)):
                self.assertLess(earlier, later)
                self.assertGreater(later, earlier)
                self.assertNotEqual(earlier, later)

    def test_pairwise_ordering_cases(self) -> None:
        for smaller_text, larger_text in PAIRWISE_ORDERING_CASES:
            with self.subTest(smaller=smaller_text, larger=larger_text):
                smaller = Version.parse(smaller_text)
                larger = Version.parse(larger_text)
                self.assertLess(smaller, larger)
                self.assertLessEqual(smaller, larger)
                self.assertGreater(larger, smaller)

    def test_build_metadata_does_not_affect_equality_or_order(self) -> None:
        for left_text, right_text in EQUAL_IGNORING_BUILD_CASES:
            with self.subTest(left=left_text, right=right_text):
                left = Version.parse(left_text)
                right = Version.parse(right_text)
                self.assertEqual(left, right)
                self.assertFalse(left < right)
                self.assertFalse(right < left)
                self.assertEqual(hash(left), hash(right))

    def test_sorting_a_shuffled_list_matches_spec_chain(self) -> None:
        shuffled_texts = [
            "1.0.0",
            "1.0.0-rc.1",
            "1.0.0-beta.11",
            "1.0.0-alpha",
            "1.0.0-beta.2",
            "1.0.0-alpha.beta",
            "1.0.0-beta",
            "1.0.0-alpha.1",
        ]
        sorted_versions = sorted(Version.parse(t) for t in shuffled_texts)
        self.assertEqual(
            [str(v) for v in sorted_versions],
            SPEC_ORDERING_CHAIN,
        )


class MiscTests(unittest.TestCase):
    def test_repr_round_trips_through_parse(self) -> None:
        v = Version.parse("1.2.3-rc.1+build.9")
        self.assertEqual(eval(repr(v), {"Version": Version}), v)

    def test_version_is_immutable(self) -> None:
        v = Version.parse("1.2.3")
        with self.assertRaises(AttributeError):
            v.major = 9  # type: ignore[misc]

    def test_is_prerelease_flag(self) -> None:
        self.assertTrue(Version.parse("1.0.0-alpha").is_prerelease)
        self.assertFalse(Version.parse("1.0.0").is_prerelease)


if __name__ == "__main__":
    unittest.main()
