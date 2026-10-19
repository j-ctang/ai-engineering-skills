import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

import metrics
from metrics import classify, kind_of, load_runs, report, reverts, row, verdicts


def pr(n=1, base="staging", head="feat/x", labels=(), paths=("src/a.ts",), **kw):
    p = {
        "number": n,
        "title": f"PR {n}",
        "body": "",
        "state": "MERGED",
        "createdAt": "2026-10-14T10:00:00Z",
        "mergedAt": "2026-10-14T12:00:00Z",
        "closedAt": "2026-10-14T12:00:00Z",
        "baseRefName": base,
        "headRefName": head,
        "labels": [{"name": x} for x in labels],
        "additions": 10,
        "deletions": 2,
        "changedFiles": len(paths),
        "files": [{"path": x} for x in paths],
        "commits": [{"committedDate": "2026-10-14T09:00:00Z"}],
        "comments": [],
    }
    p.update(kw)
    return p


def comment(at, body, by="j-ctang"):
    return {"author": {"login": by}, "createdAt": at, "body": body}


class ClassifyTest(unittest.TestCase):
    def kind(self, role, p):
        return classify(role, p)["kind"], classify(role, p)["rule"]

    def test_planted_label_wins(self):
        self.assertEqual(
            self.kind("product", pr(labels=["planted-bug"])), ("planted", "planted-bug label")
        )

    def test_kind_label_overrides_rules(self):
        self.assertEqual(self.kind("harness", pr(labels=["kind:product"])), ("product", "kind label"))

    def test_unknown_kind_label_fails(self):
        with self.assertRaisesRegex(ValueError, "unknown kind"):
            classify("product", pr(labels=["kind:infra"]))

    def test_several_kind_labels_fail(self):
        with self.assertRaisesRegex(ValueError, "several kind"):
            classify("product", pr(labels=["kind:product", "kind:harness"]))

    def test_planted_conflicting_kind_label_fails(self):
        with self.assertRaisesRegex(ValueError, "conflicts"):
            classify("product", pr(labels=["planted-bug", "kind:product"]))

    def test_promote_and_sync_are_ops(self):
        self.assertEqual(self.kind("product", pr(base="main", head="staging"))[0], "ops")
        self.assertEqual(self.kind("product", pr(base="staging", head="main"))[0], "ops")

    def test_harness_repo(self):
        self.assertEqual(self.kind("harness", pr()), ("harness", "harness repo"))

    def test_product_repo_tooling_only_is_harness(self):
        p = pr(paths=[".github/workflows/ci.yml", "AGENTS.md", ".coderabbit.yaml", "docs/CLAUDE.md"])
        self.assertEqual(self.kind("product", p), ("harness", "harness paths only"))

    def test_product_repo_code_is_product(self):
        self.assertEqual(
            self.kind("product", pr(paths=["src/a.ts", "README.md"])), ("product", "product repo")
        )

    def test_mixed_product_pr_is_flagged(self):
        self.assertTrue(classify("product", pr(paths=["src/a.ts", "AGENTS.md"]))["mixed"])
        self.assertFalse(classify("product", pr(paths=["src/a.ts"]))["mixed"])
        self.assertFalse(classify("harness", pr(paths=["src/a.ts", "AGENTS.md"]))["mixed"])

    def test_truncated_file_list_is_marked(self):
        p = pr(paths=["AGENTS.md"], changedFiles=150)
        self.assertIn("truncated", classify("product", p)["rule"])


class KindOfTest(unittest.TestCase):
    def test_merged_kind_is_kept_after_rules_change(self):
        kinds: dict[str, dict[str, object]] = {}
        first = kind_of(kinds, "product", pr(paths=["src/a.ts"]))
        self.assertEqual(kinds["1"], first)
        # The same merged PR, now with a label that would give another kind.
        again = kind_of(kinds, "product", pr(paths=["src/a.ts"], labels=["kind:harness"]))
        self.assertEqual(again["kind"], "product")

    def test_open_pr_is_not_stored(self):
        kinds: dict[str, dict[str, object]] = {}
        kind_of(kinds, "product", pr(mergedAt=None))
        self.assertEqual(kinds, {})


class VerdictTest(unittest.TestCase):
    def test_reads_posted_verdicts_and_skips_bots(self):
        p = pr(
            comments=[
                {"author": None, "createdAt": "2026-10-14T10:10:00Z", "body": "**Verdict:** Ready"},
                comment("2026-10-14T11:00:00Z", "**Verdict:** Ready to merge\n\nNo blocking findings."),
                comment("2026-10-14T10:30:00Z", "**Verdict:** Changes needed"),
                comment("2026-10-14T10:40:00Z", "**Verdict:** Ready", by="coderabbitai"),
                comment("2026-10-14T10:50:00Z", "Looks fine"),
            ]
        )
        self.assertEqual([ok for _, ok in verdicts(p)], [False, True])


