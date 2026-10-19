#!/usr/bin/env python3
"""Print PR delivery metrics for a date range.

Usage: scripts/metrics.py [--since YYYY-MM-DD] [--until YYYY-MM-DD] [--offline] [--json]

Reads two records that already exist: GitHub PR timelines (fetched with gh and
cached under ~/.local/state/pr-metrics/) and review run records written by
review_pr.py. Nothing is listed by hand. Each PR gets a kind (product, harness,
ops, planted) from mechanical rules; a kind:<name> label overrides them.
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

REPOS = {"j-ctang/ai-engineering-skills": "harness", "j-ctang/claude-code-jev-prune": "product"}
KINDS = ("product", "harness", "ops", "planted")
# Bump when a rule changes. Merged PRs keep the kind they were first given.
RULES_VERSION = 1
# Product-repo paths that are delivery tooling, not product: CI, templates,
# agent rules, reviewer config. Kept narrow on purpose.
HARNESS_PATHS = re.compile(r"^\.github/|(^|/)(AGENTS|CLAUDE)\.md$|^\.coderabbit\.yaml$")
# Promote (staging into main) and sync (main into staging) carry other PRs.
OPS_BRANCHES = {("main", "staging"), ("staging", "main")}
REVERTS = re.compile(r"\bReverts [\w.-]+/[\w.-]+#(\d+)")
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
        labels(first: 20) { nodes { name } }
        files(first: 100) { nodes { path } }
        commits(first: 100) { nodes { commit { committedDate } } }
        comments(first: 100) { nodes { author { login } createdAt body } }
      }
    }
  }
}
"""
BOTS = re.compile(r"\[bot\]$|^coderabbitai$")


def gh_prs(repo: str, tries: int = 5, wait: float = 10) -> list[dict[str, Any]]:
    """Fetch every PR of a repo. The GitHub API drops out for minutes at a time."""
    owner, name = repo.split("/")
    cmd = ["gh", "api", "graphql", "--paginate", "--slurp", "-f", f"query={QUERY}"]
    cmd += ["-F", f"owner={owner}", "-F", f"name={name}"]
    for attempt in range(1, tries + 1):
        p = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if p.returncode == 0:
            return [
                flat(n)
                for page in json.loads(p.stdout)
                for n in page["data"]["repository"]["pullRequests"]["nodes"]
            ]
        print(f"gh failed for {repo} (try {attempt}/{tries}): {p.stderr.strip()}", file=sys.stderr)
        if attempt < tries:
            time.sleep(wait)
    sys.exit(f"could not fetch PRs for {repo}")


def flat(node: dict[str, Any]) -> dict[str, Any]:
    """Unwrap GraphQL connections into plain lists."""
    pr = dict(node)
    for key in ("labels", "files", "comments"):
        pr[key] = node[key]["nodes"]
    pr["commits"] = [c["commit"] for c in node["commits"]["nodes"]]
    return pr


def t(stamp: str | None) -> datetime | None:
    return datetime.fromisoformat(stamp) if stamp else None


def minutes(a: datetime | None, b: datetime | None) -> float | None:
    return None if a is None or b is None else (b - a).total_seconds() / 60


def classify(role: str, pr: dict[str, Any]) -> dict[str, Any]:
    """Return kind, the rule that matched, and whether a product PR is mixed."""
    labels = {lb["name"] for lb in pr["labels"]}
    paths = [f["path"] for f in pr.get("files") or []]
    harness = [p for p in paths if HARNESS_PATHS.search(p)]
    kind_labels = {lb.split(":", 1)[1] for lb in labels if lb.startswith("kind:")}
    if unknown := kind_labels - set(KINDS):
        raise ValueError(f"PR #{pr['number']}: unknown kind label {sorted(unknown)}")
    if len(kind_labels) > 1:
        raise ValueError(f"PR #{pr['number']}: several kind labels {sorted(kind_labels)}")
    if "planted-bug" in labels:
        if kind_labels - {"planted"}:
            raise ValueError(f"PR #{pr['number']}: planted-bug conflicts with kind:{kind_labels.pop()}")
        kind, rule = "planted", "planted-bug label"
    elif kind_labels:
        kind, rule = kind_labels.pop(), "kind label"
    elif (pr["baseRefName"], pr["headRefName"]) in OPS_BRANCHES:
        kind, rule = "ops", "promote or sync"
    elif role == "harness":
        kind, rule = "harness", "harness repo"
    elif paths and len(harness) == len(paths):
        kind, rule = "harness", "harness paths only"
    else:
        kind, rule = "product", "product repo"
    if (pr.get("changedFiles") or 0) > len(paths) and rule in ("harness paths only", "product repo"):
        rule += " (file list truncated)"
    return {
        "kind": kind,
        "rule": rule,
        "mixed": kind == "product" and bool(harness),
        "version": RULES_VERSION,
    }


def kind_of(kinds: dict[str, Any], role: str, pr: dict[str, Any]) -> dict[str, Any]:
    """Reuse the stored kind of a merged PR, so rule changes do not rewrite history."""
    key = str(pr["number"])
    if pr["mergedAt"] and key in kinds:
        return kinds[key]  # type: ignore[no-any-return]
    k = classify(role, pr)
    if pr["mergedAt"]:
        kinds[key] = k
    return k


