"""Fetch every PR of a GitHub repo with the fields delivery metrics need.

Each list on a PR (labels, files, commits, comments) is fetched in full, so no
metric is computed from a truncated page.
"""

import json
import subprocess
import sys
import time
from typing import Any

Row = dict[str, Any]
# Fields read from each item in a PR's lists. Commit authors are left out on
# purpose: gh pr list --json commits pulls them, which multiplies the query
# past GitHub's 500,000-node limit.
LISTS = {
    "labels": "name",
    "files": "path",
    "commits": "commit { committedDate }",
    "comments": "author { login } createdAt body",
}
FIELDS = " ".join(f"{k}(first: 100) {{ totalCount nodes {{ {v} }} }}" for k, v in LISTS.items())
QUERY = f"""
query($owner: String!, $name: String!, $endCursor: String) {{
  repository(owner: $owner, name: $name) {{
    pullRequests(first: 50, after: $endCursor) {{
      pageInfo {{ hasNextPage endCursor }}
      nodes {{
        number title body state createdAt mergedAt closedAt baseRefName headRefName
        additions deletions changedFiles {FIELDS}
      }}
    }}
  }}
}}
"""


def gh(args: list[str], tries: int = 5, wait: float = 10) -> Any:
    """Run gh and parse its JSON. The GitHub API drops out or hangs for minutes at a time."""
    for attempt in range(1, tries + 1):
        try:
            p = subprocess.run(["gh", *args], capture_output=True, text=True, check=False, timeout=120)
            if p.returncode == 0:
                return json.loads(p.stdout)
            err = p.stderr.strip()
        except subprocess.TimeoutExpired:
            err = "timed out after 120 s"
        print(f"gh {' '.join(args[:2])} failed (try {attempt}/{tries}): {err}", file=sys.stderr)
        if attempt < tries:
            time.sleep(wait)
    sys.exit(f"gh {' '.join(args[:2])} failed {tries} times")


def graphql(query: str, repo: str, *variables: str) -> Any:
    owner, name = repo.split("/")
    args = ["api", "graphql", "--paginate", "--slurp", "-f", f"query={query}"]
    for v in (f"owner={owner}", f"name={name}", *variables):
        args += ["-F", v]
    return gh(args)


def rest_of(repo: str, number: int, key: str) -> list[Row]:
    """Every item of one list on one PR, page by page."""
    query = (
        "query($owner: String!, $name: String!, $number: Int!, $endCursor: String) {"
        " repository(owner: $owner, name: $name) { pullRequest(number: $number) {"
        f" {key}(first: 100, after: $endCursor) {{ pageInfo {{ hasNextPage endCursor }}"
        f" nodes {{ {LISTS[key]} }} }} }} }} }}"
    )
    pages = graphql(query, repo, f"number={number}")
    return [n for page in pages for n in page["data"]["repository"]["pullRequest"][key]["nodes"]]


def flat(repo: str, node: Row) -> Row:
    """Unwrap a PR's lists into plain lists, fetching any list longer than one page."""
    pr = dict(node)
    for key in LISTS:
        page = node[key]
        full = page["totalCount"] <= len(page["nodes"])
        pr[key] = page["nodes"] if full else rest_of(repo, node["number"], key)
    pr["commits"] = [c["commit"] for c in pr["commits"]]
    return pr


def prs(repo: str) -> list[Row]:
    """Every PR of the repo, in any state."""
    pages = graphql(QUERY, repo)
    return [flat(repo, n) for page in pages for n in page["data"]["repository"]["pullRequests"]["nodes"]]
