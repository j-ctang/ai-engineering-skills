import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import review_pr
from review_pr import (assess_follow_up, classify, conclude, diff_stats, downgrade, earlier_block,
                       format_checks, is_ancestor, load_earlier, new_record, recheck,
                       recheck_schema, recorded, render, validate)


def numstat(*rows):
    return [(str(a), str(r), (p,)) for a, r, p in rows]


class ClassifyTest(unittest.TestCase):
    def test_small(self):
        self.assertEqual(classify(numstat((10, 5, "src/a.ts")), []), ("S", 15, 1, []))

    def test_medium_by_lines(self):
        self.assertEqual(classify(numstat((40, 20, "src/a.ts")), [])[0], "M")

    def test_medium_by_files(self):
        rows = [(1, 0, f"src/{i}.ts") for i in range(4)]
        self.assertEqual(classify(numstat(*rows), [])[0], "M")

    def test_large_by_lines(self):
        self.assertEqual(classify(numstat((301, 0, "src/a.ts")), [])[0], "L")

    def test_large_by_files(self):
        rows = [(1, 0, f"src/{i}.ts") for i in range(11)]
        self.assertEqual(classify(numstat(*rows), [])[0], "L")

    def test_lockfile_ignored_for_size_but_escalates(self):
        tier, lines, files, hits = classify(
            numstat((5, 0, "src/a.ts"), (900, 800, "package-lock.json")), [])
        self.assertEqual((tier, lines, files, hits), ("M+", 5, 1, ["dependencies"]))

    def test_tests_excluded_from_size(self):
        rows = [(40, 0, "src/a.ts"), (200, 0, "test/a.test.ts"), (90, 0, "scripts/test_x.py")]
        self.assertEqual(classify(numstat(*rows), [])[:3], ("S", 40, 1))

    def test_binary_counts_as_file(self):
        self.assertEqual(classify(numstat(("-", "-", "img.png")), [])[:3], ("S", 0, 1))

    def test_escalations(self):
        cases = {
            ".github/workflows/ci.yml": "ci",
            "AGENTS.md": "agent-rules",
            "package.json": "dependencies",
            "jest.config.js": "test-gates",
            "tsconfig.build.json": "test-gates",
            "scripts/check.sh": "test-gates",
            "src/auth/session.ts": "secrets",
            ".env.example": "secrets",
        }
        for path, reason in cases.items():
            with self.subTest(path=path):
                tier, _, _, hits = classify(numstat((3, 1, path)), [])
                self.assertEqual(tier, "M+")
                self.assertIn(reason, hits)

    def test_rename_sides_both_checked(self):
        rows = [("0", "0", ("AGENTS.md", "docs/rules.md"))]
        self.assertIn("agent-rules", classify(rows, [])[3])

    def test_deleted_test_escalates(self):
        hits = classify(numstat((0, 30, "test/a.test.ts")), ["test/a.test.ts"])[3]
        self.assertIn("deleted-tests", hits)


def finding(severity, check="correctness", category=None):
    if category is None:
        category = "wrong-behavior" if severity == "blocker" else "none"
    return {"check": check, "severity": severity, "category": category, "path": "a.ts",
            "line": 1, "problem": "P.", "failure_scenario": "F.", "fix": "X."}


def checks(**fails):
    names = ["scope", "acceptance", "correctness", "tests", "safety", "docs", "pr_hygiene"]
    return {n: fails.get(n, "pass") for n in names}