class RowTest(unittest.TestCase):
    def test_first_pass_needs_ready_first_and_no_later_commit(self):
        ready = [comment("2026-10-14T11:00:00Z", "**Verdict:** Ready to merge")]
        self.assertTrue(row("r", pr(comments=ready), classify("product", pr()))["first_pass"])
        later = pr(comments=ready, commits=[{"committedDate": "2026-10-14T11:30:00Z"}])
        self.assertFalse(row("r", later, classify("product", pr()))["first_pass"])
        changes = [comment("2026-10-14T11:00:00Z", "**Verdict:** Changes needed"), *ready]
        self.assertFalse(row("r", pr(comments=changes), classify("product", pr()))["first_pass"])

    def test_wait_by_stage(self):
        p = pr(comments=[comment("2026-10-14T11:00:00Z", "**Verdict:** Ready to merge")])
        w = row("r", p, classify("product", p))["wait"]
        self.assertEqual(
            w,
            {
                "first commit > open": 60,
                "open > first review": 60,
                "last commit > merge": 180,
                "last Ready > merge": 60,
            },
        )


class RevertTest(unittest.TestCase):
    def test_body_and_title_link_the_reverted_pr(self):
        prs = [
            pr(1, title="Add cache"),
            pr(2, title="Fix log"),
            pr(3, title='Revert "Add cache"'),
            pr(4, title="Undo log fix", body="Reverts j-ctang/x#2"),
            pr(5, title='Revert "Fix log"', mergedAt=None),
        ]
        self.assertEqual(reverts(prs), {1: 3, 2: 4})


class ReportTest(unittest.TestCase):
    def rows(self):
        ready = [comment("2026-10-14T11:00:00Z", "**Verdict:** Ready to merge")]
        a = row("o/p", pr(1, comments=ready), classify("product", pr(1)))
        b = row("o/h", pr(2), classify("harness", pr(2)))
        c = row("o/p", pr(3, labels=["planted-bug"]), classify("product", pr(3, labels=["planted-bug"])))
        late = pr(4, mergedAt="2026-10-20T12:00:00Z")
        d = row("o/p", late, classify("product", late))
        a["reverted_by"] = 9
        return [a, b, c, d]

    def test_counts_only_the_date_range(self):
        runs = [
            {"repo": "o/p", "pr": 1, "status": "ok", "seconds": 20},
            {"repo": "o/p", "pr": 1, "status": "failed", "seconds": 5},
            {"repo": "o/p", "pr": 4, "status": "ok", "seconds": 30},
        ]
        rep = report(self.rows(), runs, date(2026, 10, 10), date(2026, 10, 15))
        self.assertEqual(rep["merged"], {"product": 1, "harness": 1, "planted": 1})
        self.assertEqual(rep["first_pass"], {"ready": 1, "reviewed": 1})
        self.assertEqual(rep["unreviewed"], ["o/h#2"])
        self.assertEqual(rep["reverts"], ["o/p#1 by #9"])
        self.assertEqual(rep["revert_rate"], 0.5)
        self.assertEqual(rep["review_runs"], {"runs": 2, "failed": 1, "model_seconds": 25})
        self.assertEqual(rep["active_days"], 1)
        self.assertIn("first pass: {'ready': 1, 'reviewed': 1}", metrics.render(rep))

    def test_empty_range(self):
        rep = report(self.rows(), [], date(2026, 1, 1), date(2026, 1, 2))
        self.assertEqual((rep["merged"], rep["revert_rate"]), ({}, None))
        metrics.render(rep)


class CollectTest(unittest.TestCase):
    def test_offline_reads_cache_and_keeps_kinds(self):
        with tempfile.TemporaryDirectory() as d:
            cache = Path(d) / "pr-metrics"
            cache.mkdir()
            stored = {"kind": "harness", "rule": "kind label", "mixed": False, "version": 1}
            (cache / "o-p.json").write_text(json.dumps({"prs": [pr(1)], "kinds": {"1": stored}}))
            with (
                mock.patch.object(metrics, "REPOS", {"o/p": "product"}),
                mock.patch.object(metrics, "cache_dir", return_value=cache),
                mock.patch.object(metrics, "gh_prs") as gh,
            ):
                rows = metrics.collect(offline=True)
            gh.assert_not_called()
            self.assertEqual(rows[0]["kind"], "harness")

    def test_gh_is_retried(self):
        fail = mock.Mock(returncode=1, stderr="error connecting to api.github.com", stdout="")
        node = {
            "number": 1,
            "labels": {"nodes": [{"name": "risk:low"}]},
            "files": {"nodes": [{"path": "a"}]},
            "commits": {"nodes": [{"commit": {"committedDate": "2026-10-14T09:00:00Z"}}]},
            "comments": {"nodes": []},
        }
        page = {"data": {"repository": {"pullRequests": {"nodes": [node]}}}}
        ok = mock.Mock(returncode=0, stdout=json.dumps([page]))
        with mock.patch("subprocess.run", side_effect=[fail, ok]), mock.patch("builtins.print"):
            (got,) = metrics.gh_prs("o/p", wait=0)
        self.assertEqual(got["labels"], [{"name": "risk:low"}])
        self.assertEqual(got["commits"], [{"committedDate": "2026-10-14T09:00:00Z"}])


class LoadRunsTest(unittest.TestCase):
    def test_reads_run_records_and_skips_broken_ones(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "a").mkdir()
            (Path(d) / "a" / "run.json").write_text('{"pr": 1}')
            (Path(d) / "b").mkdir()
            (Path(d) / "b" / "run.json").write_text("{")
            with mock.patch("builtins.print"):
                self.assertEqual(load_runs(Path(d)), [{"pr": 1}])


if __name__ == "__main__":
    unittest.main()
