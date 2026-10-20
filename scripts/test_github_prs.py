import itertools
import json
import subprocess
import unittest
from unittest import mock

import github_prs
from github_prs import LISTS, flat, gh, rest_of


def conn(nodes, total=None):
    return {"totalCount": len(nodes) if total is None else total, "nodes": nodes}


def node(n=1, **lists):
    out = {
        "number": n,
        "labels": conn([{"name": "risk:low"}]),
        "files": conn([{"path": "a"}]),
        "commits": conn([{"commit": {"committedDate": "2026-10-14T09:00:00Z"}}]),
        "comments": conn([]),
    }
    out.update(lists)
    return out


class GhTest(unittest.TestCase):
    def test_retries_on_error_and_timeout(self):
        fail = mock.Mock(returncode=1, stderr="error connecting to api.github.com", stdout="")
        hang = subprocess.TimeoutExpired("gh", 120)
        ok = mock.Mock(returncode=0, stdout="[1]")
        with (
            mock.patch("subprocess.run", side_effect=[fail, hang, ok]) as run,
            mock.patch("time.sleep") as sleep,
            mock.patch("builtins.print"),
        ):
            self.assertEqual(gh(["api", "x"]), [1])
        self.assertEqual(run.call_args.kwargs["timeout"], 120)
        self.assertEqual([c.args for c in sleep.call_args_list], [(10,), (10,)])

    def test_gives_up(self):
        fail = mock.Mock(returncode=1, stderr="boom", stdout="")
        with (
            mock.patch("subprocess.run", return_value=fail),
            mock.patch("builtins.print"),
            self.assertRaises(SystemExit),
        ):
            gh(["api", "x"], tries=2, wait=0)


class QueryTest(unittest.TestCase):
    def test_query_skips_commit_authors(self):
        # Commit authors multiply the node count past GitHub's 500,000 limit.
        self.assertNotIn("authors", github_prs.QUERY)
        for key in LISTS:
            self.assertIn(
                f"{key}(first: 100) {{ totalCount nodes {{ {LISTS[key]} }} }}", github_prs.QUERY
            )


class FlatTest(unittest.TestCase):
    def test_one_page_is_unwrapped_without_more_calls(self):
        with mock.patch.object(github_prs, "gh") as g:
            pr = flat("o/p", node())
        g.assert_not_called()
        self.assertEqual(pr["labels"], [{"name": "risk:low"}])
        self.assertEqual(pr["commits"], [{"committedDate": "2026-10-14T09:00:00Z"}])
        self.assertEqual(pr["comments"], [])

    def test_every_long_list_is_fetched_in_full(self):
        rest = {
            "labels": [{"name": "a"}, {"name": "b"}],
            "files": [{"path": "a"}, {"path": "src/b.ts"}],
            "commits": [
                {"commit": {"committedDate": d}}
                for d in ("2026-10-14T09:00:00Z", "2026-10-13T09:00:00Z")
            ],
            "comments": [{"author": None, "createdAt": "2026-10-14T10:00:00Z", "body": "x"}],
        }
        long = {k: conn([], total=101) for k in LISTS}
        with mock.patch.object(github_prs, "rest_of", side_effect=lambda repo, n, key: rest[key]) as r:
            pr = flat("o/p", node(**long))
        self.assertEqual({c.args[2] for c in r.call_args_list}, set(LISTS))
        self.assertEqual(pr["files"], rest["files"])
        self.assertEqual(pr["labels"], rest["labels"])
        self.assertEqual([c["committedDate"][8:10] for c in pr["commits"]], ["14", "13"])
        self.assertEqual(pr["comments"], rest["comments"])


class RestOfTest(unittest.TestCase):
    def test_pages_through_one_connection(self):
        def page(nodes):
            return {"data": {"repository": {"pullRequest": {"commits": {"nodes": nodes}}}}}

        pages = [page([{"commit": {"committedDate": "1"}}]), page([{"commit": {"committedDate": "2"}}])]
        with mock.patch.object(github_prs, "gh", return_value=pages) as g:
            got = rest_of("o/p", 7, "commits")
        self.assertEqual([c["commit"]["committedDate"] for c in got], ["1", "2"])
        args = g.call_args.args[0]
        self.assertIn("--paginate", args)
        self.assertIn("number=7", args)
        self.assertIn("name=p", args)
        self.assertIn(
            "commits(first: 100, after: $endCursor)", next(a for a in args if a.startswith("query="))
        )


class GraphqlTest(unittest.TestCase):
    def test_repo_names_stay_strings_and_number_is_typed(self):
        with mock.patch.object(github_prs, "gh", return_value=[]) as g:
            github_prs.graphql("q", "123/true", 7)
        args = g.call_args.args[0]
        pairs = list(itertools.pairwise(args))
        self.assertIn(("-f", "owner=123"), pairs)
        self.assertIn(("-f", "name=true"), pairs)
        self.assertIn(("-F", "number=7"), pairs)
        self.assertNotIn(("-F", "owner=123"), pairs)


class PrsTest(unittest.TestCase):
    def test_reads_every_page_of_prs(self):
        def page(nodes):
            return {"data": {"repository": {"pullRequests": {"nodes": nodes}}}}

        with mock.patch.object(github_prs, "gh", return_value=[page([node(1)]), page([node(2)])]):
            prs = github_prs.prs("o/p")
        self.assertEqual([p["number"] for p in prs], [1, 2])
        json.dumps(prs)  # plain data, safe to cache


if __name__ == "__main__":
    unittest.main()