class GitDiffTest(unittest.TestCase):
    """Run diff_stats against a real repo, so git's output format is covered."""

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.repo = Path(self.dir.name)
        self.git("init", "-q")
        self.write("test/a.test.ts", "x\n" * 20)
        self.write("src/big.ts", "".join(f"line {i}\n" for i in range(400)))
        self.commit()
        self.base = self.git("rev-parse", "HEAD").strip()

    def tearDown(self):
        self.dir.cleanup()

    def git(self, *args):
        return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t",
                               "-c", "commit.gpgsign=false", *args],
                              cwd=self.repo, check=True, capture_output=True, text=True).stdout

    def write(self, path, text):
        (self.repo / path).parent.mkdir(parents=True, exist_ok=True)
        (self.repo / path).write_text(text)

    def commit(self):
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "c")
        return self.git("rev-parse", "HEAD").strip()

    def test_quoted_path_still_escalates(self):
        self.write(".github/workflows/ci \u00e4.yml", "a\n")
        head = self.commit()
        tier, _, _, hits = classify(*diff_stats(self.repo, self.base, head))
        self.assertEqual((tier, hits), ("M+", ["ci"]))

    def test_pure_move_counts_no_lines(self):
        self.git("mv", "src/big.ts", "src/moved.ts")
        head = self.commit()
        self.assertEqual(classify(*diff_stats(self.repo, self.base, head))[:3], ("S", 0, 1))

    def test_test_moved_out_of_tests_counts_as_deleted(self):
        self.git("mv", "test/a.test.ts", "src/a.ts")
        head = self.commit()
        self.assertIn("deleted-tests", classify(*diff_stats(self.repo, self.base, head))[3])

    def test_ancestor_check(self):
        head = self.commit_change("src/new.ts")
        self.assertTrue(is_ancestor(self.repo, self.base, head))
        self.git("checkout", "-q", "-b", "other", self.base)
        other = self.commit_change("src/other.ts")
        self.assertFalse(is_ancestor(self.repo, head, other))
        self.assertFalse(is_ancestor(self.repo, "0" * 40, other))

    def commit_change(self, path):
        self.write(path, "a\n")
        return self.commit()

    def test_test_moved_between_test_paths_is_not_deleted(self):
        (self.repo / "tests").mkdir()
        self.git("mv", "test/a.test.ts", "tests/a.test.ts")
        head = self.commit()
        self.assertNotIn("deleted-tests", classify(*diff_stats(self.repo, self.base, head))[3])


class CiTest(unittest.TestCase):
    def test_format_checks(self):
        runs = [{"name": "offline-check", "status": "completed", "conclusion": "success"},
                {"name": "lint", "status": "in_progress", "conclusion": None}]
        statuses = [{"context": "deploy", "state": "failure"}]
        self.assertEqual(format_checks(runs, statuses),
                         "offline-check: success, lint: in_progress, deploy: failure")
        self.assertEqual(format_checks([], []), "none")

    def test_reads_pinned_head_on_every_page(self):
        with mock.patch.object(review_pr, "sh", return_value="") as sh:
            review_pr.ci_result("o/r", "abc123")
        urls = [c.args[3] for c in sh.call_args_list]
        self.assertEqual(urls, ["repos/o/r/commits/abc123/check-runs",
                                "repos/o/r/commits/abc123/status"])
        self.assertTrue(all("--paginate" in c.args for c in sh.call_args_list))


class RecordedTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.out = Path(self.dir.name)

    def tearDown(self):
        self.dir.cleanup()

    def record(self):
        return json.loads((self.out / "run.json").read_text())

    def test_failure_keeps_record(self):
        with self.assertRaises(ValueError):
            with recorded(self.out, {"pr": 1}):
                raise ValueError("bad JSON")
        self.assertEqual(self.record()["status"], "failed")
        self.assertEqual(self.record()["error"], "ValueError: bad JSON")

    def test_success_records_ok(self):
        with recorded(self.out, {"pr": 1}):
            pass
        self.assertEqual(self.record()["status"], "ok")

    def test_dry_run_status_kept(self):
        with recorded(self.out, {"status": "dry-run"}):
            pass
        self.assertEqual(self.record()["status"], "dry-run")


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

    def test_unknown_category_rejected(self):
        bad = finding("blocker", category="style")
        with self.assertRaises(ValueError):
            validate({"checks": checks(correctness="fail"), "findings": [bad], "follow_ups": []})


class DowngradeTest(unittest.TestCase):
    def test_blocker_without_category_downgraded(self):
        review = {"checks": checks(correctness="fail"),
                  "findings": [finding("blocker", category="none")], "follow_ups": []}
        self.assertEqual(downgrade(validate(review)), 1)
        self.assertEqual(review["findings"][0]["severity"], "should-fix")
        self.assertEqual(review["checks"]["correctness"], "pass")

    def test_check_with_real_blocker_stays_failed(self):
        review = {"checks": checks(correctness="fail"),
                  "findings": [finding("blocker", category="none"), finding("blocker")],
                  "follow_ups": []}
        self.assertEqual(downgrade(validate(review)), 1)
        self.assertEqual(review["checks"]["correctness"], "fail")

    def test_categorized_blockers_kept(self):
        review = {"checks": checks(safety="fail", tests="fail"),
                  "findings": [finding("blocker", "safety", "security"),
                               finding("blocker", "tests", "weakened-gate")],
                  "follow_ups": []}
        self.assertEqual(downgrade(validate(review)), 0)
        self.assertEqual([f["severity"] for f in review["findings"]], ["blocker"] * 2)