def verdicts(pr: dict[str, Any]) -> list[tuple[datetime, bool]]:
    """Posted review verdicts, oldest first, as (time, ready)."""
    out = []
    for c in pr.get("comments") or []:
        if (
            not c["author"]
            or BOTS.search(c["author"]["login"])
            or not c["body"].startswith("**Verdict:**")
        ):
            continue
        ready = c["body"].splitlines()[0].removeprefix("**Verdict:**").strip().startswith("Ready")
        out.append((t(c["createdAt"]), ready))
    return sorted(out)  # type: ignore[arg-type]


def row(repo: str, pr: dict[str, Any], k: dict[str, Any]) -> dict[str, Any]:
    created, merged = t(pr["createdAt"]), t(pr["mergedAt"])
    commits = sorted(t(c["committedDate"]) for c in pr.get("commits") or [])  # type: ignore[type-var]
    v = verdicts(pr)
    first_review = v[0][0] if v else None
    last_ready = max((at for at, ok in v if ok), default=None)
    return {
        "repo": repo,
        "pr": pr["number"],
        "title": pr["title"],
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


def reverts(prs: list[dict[str, Any]]) -> dict[int, int]:
    """Map each reverted PR number to the merged PR that reverted it."""
    by_title = {p["title"]: p["number"] for p in prs}
    out = {}
    for p in prs:
        if not p["mergedAt"]:
            continue
        if m := REVERTS.search(p.get("body") or ""):
            out[int(m.group(1))] = p["number"]
        elif (m := re.fullmatch(r'Revert "(.+)"', p["title"])) and m.group(1) in by_title:
            out[by_title[m.group(1)]] = p["number"]
    return out


def load_runs(root: Path) -> list[dict[str, Any]]:
    runs = []
    for f in sorted(root.glob("*/run.json")):
        try:
            runs.append(json.loads(f.read_text()))
        except (OSError, json.JSONDecodeError):
            print(f"skipping unreadable run record {f}", file=sys.stderr)
    return runs


def median(xs: list[float | None]) -> float | None:
    vals = [x for x in xs if x is not None]
    return round(statistics.median(vals), 1) if vals else None


def report(
    rows: list[dict[str, Any]], runs: list[dict[str, Any]], since: date, until: date
) -> dict[str, Any]:
    def local_day(stamp: str) -> date:
        return datetime.fromisoformat(stamp).astimezone().date()

    merged = [r for r in rows if r["merged"] and since <= local_day(r["merged"]) <= until]
    delivered = [r for r in merged if r["kind"] in ("product", "harness")]
    reviewed = [r for r in delivered if r["reviewed"]]
    reverted = [r for r in delivered if r.get("reverted_by")]
    in_range = {(r["repo"], r["pr"]) for r in merged}
    rr = [x for x in runs if (x.get("repo"), x.get("pr")) in in_range]
    days = {local_day(r["merged"]) for r in merged}
    return {
        "since": since.isoformat(),
        "until": until.isoformat(),
        "merged": dict(Counter(r["kind"] for r in merged)),
        "active_days": len(days),
        "merged_per_active_day": round(len(merged) / len(days), 1) if days else None,
        "lines": {k: sum(r["lines"] for r in merged if r["kind"] == k) for k in KINDS},
        "mixed": [f"{r['repo']}#{r['pr']}" for r in merged if r["mixed"]],
        "first_pass": {"ready": sum(r["first_pass"] for r in reviewed), "reviewed": len(reviewed)},
        "unreviewed": [f"{r['repo']}#{r['pr']}" for r in delivered if not r["reviewed"]],
        "median_wait_min": {s: median([r["wait"][s] for r in delivered]) for s in delivered[0]["wait"]}
        if delivered
        else {},
        "reverts": [f"{r['repo']}#{r['pr']} by #{r['reverted_by']}" for r in reverted],
        "revert_rate": round(len(reverted) / len(delivered), 3) if delivered else None,
        "review_runs": {
            "runs": len(rr),
            "failed": sum(x.get("status") == "failed" for x in rr),
            "model_seconds": sum(x.get("seconds") or 0 for x in rr),
        },
    }


def render(rep: dict[str, Any]) -> str:
    fp = rep["first_pass"]
    lines = [
        f"PR metrics {rep['since']} to {rep['until']}",
        f"merged by kind: {rep['merged'] or 'none'}",
        f"active days: {rep['active_days']}, merged per active day: {rep['merged_per_active_day']}",
        f"lines by kind: {rep['lines']}",
        f"first-pass: {fp['ready']}/{fp['reviewed']} reviewed product and harness PRs",
        f"unreviewed: {', '.join(rep['unreviewed']) or 'none'}",
        f"mixed product PRs: {', '.join(rep['mixed']) or 'none'}",
        "median wait (min): " + ", ".join(f"{k} {v}" for k, v in rep["median_wait_min"].items()),
        f"reverts: {', '.join(rep['reverts']) or 'none'} (rate {rep['revert_rate']})",
        "review runs: {runs}, failed {failed}, model seconds {model_seconds}".format(
            **rep["review_runs"]
        ),
    ]
    return "\n".join(lines)


def cache_dir() -> Path:
    state = os.environ.get("XDG_STATE_HOME") or Path.home() / ".local" / "state"
    return Path(state) / "pr-metrics"


def collect(offline: bool) -> list[dict[str, Any]]:
    """Fetch (or read cached) PRs for every repo, classify them, and save the cache."""
    rows = []
    cache_dir().mkdir(parents=True, exist_ok=True)
    for repo, role in REPOS.items():
        path = cache_dir() / f"{repo.replace('/', '-')}.json"
        cache = json.loads(path.read_text()) if path.exists() else {"prs": [], "kinds": {}}
        if not offline:
            cache["prs"] = gh_prs(repo)
        undone = reverts(cache["prs"])
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
