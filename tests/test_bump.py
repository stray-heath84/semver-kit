import unittest

from semverkit import InvalidVersionError, Version

BUMP_CASES = [
    # (start, part, prerelease_id, expected)
    ("1.2.3", "major", "", "2.0.0"),
    ("1.2.3", "minor", "", "1.3.0"),
    ("1.2.3", "patch", "", "1.2.4"),
    ("1.2.3+build.5", "patch", "", "1.2.4"),
    ("1.2.3-rc.1", "patch", "", "1.2.3"),
    ("1.2.0-rc.1", "minor", "", "1.2.0"),
    ("1.2.3-rc.1", "minor", "", "1.3.0"),
    ("2.0.0-rc.1", "major", "", "2.0.0"),
    ("2.1.0-rc.1", "major", "", "3.0.0"),
    ("1.2.3", "prerelease", "", "1.2.4-0"),
    ("1.2.3", "prerelease", "rc", "1.2.4-rc.0"),
    ("1.2.4-rc.0", "prerelease", "rc", "1.2.4-rc.1"),
    ("1.2.4-rc.9", "prerelease", "", "1.2.4-rc.10"),
    ("1.2.4-rc.1", "prerelease", "beta", "1.2.4-beta.0"),
    ("1.2.4-rc", "prerelease", "", "1.2.4-rc.0"),
    ("1.2.4-0", "prerelease", "", "1.2.4-1"),
    ("1.2.4-rc.1.x", "prerelease", "", "1.2.4-rc.2.x"),
    ("1.2.4-rc.1+meta", "prerelease", "rc", "1.2.4-rc.2"),
]


class BumpTests(unittest.TestCase):
    def test_cases(self):
        for start, part, ident, expected in BUMP_CASES:
            with self.subTest(start=start, part=part, ident=ident):
                result = Version.parse(start).bump(part, ident)
                self.assertEqual(str(result), expected)

    def test_original_is_unchanged(self):
        v = Version.parse("1.2.3")
        v.bump("major")
        self.assertEqual(str(v), "1.2.3")

    def test_bump_orders_after_original(self):
        for start in ("1.2.3", "1.2.3-rc.1", "0.0.0-0", "1.0.0-alpha"):
            v = Version.parse(start)
            for part in ("major", "minor", "patch", "prerelease"):
                with self.subTest(start=start, part=part):
                    self.assertGreater(v.bump(part), v)

    def test_unknown_part(self):
        with self.assertRaises(ValueError):
            Version.parse("1.2.3").bump("build")

    def test_prerelease_id_needs_prerelease_part(self):
        with self.assertRaises(ValueError):
            Version.parse("1.2.3").bump("patch", "rc")

    def test_invalid_prerelease_id(self):
        for bad in ("a..b", "01", "rc_1", "rc."):
            with self.subTest(bad=bad):
                with self.assertRaises(InvalidVersionError):
                    Version.parse("1.2.3").bump("prerelease", bad)


if __name__ == "__main__":
    unittest.main()