class ConcludeTest(unittest.TestCase):
    def test_run_record_counts_downgrades(self):
        review = {"checks": checks(correctness="fail"),
                  "findings": [finding("blocker", category="none"), finding("nit")],
                  "follow_ups": []}
        run = {}
        comment = conclude(validate(review), "S", [], run)
        self.assertEqual(run["downgraded"], 1)
        self.assertEqual(run["verdict"], "Ready to merge")
        self.assertEqual(run["findings"], {"blocker": 0, "should-fix": 1, "nit": 1})
        self.assertIn("Ready to merge", comment)


class RenderTest(unittest.TestCase):
    def test_no_findings(self):
        text = render("Ready to merge", "S", [], {"findings": [], "follow_ups": []})
        self.assertIn("No blocking findings.", text)

    def test_blockers_first_and_tier_label(self):
        text = render("Changes needed", "M+", ["ci"],
                      {"findings": [finding("nit"), finding("blocker")], "follow_ups": ["Later."]})
        self.assertLess(text.index("blocker"), text.index("nit"))
        self.assertIn("Review tier: M+ (ci)", text)
        self.assertIn("Follow-ups", text)


def earlier_finding(severity, path="a.ts"):
    return dict(finding(severity), path=path)


def status(id, state):
    return {"id": id, "status": state, "note": "N."}


class RecheckTest(unittest.TestCase):
    def setUp(self):
        self.earlier = [earlier_finding("blocker", "old.ts"), earlier_finding("should-fix", "b.ts")]

    def review(self, statuses, findings=(), **fails):
        return {"checks": checks(**fails), "findings": list(findings), "follow_ups": [],
                "earlier": statuses}

    def test_open_earlier_finding_keeps_severity(self):
        review = self.review([status(1, "open"), status(2, "fixed")])
        self.assertEqual(recheck(review, self.earlier, {"a.ts"}), {"fixed": 1, "open": 1})
        self.assertEqual(review["findings"], [self.earlier[0]])
        self.assertEqual(review["checks"]["correctness"], "fail")
        self.assertEqual([f["status"] for f in review["earlier"]], ["open", "fixed"])

    def test_check_failed_by_open_earlier_blocker_accepted(self):
        review = self.review([status(1, "open"), status(2, "fixed")], correctness="fail")
        self.assertEqual(assess_follow_up(review, self.earlier, {"a.ts"}),
                         {"fixed": 1, "open": 1})
        run = {}
        conclude(review, "S", [], run)
        self.assertEqual(run["verdict"], "Changes needed")

    def test_follow_up_still_rejects_bad_findings(self):
        bad = dict(finding("nit"), severity="critical")
        with self.assertRaises(ValueError):
            assess_follow_up(self.review([status(1, "open"), status(2, "fixed")], [bad]),
                             self.earlier, {"a.ts"})

    def test_missing_status_rejected(self):
        with self.assertRaises(ValueError):
            recheck(self.review([status(1, "fixed")]), self.earlier, set())

    def test_unknown_or_duplicate_id_rejected(self):
        for statuses in ([status(1, "fixed"), status(3, "fixed")],
                         [status(1, "fixed"), status(1, "open")]):
            with self.subTest(statuses=statuses), self.assertRaises(ValueError):
                recheck(self.review(statuses), self.earlier, set())

    def test_missing_earlier_key_rejected(self):
        review = self.review([])
        del review["earlier"]
        with self.assertRaises(ValueError):
            recheck(review, self.earlier, set())

    def test_unknown_status_rejected(self):
        with self.assertRaises(ValueError):
            recheck(self.review([status(1, "wontfix"), status(2, "fixed")]), self.earlier, set())

    def test_new_finding_outside_new_commits_becomes_follow_up(self):
        outside = dict(finding("blocker"), path="old.ts")
        review = self.review([status(1, "fixed"), status(2, "fixed")],
                             [finding("nit"), outside], correctness="fail")
        recheck(review, self.earlier, {"a.ts"})
        self.assertEqual(review["findings"], [finding("nit")])
        self.assertEqual(review["follow_ups"], ["old.ts:1: P."])
        self.assertEqual(review["checks"]["correctness"], "pass")

    def test_verdict_counts_open_earlier_and_new_blockers(self):
        review = self.review([status(1, "fixed"), status(2, "fixed")])
        recheck(review, self.earlier, {"a.ts"})
        self.assertEqual(conclude(review, "S", [], {}).splitlines()[0],
                         "**Verdict:** Ready to merge")
        review = self.review([status(1, "open"), status(2, "fixed")])
        recheck(review, self.earlier, {"a.ts"})
        run = {}
        conclude(review, "S", [], run)
        self.assertEqual(run["verdict"], "Changes needed")
        review = self.review([status(1, "fixed"), status(2, "fixed")],
                             [finding("blocker")], correctness="fail")
        recheck(review, self.earlier, {"a.ts"})
        self.assertEqual(conclude(review, "S", [], {}).splitlines()[0],
                         "**Verdict:** Changes needed")

    def test_render_lists_fixed_findings(self):
        review = self.review([status(1, "fixed"), status(2, "open")])
        recheck(review, self.earlier, {"a.ts"})
        text = conclude(review, "S", [], {})
        self.assertIn("Fixed since the last review:", text)
        self.assertIn("`old.ts:1`: P. N.", text)

    def test_schema_requires_earlier(self):
        schema = recheck_schema()
        self.assertIn("earlier", schema["required"])
        item = schema["properties"]["earlier"]["items"]
        self.assertEqual(item["properties"]["status"]["enum"], ["fixed", "open"])
        self.assertNotIn("earlier", json.loads(review_pr.SCHEMA.read_text())["required"])

    def test_earlier_block_numbers_findings(self):
        text = earlier_block(self.earlier, "abc123")
        self.assertIn("abc123", text)
        self.assertIn("1. [blocker] `old.ts:1`: P. Fix: X.", text)
        self.assertIn("2. [should-fix] `b.ts:1`", text)


