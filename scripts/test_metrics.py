import json
import subprocess
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path
from unittest import mock

import metrics
from metrics import classify, completed, kind_of, load_runs, report, reverts, row


def pr(n=1, base="staging", head="feat/x", labels=(), paths=("src/a.ts",), **kw):
    p = {
        "number": n,
        "title": f"PR {n}",
        "body": "",
        "createdAt": "2026-10-14T10:00:00Z",
        "mergedAt": "2026-10-14T12:00:00Z",
        "baseRefName": base,
        "headRefName": head,
        "headRefOid": "h2",
        "labels": [{"name": x} for x in labels],
        "additions": 10,
        "deletions": 2,
        "changedFiles": len(paths),
        "files": [{"path": x} for x in paths],
    }
    p.update(kw)
    return p


def run(at, verdict="Ready to merge", head="h2", **kw):
    return {
        "repo": "o/p",
        "pr": 1,
        "head": head,
        "verdict": verdict,
        "at": datetime.fromisoformat(at),
        **kw,
    }


class ClassifyTest(unittest.TestCase):
    def kind(self, role, p):
        k = classify(role, p)
        return k["kind"], k["rule"]

    def test_planted_label_wins(self):
        self.assertEqual(
            self.kind("product", pr(labels=["planted-bug"])), ("planted", "planted-bug label")
        )

    def test_planted_wins_over_any_kind_label(self):
        for extra in ("kind:product", "kind:infra"):
            self.assertEqual(self.kind("product", pr(labels=["planted-bug", extra]))[0], "planted")

    def test_kind_label_overrides_rules(self):
        self.assertEqual(self.kind("harness", pr(labels=["kind:product"])), ("product", "kind label"))

    def test_unknown_kind_label_fails(self):
        with self.assertRaisesRegex(ValueError, "unknown kind"):
            classify("product", pr(labels=["kind:infra"]))

    def test_several_kind_labels_fail(self):
        with self.assertRaisesRegex(ValueError, "several kind"):
            classify("product", pr(labels=["kind:product", "kind:harness"]))

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

    def test_truncated_file_list_fails_only_for_the_path_rule(self):
        big = pr(paths=["AGENTS.md"], changedFiles=150)
        with self.assertRaisesRegex(ValueError, "truncated"):
            classify("product", big)
        self.assertEqual(self.kind("harness", big)[0], "harness")
        labelled = classify("product", {**big, "labels": [{"name": "kind:product"}]})
        self.assertEqual((labelled["kind"], labelled["mixed"]), ("product", None))


class KindOfTest(unittest.TestCase):
    def test_merged_kind_is_kept_after_rules_change(self):
        kinds: dict[str, dict[str, object]] = {}
        first = kind_of(kinds, "product", pr(paths=["src/a.ts"]))
        self.assertEqual(kinds["1"], first)
        again = kind_of(kinds, "product", pr(paths=["src/a.ts"], labels=["kind:harness"]))
        self.assertEqual(again["kind"], "product")

    def test_open_pr_is_not_stored(self):
        kinds: dict[str, dict[str, object]] = {}
        kind_of(kinds, "product", pr(mergedAt=None))
        self.assertEqual(kinds, {})


class RowTest(unittest.TestCase):
    def first_pass(self, reviews, **kw):
        p = pr(**kw)
        return row("o/p", p, classify("product", p), reviews)["first_pass"]

    def test_first_pass_needs_ready_first_review_of_the_final_head(self):
        self.assertTrue(self.first_pass([run("2026-10-14T11:00:00+00:00")]))
        # Ready, but more was pushed after the reviewed head.
        self.assertFalse(self.first_pass([run("2026-10-14T11:00:00+00:00", head="h1")]))
        changes = [run("2026-10-14T10:30:00+00:00", "Changes needed"), run("2026-10-14T11:00:00+00:00")]
        self.assertFalse(self.first_pass(changes))
        self.assertFalse(self.first_pass([]))

    def test_wait_by_stage(self):
        reviews = [
            run("2026-10-14T10:30:00+00:00", "Changes needed", head="h1"),
            run("2026-10-14T10:45:00+00:00", head="h1"),
            run("2026-10-14T11:00:00+00:00"),
        ]
        p = pr()
        w = row("o/p", p, classify("product", p), reviews)["wait"]
        self.assertEqual(w, {"open > first review": 30, "last Ready > merge": 60})

    def test_unreviewed_has_no_waits(self):
        p = pr()
        r = row("o/p", p, classify("product", p), [])
        self.assertEqual((r["reviewed"], set(r["wait"].values())), (False, {None}))


