#!/usr/bin/env python3
"""Print PR delivery metrics for a date range.

Usage: scripts/metrics.py [--since YYYY-MM-DD] [--until YYYY-MM-DD] [--offline] [--json]

Reads GitHub PR timelines (cached under ~/.local/state/pr-metrics/) and
review_pr.py run records. Each PR gets a kind from rules, never a hand list.
"""

import argparse
import json
import os
import re
import statistics
import subprocess
import sys
import time
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from typing import Any

from review_pr import runs_root

Row = dict[str, Any]
REPOS = {"j-ctang/ai-engineering-skills": "harness", "j-ctang/claude-code-jev-prune": "product"}
KINDS = ("product", "harness", "ops", "planted")
# Bump when a rule changes. Merged PRs keep the kind they were first given.
RULES_VERSION = 1
# Product-repo paths that are delivery tooling, not product: CI, templates,
# agent rules, reviewer config. Kept narrow on purpose.
HARNESS_PATHS = re.compile(r"^\.github/|(^|/)(AGENTS|CLAUDE)\.md$|^\.coderabbit\.yaml$")
# Promote (staging into main) and sync (main into staging) carry other PRs.
OPS_BRANCHES = {("main", "staging"), ("staging", "main")}
REVERTS = re.compile(r"\bReverts ([\w.-]+/[\w.-]+)#(\d+)")
STAMP = re.compile(r"-(\d{8})-\d{6}$")  # run directory names end in local time
# Only the fields the report needs. gh pr list --json commits also pulls commit
# authors, which pushes the query past GitHub's 500,000-node limit.
QUERY = """
query($owner: String!, $name: String!, $endCursor: String) {
  repository(owner: $owner, name: $name) {
    pullRequests(first: 50, after: $endCursor) {
      pageInfo { hasNextPage endCursor }
      nodes {
        number title body state createdAt mergedAt closedAt baseRefName headRefName
        additions deletions changedFiles
        labels(first: 100) { totalCount nodes { name } }
        files(first: 100) { totalCount nodes { path } }
        first: commits(first: 1) { nodes { commit { committedDate } } }
        last: commits(last: 1) { nodes { commit { committedDate } } }
        comments(first: 100) { totalCount nodes { author { login } createdAt body } }
      }
    }
  }
}
"""
STAGES = ("first commit > open", "open > first review", "last commit > merge", "last Ready > merge")
VERDICT = "**Verdict:**"
BOTS = re.compile(r"\[bot\]$|^coderabbitai$")


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


def gh_prs(repo: str) -> list[Row]:
    owner, name = repo.split("/")
    q = ["api", "graphql", "--paginate", "--slurp", "-f", f"query={QUERY}", "-F", f"owner={owner}"]
    pages = gh([*q, "-F", f"name={name}"])
    return [flat(repo, n) for page in pages for n in page["data"]["repository"]["pullRequests"]["nodes"]]


def flat(repo: str, node: Row) -> Row:
    """Unwrap GraphQL connections. A list longer than one page is fetched in full."""
    pr = dict(node, labels=node["labels"]["nodes"], files=node["files"]["nodes"])
    pr["commits"] = [c["commit"] for c in node["first"]["nodes"] + node["last"]["nodes"]]
    pr["comments"] = node["comments"]["nodes"]
    if node["labels"]["totalCount"] > len(pr["labels"]):
        raise ValueError(f"PR #{node['number']}: more than 100 labels")
    every = ["api", "--paginate", "--slurp"]
    if node["files"]["totalCount"] > len(pr["files"]):
        pages = gh([*every, f"repos/{repo}/pulls/{node['number']}/files"])
        pr["files"] = [{"path": f["filename"]} for page in pages for f in page]
    if node["comments"]["totalCount"] > len(pr["comments"]):
        pages = gh([*every, f"repos/{repo}/issues/{node['number']}/comments"])
        rest = [c for page in pages for c in page]  # REST "user" has a "login" key, like "author"
        pr["comments"] = [
            {"author": c["user"], "createdAt": c["created_at"], "body": c["body"]} for c in rest
        ]
    return pr


def t(stamp: str | None) -> datetime | None:
    return datetime.fromisoformat(stamp) if stamp else None