class NewRecordTest(unittest.TestCase):
    def args(self, since=None):
        return mock.Mock(reviewer="codex", repo="o/r", pr=3, since=since)

    def test_first_round(self):
        run = new_record(self.args(), "abc", None)
        self.assertEqual((run["round"], "since" in run), (1, False))

    def test_follow_up_counts_rounds_and_names_earlier_run(self):
        run = new_record(self.args(Path("/tmp/review/r1")), "def", ({"round": 2}, []))
        self.assertEqual((run["round"], run["since"]), (3, "/tmp/review/r1"))
        run = new_record(self.args(Path("/tmp/review/r0")), "def", ({}, []))
        self.assertEqual(run["round"], 2)


class LoadEarlierTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.out = Path(self.dir.name)

    def tearDown(self):
        self.dir.cleanup()

    def write(self, run, findings=None):
        (self.out / "run.json").write_text(json.dumps(run))
        if findings is not None:
            (self.out / "review.json").write_text(json.dumps({"findings": findings}))

    def test_loads_finished_run(self):
        run = {"repo": "o/r", "pr": 3, "status": "ok", "head": "abc", "round": 2}
        self.write(run, [finding("nit")])
        self.assertEqual(load_earlier(self.out, "o/r", 3), (run, [finding("nit")]))

    def test_rejects_other_pr_failed_run_or_missing_review(self):
        cases = [({"repo": "o/r", "pr": 4, "status": "ok", "head": "a"}, []),
                 ({"repo": "o/r", "pr": 3, "status": "failed", "head": "a"}, []),
                 ({"repo": "o/r", "pr": 3, "status": "ok", "head": "a"}, None)]
        for run, findings in cases:
            with self.subTest(run=run, findings=findings):
                (self.out / "review.json").unlink(missing_ok=True)
                self.write(run, findings)
                with self.assertRaises(ValueError):
                    load_earlier(self.out, "o/r", 3)


if __name__ == "__main__":
    unittest.main()
