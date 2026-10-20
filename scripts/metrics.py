#!/usr/bin/env python3
"""Print PR delivery metrics for a date range.

Usage: scripts/metrics.py [--since YYYY-MM-DD] [--until YYYY-MM-DD] [--offline] [--json]

Review events come from review_pr.py's own run records. PR facts come from one
gh pr list call per repo, cached under ~/.local/state/pr-metrics/. Each PR gets
a kind from rules, never from a hand-written list.
"""

import argparse
import json
import os
import re
import statistics
import subprocess
import sys
import time
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
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
STAMP = re.compile(r"-(\d{8}-\d{6})$")  # run directory names end in local time
# No commits or comments: review events come from run records, and the size
# gate keeps reviewed PRs far below the 100-file page limit.
FIELDS = (
    "number,title,body,createdAt,mergedAt,baseRefName,headRefName,headRefOid,"
    "labels,additions,deletions,changedFiles,files"
)
STAGES = ("open > first review", "last Ready > merge")
LIMIT = 1000  # gh pr list returns the newest first; a full page means older PRs were cut


def gh_prs(repo: str, tries: int = 5, wait: float = 10) -> list[Row]:
    """Every PR of a repo. The GitHub API drops out or hangs for minutes at a time."""
    cmd = ["gh", "pr", "list", "-R", repo, "--state", "all", "--limit", str(LIMIT), "--json", FIELDS]
    for attempt in range(1, tries + 1):
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=120)
            if p.returncode == 0:
                prs: list[Row] = json.loads(p.stdout)
                if len(prs) >= LIMIT:
                    sys.exit(f"{repo} has {LIMIT}+ PRs; raise LIMIT so older PRs are not cut")
                return prs
            err = p.stderr.strip()
        except subprocess.TimeoutExpired:
            err = "timed out after 120 s"
        print(f"gh failed for {repo} (try {attempt}/{tries}): {err}", file=sys.stderr)
        if attempt < tries:
            time.sleep(wait)
    sys.exit(f"could not fetch PRs for {repo}")


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
    elif (pr.get("changedFiles") or 0) > len(paths):
        # Only the path rule needs every file. The review size gate keeps PRs far below the cap.
        raise ValueError(f"PR #{pr['number']}: file list truncated; classify it with a kind: label")
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


def row(repo: str, pr: Row, k: Row, reviews: list[Row]) -> Row:
    """One PR's numbers. reviews are its completed review runs, oldest first."""
    created, merged = t(pr["createdAt"]), t(pr["mergedAt"])
    ready = [r for r in reviews if r["verdict"].startswith("Ready")]
    first = reviews[0] if reviews else None
    return {
        "repo": repo,
        "pr": pr["number"],
        **{x: k[x] for x in ("kind", "rule", "mixed")},
        "merged": merged.isoformat() if merged else None,
        "lines": pr["additions"] + pr["deletions"],
        "reviewed": bool(reviews),
        # Ready on the first review, and nothing pushed after the head it reviewed.
        "first_pass": bool(first and first in ready and first["head"] == pr["headRefOid"]),
        "wait": {
            "open > first review": minutes(created, first["at"]) if first else None,
            "last Ready > merge": minutes(ready[-1]["at"], merged) if ready else None,
        },
    }


def reverts(repo: str, prs: list[Row]) -> dict[int, int]:
    """Map each reverted PR number to the merged PR that reverted it."""
    by_title = {p["title"]: p["number"] for p in prs}
    out = {}
    for p in prs:
        if not p["mergedAt"]:
            continue
        m = REVERTS.search(p.get("body") or "")
        if m and m.group(1).lower() == repo.lower():  # a revert names its repo; others are not ours
            out[int(m.group(2))] = p["number"]
        elif (m := re.fullmatch(r'Revert "(.+)"', p["title"])) and m.group(1) in by_title:
            out[by_title[m.group(1)]] = p["number"]
    return out


def load_runs(root: Path) -> list[Row]:
    """Run records with an aware finish time. Old records lack finished_at; their
    directory name holds the start time in local time, plus the run's seconds."""
    runs = []
    for f in sorted(root.glob("*/run.json")):
        try:
            run = json.loads(f.read_text())
        except (OSError, json.JSONDecodeError):
            print(f"skipping unreadable run record {f}", file=sys.stderr)
            continue
        if at := run.get("finished_at"):
            run["at"] = datetime.fromisoformat(at)
        elif m := STAMP.search(f.parent.name):
            started = datetime.strptime(m.group(1), "%Y%m%d-%H%M%S").astimezone()
            run["at"] = started + timedelta(seconds=run.get("seconds") or 0)
        else:
            continue
        runs.append(run)
    return sorted(runs, key=lambda r: r["at"])


def completed(run: Row) -> bool:
    """A review that reached a verdict. Failed and dry runs did not."""
    return bool(run.get("verdict")) and run.get("status") in (None, "ok")


def median(xs: list[float | None]) -> float | None:
    vals = [x for x in xs if x is not None]
    return round(statistics.median(vals), 1) if vals else None


def report(rows: list[Row], runs: list[Row], since: date, until: date) -> Row:
    def local_day(at: datetime) -> date:
        return at.astimezone().date()

    merged = [r for r in rows if r["merged"] and since <= local_day(t(r["merged"])) <= until]  # type: ignore[arg-type]
    delivered = [r for r in merged if r["kind"] in ("product", "harness")]
    reviewed = [r for r in delivered if r["reviewed"]]
    reverted = [r for r in delivered if r.get("reverted_by")]
    # Runs count by the day they ran, not by when their PR merged.
    rr = [x for x in runs if since <= local_day(x["at"]) <= until]
    days = {local_day(t(r["merged"])) for r in merged}  # type: ignore[arg-type]
    ready = sum(r["first_pass"] for r in reviewed)
    return {
        "range": f"{since} to {until}",
        "merged": dict(Counter(r["kind"] for r in merged)),
        "active_days": len(days),
        "merged_per_active_day": round(len(merged) / len(days), 1) if days else None,
        "lines": {k: sum(r["lines"] for r in merged if r["kind"] == k) for k in KINDS},
        "mixed": [f"{r['repo']}#{r['pr']}" for r in merged if r["mixed"]],
        "first_pass": {
            "ready": ready,
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


def collect(offline: bool, runs: list[Row]) -> list[Row]:
    """Fetch (or read cached) PRs for every repo, classify them, and save the cache."""
    by_pr = defaultdict(list)
    for run in filter(completed, runs):
        by_pr[(run["repo"], run["pr"])].append(run)
    rows = []
    cache_dir().mkdir(parents=True, exist_ok=True)
    for repo, role in REPOS.items():
        path = cache_dir() / f"{repo.replace('/', '-')}.json"
        if offline and not path.exists():
            raise ValueError(f"no cached PRs for {repo}; run once without --offline")
        cache = json.loads(path.read_text()) if path.exists() else {"prs": [], "kinds": {}}
        if not offline:
            cache["prs"] = gh_prs(repo)
        undone = reverts(repo, cache["prs"])
        for pr in cache["prs"]:
            r = row(repo, pr, kind_of(cache["kinds"], role, pr), by_pr[(repo, pr["number"])])
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
    runs = load_runs(runs_root())
    try:
        rows = collect(args.offline, runs)
    except ValueError as e:
        sys.exit(str(e))
    rep = report(rows, runs, args.since, args.until)
    print(json.dumps(rep, indent=2) if args.json else render(rep))


if __name__ == "__main__":
    main()