def minutes(a: datetime | None, b: datetime | None) -> float | None:
    return None if a is None or b is None else (b - a).total_seconds() / 60


def classify(role: str, pr: Row) -> Row:
    """Return kind, the rule that matched, and whether a product PR is mixed."""
    labels = {lb["name"] for lb in pr["labels"]}
    paths = [f["path"] for f in pr.get("files") or []]
    harness = [p for p in paths if HARNESS_PATHS.search(p)]
    kind_labels = {lb.split(":", 1)[1] for lb in labels if lb.startswith("kind:")}
    if "planted-bug" in labels:  # first match wins, so later labels are not checked
        return {"kind": "planted", "rule": "planted-bug label", "mixed": False, "version": RULES_VERSION}
    if unknown := kind_labels - set(KINDS):
        raise ValueError(f"PR #{pr['number']}: unknown kind label {sorted(unknown)}")
    if len(kind_labels) > 1:
        raise ValueError(f"PR #{pr['number']}: several kind labels {sorted(kind_labels)}")
    if kind_labels:
        kind, rule = kind_labels.pop(), "kind label"
    elif (pr["baseRefName"], pr["headRefName"]) in OPS_BRANCHES:
        kind, rule = "ops", "promote or sync"
    elif role == "harness":
        kind, rule = "harness", "harness repo"
    elif paths and len(harness) == len(paths):
        kind, rule = "harness", "harness paths only"
    else:
        kind, rule = "product", "product repo"
    return {
        "kind": kind,
        "rule": rule,
        "mixed": kind == "product" and bool(harness),
        "version": RULES_VERSION,
    }


def kind_of(kinds: Row, role: str, pr: Row) -> Row:
    """Reuse the stored kind of a merged PR, so rule changes do not rewrite history."""
    key = str(pr["number"])
    if pr["mergedAt"] and key in kinds:
        return kinds[key]  # type: ignore[no-any-return]
    k = classify(role, pr)
    if pr["mergedAt"]:
        kinds[key] = k
    return k


def verdicts(pr: Row) -> list[tuple[datetime, bool]]:
    """Posted review verdicts, oldest first, as (time, ready)."""
    out = []
    for c in pr.get("comments") or []:
        if c["author"] and not BOTS.search(c["author"]["login"]) and c["body"].startswith(VERDICT):
            ready = c["body"].splitlines()[0].removeprefix(VERDICT).strip().startswith("Ready")
            out.append((t(c["createdAt"]), ready))
    return sorted(out)  # type: ignore[arg-type]


def row(repo: str, pr: Row, k: Row) -> Row:
    created, merged = t(pr["createdAt"]), t(pr["mergedAt"])
    commits = sorted(t(c["committedDate"]) for c in pr.get("commits") or [])  # type: ignore[type-var]
    v = verdicts(pr)
    first_review = v[0][0] if v else None
    last_ready = max((at for at, ok in v if ok), default=None)
    return {
        "repo": repo,
        "pr": pr["number"],
        **{x: k[x] for x in ("kind", "rule", "mixed")},
        "merged": merged.isoformat() if merged else None,
        "lines": pr["additions"] + pr["deletions"],
        "reviewed": bool(v),
        "first_pass": bool(v) and v[0][1] and not any(c > v[0][0] for c in commits),  # type: ignore[operator]
        "wait": {
            "first commit > open": minutes(commits[0], created) if commits else None,
            "open > first review": minutes(created, first_review),
            "last commit > merge": minutes(commits[-1], merged) if commits else None,
            "last Ready > merge": minutes(last_ready, merged),
        },
    }


def reverts(repo: str, prs: list[Row]) -> dict[int, int]:
    """Map each reverted PR number to the merged PR that reverted it."""
    by_title = {p["title"]: p["number"] for p in prs}
    out = {}
    for p in prs:
        if not p["mergedAt"]:
            continue
        if m := REVERTS.search(p.get("body") or ""):
            if m.group(1).lower() == repo.lower():  # a revert names its repo; others are not ours
                out[int(m.group(2))] = p["number"]
        elif (m := re.fullmatch(r'Revert "(.+)"', p["title"])) and m.group(1) in by_title:
            out[by_title[m.group(1)]] = p["number"]
    return out


