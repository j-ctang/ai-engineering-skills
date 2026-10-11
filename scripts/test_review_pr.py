import unittest

from review_pr import render, validate


def finding(severity, check="correctness"):
    return {"check": check, "severity": severity, "path": "a.ts", "line": 1,
            "problem": "P.", "failure_scenario": "F.", "fix": "X."}


def checks(**fails):
    names = ["scope", "acceptance", "correctness", "tests", "safety", "docs", "pr_hygiene"]
    return {n: fails.get(n, "pass") for n in names}


class ValidateTest(unittest.TestCase):
    def test_fail_without_blocker_rejected(self):
        with self.assertRaises(ValueError):
            validate({"checks": checks(tests="fail"), "findings": [], "follow_ups": []})

    def test_blocker_without_fail_rejected(self):
        with self.assertRaises(ValueError):
            validate({"checks": checks(), "findings": [finding("blocker")], "follow_ups": []})

    def test_missing_key_rejected(self):
        with self.assertRaises(ValueError):
            validate({"checks": checks(), "findings": []})

    def test_unknown_severity_rejected(self):
        bad = dict(finding("nit"), severity="critical")
        with self.assertRaises(ValueError):
            validate({"checks": checks(), "findings": [bad], "follow_ups": []})

    def test_extra_finding_field_rejected(self):
        bad = dict(finding("nit"), extra="x")
        with self.assertRaises(ValueError):
            validate({"checks": checks(), "findings": [bad], "follow_ups": []})

    def test_nits_capped(self):
        review = validate({"checks": checks(), "findings": [finding("nit")] * 5,
                           "follow_ups": []})
        self.assertEqual(len(review["findings"]), 3)


class RenderTest(unittest.TestCase):
    def test_no_findings(self):
        text = render("Ready to merge", {"findings": [], "follow_ups": []})
        self.assertIn("No blocking findings.", text)

    def test_blockers_first(self):
        text = render("Changes needed",
                      {"findings": [finding("nit"), finding("blocker")], "follow_ups": ["Later."]})
        self.assertLess(text.index("blocker"), text.index("nit"))
        self.assertIn("Follow-ups", text)


if __name__ == "__main__":
    unittest.main()