class CompletedTest(unittest.TestCase):
    def test_only_runs_with_a_verdict_count(self):
        self.assertTrue(completed({"verdict": "Ready to merge", "status": "ok"}))
        self.assertTrue(completed({"verdict": "Changes needed"}))  # records older than status
        self.assertFalse(completed({"verdict": "Ready to merge", "status": "dry-run"}))
        self.assertFalse(completed({"status": "failed"}))


class RevertTest(unittest.TestCase):
    def test_body_and_title_link_the_reverted_pr(self):
        prs = [
            pr(1, title="Add cache"),
            pr(2, title="Fix log"),
            pr(3, title='Revert "Add cache"', mergedAt="2026-10-15T12:00:00Z"),
            pr(4, title="Undo log fix", body="Reverts j-ctang/x#2"),
            pr(5, title='Revert "Fix log"', mergedAt=None),
        ]
        self.assertEqual(reverts("j-ctang/x", prs), {1: 3, 2: 4})

    def test_title_match_needs_one_earlier_merge(self):
        prs = [
            pr(1, title="Fix log", mergedAt="2026-10-10T12:00:00Z"),
            pr(2, title='Revert "Fix log"', mergedAt="2026-10-11T12:00:00Z"),
            pr(3, title="Fix log", mergedAt="2026-10-12T12:00:00Z"),
            pr(4, title='Revert "Fix log"', mergedAt="2026-10-13T12:00:00Z"),
            pr(5, title="Fix log", mergedAt="2026-10-14T12:00:00Z"),
        ]
        # #2 can only mean #1. #4 could mean #1 or #3, so it is skipped, not guessed.
        with mock.patch("builtins.print") as warn:
            self.assertEqual(reverts("j-ctang/x", prs), {1: 2})
        self.assertIn("several PRs", warn.call_args.args[0])

    def test_body_naming_another_repo_is_ignored(self):
        prs = [pr(1), pr(2, title="Undo", body="Reverts j-ctang/other#1")]
        self.assertEqual(reverts("j-ctang/x", prs), {})

    def test_every_same_repo_body_reference_counts(self):
        body = "Reverts j-ctang/other#8\nReverts j-ctang/x#1\nReverts j-ctang/x#2"
        prs = [pr(1), pr(2), pr(3, title="Undo two", body=body)]
        self.assertEqual(reverts("j-ctang/x", prs), {1: 3, 2: 3})

    def test_foreign_body_still_allows_title_match(self):
        prs = [
            pr(1, title="Add cache"),
            pr(
                2,
                title='Revert "Add cache"',
                body="Reverts j-ctang/other#5",
                mergedAt="2026-10-15T12:00:00Z",
            ),
        ]
        self.assertEqual(reverts("j-ctang/x", prs), {1: 2})


class ReportTest(unittest.TestCase):
    def rows(self):
        a = row("o/p", pr(1), classify("product", pr(1)), [run("2026-10-14T11:00:00+00:00")])
        b = row("o/h", pr(2), classify("harness", pr(2)), [])
        c = row(
            "o/p", pr(3, labels=["planted-bug"]), classify("product", pr(3, labels=["planted-bug"])), []
        )
        late = pr(4, mergedAt="2026-10-20T12:00:00Z")
        d = row("o/p", late, classify("product", late), [])
        a["reverted_by"] = 9
        return [a, b, c, d]

    def test_counts_only_the_date_range(self):
        runs = [
            run("2026-10-14T11:00:00+00:00", status="ok", seconds=20),
            run("2026-10-15T11:00:00+00:00", status="failed", seconds=5),
            run("2026-10-09T11:00:00+00:00", status="ok", seconds=30),
        ]
        rep = report(self.rows(), runs, date(2026, 10, 10), date(2026, 10, 15))
        self.assertEqual(rep["merged"], {"product": 1, "harness": 1, "planted": 1})
        self.assertEqual(rep["first_pass"], {"ready": 1, "reviewed": 1, "rate": 1.0})
        self.assertEqual(rep["unreviewed"], ["o/h#2"])
        self.assertEqual(rep["reverts"], ["o/p#1 by #9"])
        self.assertEqual(rep["revert_rate"], 0.5)
        self.assertEqual(rep["review_runs"], {"runs": 2, "failed": 1, "run_seconds": 25})
        self.assertEqual(rep["active_days"], 1)
        self.assertIn("first pass: {'ready': 1, 'reviewed': 1, 'rate': 1.0}", metrics.render(rep))

    def test_empty_range(self):
        rep = report(self.rows(), [], date(2026, 1, 1), date(2026, 1, 2))
        self.assertEqual(
            (rep["merged"], rep["revert_rate"], rep["first_pass"]["rate"]), ({}, None, None)
        )
        metrics.render(rep)