def load_runs(root: Path) -> list[Row]:
    runs = []
    for f in sorted(root.glob("*/run.json")):
        try:
            run = json.loads(f.read_text())
            m = STAMP.search(f.parent.name)
            run["day"] = datetime.strptime(m.group(1), "%Y%m%d").date().isoformat() if m else None
            runs.append(run)
        except (OSError, json.JSONDecodeError):
            print(f"skipping unreadable run record {f}", file=sys.stderr)
    return runs


def median(xs: list[float | None]) -> float | None:
    vals = [x for x in xs if x is not None]
    return round(statistics.median(vals), 1) if vals else None


def report(rows: list[Row], runs: list[Row], since: date, until: date) -> Row:
    def local_day(stamp: str) -> date:
        return datetime.fromisoformat(stamp).astimezone().date()

    merged = [r for r in rows if r["merged"] and since <= local_day(r["merged"]) <= until]
    delivered = [r for r in merged if r["kind"] in ("product", "harness")]
    reviewed = [r for r in delivered if r["reviewed"]]
    reverted = [r for r in delivered if r.get("reverted_by")]
    # Runs count by the day they ran, not by when their PR merged.
    rr = [x for x in runs if x.get("day") and since <= date.fromisoformat(x["day"]) <= until]
    days = {local_day(r["merged"]) for r in merged}
    return {
        "range": f"{since} to {until}",
        "merged": dict(Counter(r["kind"] for r in merged)),
        "active_days": len(days),
        "merged_per_active_day": round(len(merged) / len(days), 1) if days else None,
        "lines": {k: sum(r["lines"] for r in merged if r["kind"] == k) for k in KINDS},
        "mixed": [f"{r['repo']}#{r['pr']}" for r in merged if r["mixed"]],
        "first_pass": {
            "ready": (ready := sum(r["first_pass"] for r in reviewed)),
            "reviewed": len(reviewed),
            "rate": round(ready / len(reviewed), 2) if reviewed else None,
        },
        "unreviewed": [f"{r['repo']}#{r['pr']}" for r in delivered if not r["reviewed"]],
        "median_wait_min": {s: median([r["wait"][s] for r in delivered]) for s in STAGES},
        "reverts": [f"{r['repo']}#{r['pr']} by #{r['reverted_by']}" for r in reverted],
        "revert_rate": round(len(reverted) / len(delivered), 3) if delivered else None,
        "review_runs": {
            "runs": len(rr),
            "failed": sum(x.get("status") == "failed" for x in rr),
            "model_seconds": sum(x.get("seconds") or 0 for x in rr),
        },
    }


def render(rep: Row) -> str:
    return "\n".join(f"{k.replace('_', ' ')}: {v}" for k, v in rep.items())


def cache_dir() -> Path:
    state = os.environ.get("XDG_STATE_HOME") or Path.home() / ".local" / "state"
    return Path(state) / "pr-metrics"


def collect(offline: bool) -> list[Row]:
    """Fetch (or read cached) PRs for every repo, classify them, and save the cache."""
    rows = []
    cache_dir().mkdir(parents=True, exist_ok=True)
    for repo, role in REPOS.items():
        path = cache_dir() / f"{repo.replace('/', '-')}.json"
        cache = json.loads(path.read_text()) if path.exists() else {"prs": [], "kinds": {}}
        if not offline:
            cache["prs"] = gh_prs(repo)
        undone = reverts(repo, cache["prs"])
        for pr in cache["prs"]:
            r = row(repo, pr, kind_of(cache["kinds"], role, pr))
            r["reverted_by"] = undone.get(pr["number"])
            rows.append(r)
        path.write_text(json.dumps(cache))
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--since", type=date.fromisoformat, default=date(2000, 1, 1))
    ap.add_argument("--until", type=date.fromisoformat, default=date.today())
    ap.add_argument("--offline", action="store_true", help="use the cached PRs, do not call gh")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    try:
        rows = collect(args.offline)
    except ValueError as e:
        sys.exit(str(e))
    rep = report(rows, load_runs(runs_root()), args.since, args.until)
    print(json.dumps(rep, indent=2) if args.json else render(rep))


if __name__ == "__main__":
    main()