class CollectTest(unittest.TestCase):
    def test_offline_reads_cache_keeps_kinds_and_joins_runs(self):
        with tempfile.TemporaryDirectory() as d:
            cache = Path(d) / "pr-metrics"
            cache.mkdir()
            stored = {"kind": "harness", "rule": "kind label", "mixed": False, "version": 1}
            (cache / "o-p.json").write_text(json.dumps({"prs": [pr(1)], "kinds": {"1": stored}}))
            runs = [
                run("2026-10-14T11:00:00+00:00", status="ok"),
                run("2026-10-14T11:30:00+00:00", status="failed"),
            ]
            with (
                mock.patch.object(metrics, "REPOS", {"o/p": "product"}),
                mock.patch.object(metrics, "cache_dir", return_value=cache),
                mock.patch.object(metrics, "gh_prs") as gh,
            ):
                (r,) = metrics.collect(offline=True, runs=runs)
            gh.assert_not_called()
            self.assertEqual((r["kind"], r["first_pass"]), ("harness", True))
            self.assertEqual(r["wait"]["last Ready > merge"], 60)

    def test_offline_without_cache_fails(self):
        with (
            tempfile.TemporaryDirectory() as d,
            mock.patch.object(metrics, "REPOS", {"o/p": "product"}),
            mock.patch.object(metrics, "cache_dir", return_value=Path(d)),
            self.assertRaisesRegex(ValueError, "no cached PRs"),
        ):
            metrics.collect(offline=True, runs=[])


class GhTest(unittest.TestCase):
    def test_retries_on_error_and_timeout(self):
        fail = mock.Mock(returncode=1, stderr="error connecting to api.github.com", stdout="")
        hang = subprocess.TimeoutExpired("gh", 120)
        ok = mock.Mock(returncode=0, stdout='[{"number": 1}]')
        with (
            mock.patch("subprocess.run", side_effect=[fail, hang, ok]) as sub,
            mock.patch("time.sleep") as sleep,
            mock.patch("builtins.print"),
        ):
            self.assertEqual(metrics.gh_prs("o/p"), [{"number": 1}])
        self.assertEqual(sub.call_args.kwargs["timeout"], 120)
        self.assertNotIn("commits", sub.call_args.args[0][-1])
        self.assertEqual([c.args for c in sleep.call_args_list], [(10,), (10,)])

    def test_full_page_fails_instead_of_cutting_history(self):
        ok = mock.Mock(returncode=0, stdout=json.dumps([{"number": n} for n in range(3)]))
        with (
            mock.patch("subprocess.run", return_value=ok),
            mock.patch.object(metrics, "LIMIT", 3),
            self.assertRaisesRegex(SystemExit, "raise LIMIT"),
        ):
            metrics.gh_prs("o/p")

    def test_gives_up(self):
        fail = mock.Mock(returncode=1, stderr="boom", stdout="")
        with (
            mock.patch("subprocess.run", return_value=fail),
            mock.patch("builtins.print"),
            self.assertRaises(SystemExit),
        ):
            metrics.gh_prs("o/p", tries=2, wait=0)


class LoadRunsTest(unittest.TestCase):
    def test_times_from_record_or_directory_name(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for name, body in (
                ("o-p-1-abc-20261014-120000", '{"pr": 1, "finished_at": "2026-10-14T20:00:00+00:00"}'),
                ("o-p-2-abc-20261013-090000", '{"pr": 2, "seconds": 90}'),
                ("odd", '{"pr": 3}'),
                ("o-p-4-abc-20261012-090000", "{"),
            ):
                (root / name).mkdir()
                (root / name / "run.json").write_text(body)
            with mock.patch("builtins.print"):
                runs = load_runs(root)
        self.assertEqual([r["pr"] for r in runs], [2, 1])
        self.assertEqual(runs[1]["at"].isoformat(), "2026-10-14T20:00:00+00:00")
        # Legacy finish time: directory start time plus the run's seconds.
        self.assertEqual(runs[0]["at"].replace(tzinfo=None), datetime(2026, 10, 13, 9, 1, 30))
        self.assertIsNotNone(runs[0]["at"].tzinfo)


if __name__ == "__main__":
    unittest.main()
