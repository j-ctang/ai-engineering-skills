#!/usr/bin/env python3
"""Run an independent, read-only PR review with Codex or Claude.

Usage: scripts/review_pr.py <codex|claude> <owner/repo> <pr> <checkout-dir>
       [--dry-run]

The script decides everything that can be decided mechanically: the pinned
commit, the review tier, the output shape, and the verdict. The model only
reports findings. Each run gets its own directory under /tmp/review/ with
diff.patch, prompt.md, review.json, comment.md, and run.json. Posting the
comment is a separate, deliberate step:
gh pr comment <pr> -R <repo> -F <run-dir>/comment.md
"""

import argparse
import json
import re
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
PROMPT = HERE / "prompts" / "review-pr.md"
SCHEMA = HERE / "prompts" / "review-schema.json"

# Files that do not count toward review size.
IGNORED = re.compile(
    r"(^|/)(package-lock\.json|yarn\.lock|pnpm-lock\.yaml|[^/]+\.lock)$"
    r"|(^|/)(dist|build|coverage)/|\.min\.js$|\.snap$"
)
# Tests do not count toward size either, so a PR never drops tests to fit.
TEST = re.compile(r"(^|/)(test|tests|__tests__)/|(^|/)test_[^/]+$|\.(test|spec)\.[^/]+$")

# Paths that raise the tier, whatever the size.
ESCALATIONS = {
    "ci": r"^\.github/workflows/",
    "agent-rules": r"(^|/)(AGENTS|CLAUDE)\.md$",
    "dependencies": r"(^|/)(package\.json|package-lock\.json|yarn\.lock|pnpm-lock\.yaml|[^/]+\.lock)$",
    "test-gates": (r"(^|/)(jest\.config\.[^/]+|\.eslintrc[^/]*|eslint\.config\.[^/]+"
                   r"|tsconfig[^/]*\.json|scripts/(check|verify)[^/]*)$"),
    "secrets": r"(auth|credential|secret|token|\.env)",
}

SMALL_LINES, SMALL_FILES = 50, 3
MEDIUM_LINES, MEDIUM_FILES = 300, 10
MAX_NITS = 3
CHECKS = {"scope", "acceptance", "correctness", "tests", "safety", "docs", "pr_hygiene"}
SEVERITIES = ["blocker", "should-fix", "nit"]
# A blocker must name one of these reasons, or the script downgrades it.
CATEGORIES = {"wrong-behavior", "security", "weakened-gate", "unmet-acceptance", "none"}
FIELDS = {"check", "severity", "category", "path", "line", "problem", "failure_scenario", "fix"}

TIER_INSTRUCTIONS = {
    "S": "Small diff. Read the whole diff in one pass, then work through the checks.",
    "M": (
        "Medium diff. Review one file at a time. For each changed source file, "
        "read its tests and its callers before judging correctness."
    ),
    "M+": (
        "Medium diff with risky paths ({escalations}). Review one file at a "
        "time, read tests and callers, then do a separate safety pass over the "
        "risky paths: secrets, permissions, network access, dependency pinning, "
        "and any weakened check or gate."
    ),
}


def sh(*args, cwd=None):
    return subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True).stdout


def gh_json(*args):
    return json.loads(sh("gh", *args))


def parse_numstat(raw):
    """Parse `git diff -z -M --numstat` into (added, removed, paths) rows.

    A rename lists both paths, source first, so both sides can escalate.
    """
    rows, tokens = [], iter(raw.split("\0"))
    for token in tokens:
        if not token:
            continue
        added, removed, path = token.split("\t", 2)
        paths = (path,) if path else (next(tokens), next(tokens))
        rows.append((added, removed, paths))
    return rows


def parse_deleted(raw):
    """Parse `git diff -z -M --name-status --diff-filter=DR` into removed paths.

    A rename counts as a deletion of its source when it moves a test out of
    the test paths, so a test cannot vanish by being renamed.
    """
    removed, tokens = [], iter(raw.split("\0"))
    for status in tokens:
        if status.startswith("D"):
            removed.append(next(tokens))
        elif status.startswith("R"):
            source, dest = next(tokens), next(tokens)
            if not TEST.search(dest):
                removed.append(source)
    return removed


def diff_stats(checkout, base, head):
    """Return (rows, deleted) for base..head, read with -z so paths stay unquoted."""
    span = f"{base}..{head}"
    rows = parse_numstat(sh("git", "diff", "-z", "-M", "--numstat", span, cwd=checkout))
    deleted = parse_deleted(sh("git", "diff", "-z", "-M", "--name-status",
                               "--diff-filter=DR", span, cwd=checkout))
    return rows, deleted


def classify(rows, deleted):
    """Return (tier, lines, files, escalations) for parse_numstat rows.

    Size uses the destination path; escalation checks every path.
    """
    lines = files = 0
    paths = []
    for added, removed, names in rows:
        paths += names
        if IGNORED.search(names[-1]) or TEST.search(names[-1]):
            continue
        files += 1
        if added != "-":
            lines += int(added) + int(removed)
    hits = sorted(
        name for name, pattern in ESCALATIONS.items()
        if any(re.search(pattern, p, re.I) for p in paths)
    )
    if any(TEST.search(p) for p in deleted):
        hits.append("deleted-tests")
    if lines > MEDIUM_LINES or files > MEDIUM_FILES:
        return "L", lines, files, hits
    if lines <= SMALL_LINES and files <= SMALL_FILES and not hits:
        return "S", lines, files, hits
    return ("M+" if hits else "M"), lines, files, hits


def validate(review):
    """Reject output that breaks the schema or rules it cannot express."""
    if set(review) != {"checks", "findings", "follow_ups"} or set(review["checks"]) != CHECKS:
        raise ValueError("review does not match the schema")
    if any(s not in ("pass", "fail", "n/a") for s in review["checks"].values()):
        raise ValueError("check status must be pass, fail, or n/a")
    for f in review["findings"]:
        if (set(f) != FIELDS or f["check"] not in CHECKS
                or f["severity"] not in SEVERITIES or f["category"] not in CATEGORIES
                or not isinstance(f["line"], int)):
            raise ValueError(f"finding does not match the schema: {f}")
    blocked = {f["check"] for f in review["findings"] if f["severity"] == "blocker"}
    for check, status in review["checks"].items():
        if (status == "fail") != (check in blocked):
            raise ValueError(f"check {check} is {status} but blocker findings say otherwise")
    kept, nits = [], 0
    for f in review["findings"]:
        nits += f["severity"] == "nit"
        if f["severity"] != "nit" or nits <= MAX_NITS:
            kept.append(f)
    review["findings"] = kept
    return review


def downgrade(review):
    """Turn blockers with no blocking reason into should-fix. Return the count.

    A check stays failed only while it still has a blocker.
    """
    count = 0
    for f in review["findings"]:
        if f["severity"] == "blocker" and f["category"] == "none":
            f["severity"] = "should-fix"
            count += 1
    blocked = {f["check"] for f in review["findings"] if f["severity"] == "blocker"}
    for check, status in review["checks"].items():
        if status == "fail" and check not in blocked:
            review["checks"][check] = "pass"
    return count


def render(verdict, tier, escalations, review):
    out = [f"**Verdict:** {verdict}", ""]
    label = tier + (f" ({', '.join(escalations)})" if escalations else "")
    out += [f"Review tier: {label}", ""]
    findings = sorted(
        review["findings"],
        key=lambda f: SEVERITIES.index(f["severity"]),
    )
    if not findings:
        out.append("No blocking findings.")
    for f in findings:
        out.append(f"- **{f['severity']}** `{f['path']}:{f['line']}`: {f['problem']} {f['fix']}")
    if review["follow_ups"]:
        out += ["", "Follow-ups (outside this PR):"]
        out += [f"- {item}" for item in review["follow_ups"]]
    return "\n".join(out) + "\n"


def conclude(review, tier, escalations, run):
    """Apply downgrades, fill the run record, and return the comment."""
    run["downgraded"] = downgrade(review)
    blockers = any(f["severity"] == "blocker" for f in review["findings"])
    run["verdict"] = "Changes needed" if blockers else "Ready to merge"
    run["findings"] = {s: sum(f["severity"] == s for f in review["findings"])
                       for s in SEVERITIES}
    return render(run["verdict"], tier, escalations, review)


def format_checks(runs, statuses):
    """Summarize check runs and commit statuses as "name: result"."""
    results = [f"{r['name']}: {r['conclusion'] or r['status']}" for r in runs]
    results += [f"{st['context']}: {st['state']}" for st in statuses]
    return ", ".join(results) or "none"


def ci_result(repo, head):
    """Read CI for the pinned head, not whatever the PR points at now."""
    def pages(path, key):
        out = sh("gh", "api", "--paginate", f"repos/{repo}/commits/{head}/{path}",
                 "--jq", f".{key}[]")
        return [json.loads(line) for line in out.splitlines()]
    return format_checks(pages("check-runs", "check_runs"), pages("status", "statuses"))


@contextmanager
def recorded(out, run):
    """Write run.json when the block ends, with the error if it failed."""
    started = time.time()
    try:
        yield
        run.setdefault("status", "ok")
    except BaseException as e:
        run.update(status="failed", error=f"{type(e).__name__}: {e}"[:500])
        raise
    finally:
        run["seconds"] = round(time.time() - started)
        (out / "run.json").write_text(json.dumps(run, indent=2))


def run_reviewer(reviewer, checkout, prompt, out):
    if reviewer == "codex":
        with open(out / "log.txt", "w") as log:
            subprocess.run(
                ["codex", "exec", "-C", str(checkout), "-s", "read-only", "--ephemeral",
                 "--output-schema", str(SCHEMA), "-o", str(out / "raw.txt"), "-"],
                input=prompt, text=True, stdout=log, stderr=log, check=True,
            )
        return json.loads((out / "raw.txt").read_text())
    # Claude has no OS sandbox here, so it gets no shell. It reads the saved
    # diff and repo files only.
    result = subprocess.run(
        ["claude", "-p", "--output-format", "json",
         "--json-schema", SCHEMA.read_text(), "--add-dir", str(out),
         "--disallowedTools", "Bash,Edit,Write,NotebookEdit",
         "--allowedTools", "Read,Grep,Glob"],
        cwd=checkout, input=prompt, text=True, capture_output=True, check=True,
    )
    (out / "raw.txt").write_text(result.stdout)
    wrapper = json.loads(result.stdout)
    return wrapper.get("structured_output") or json.loads(wrapper["result"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("reviewer", choices=["codex", "claude"])
    ap.add_argument("repo")
    ap.add_argument("pr", type=int)
    ap.add_argument("checkout", type=Path)
    ap.add_argument("--dry-run", action="store_true", help="stop after writing the prompt")
    args = ap.parse_args()

    pr = gh_json("pr", "view", str(args.pr), "-R", args.repo,
                 "--json", "state,body,baseRefName,headRefOid,closingIssuesReferences")
    if pr["state"] != "OPEN":
        sys.exit(f"PR #{args.pr} is {pr['state'].lower()}, not open")
    head = pr["headRefOid"]

    # GitHub only links closing issues for PRs into the default branch, so
    # fall back to the "Closes #N" line for PRs into staging.
    refs = pr["closingIssuesReferences"]
    match = re.search(r"^closes #(\d+)", pr["body"], re.I | re.M)
    issue = refs[0]["number"] if refs else match and int(match.group(1))
    if not issue:
        sys.exit(f"PR #{args.pr} does not close an issue")

    sh("git", "fetch", "-q", "origin", pr["baseRefName"], head, cwd=args.checkout)
    if sh("git", "rev-parse", "HEAD", cwd=args.checkout).strip() != head:
        sys.exit(f"{args.checkout} is not checked out at PR head {head}")
    if sh("git", "status", "--porcelain", cwd=args.checkout).strip():
        sys.exit(f"{args.checkout} has uncommitted changes")
    base = sh("git", "merge-base", f"origin/{pr['baseRefName']}", head, cwd=args.checkout).strip()

    diff = sh("git", "diff", f"{base}..{head}", cwd=args.checkout)
    if not diff.strip():
        sys.exit(f"PR #{args.pr} has an empty diff against {pr['baseRefName']}")

    # One directory per run, so reruns and other repos never overwrite a record.
    stamp = time.strftime("%Y%m%d-%H%M%S")
    out = Path("/tmp/review") / f"{args.repo.replace('/', '-')}-{args.pr}-{head[:7]}-{stamp}"
    out.mkdir(parents=True)
    (out / "diff.patch").write_text(diff)

    tier, lines, files, escalations = classify(*diff_stats(args.checkout, base, head))

    run = {
        "reviewer": args.reviewer, "repo": args.repo, "pr": args.pr, "head": head,
        "prompt_version": sh("git", "rev-parse", "--short", "HEAD", cwd=HERE).strip(),
        "tier": tier, "lines": lines, "files": files, "escalations": escalations,
    }
    if args.dry_run:
        print(json.dumps(run, indent=2))
        run["status"] = "dry-run"
    with recorded(out, run):
        finish(args, pr, issue, base, head, out, run)


def finish(args, pr, issue, base, head, out, run):
    """Write the prompt, run the model, and write the comment."""
    tier, escalations = run["tier"], run["escalations"]
    if tier == "L":
        if args.dry_run:
            return
        verdict = "Changes needed"
        run.update(verdict=verdict, findings={})
        (out / "comment.md").write_text(
            f"**Verdict:** {verdict}\n\nToo large to review: {run['lines']} changed lines in "
            f"{run['files']} files. Split into PRs of at most {MEDIUM_LINES} lines and "
            f"{MEDIUM_FILES} files. Tests, lockfiles, and generated files do not count.\n"
        )
        print(out / "comment.md")
        return

    values = {
        "REPO": args.repo, "PR": str(args.pr), "BASE_SHA": base, "HEAD_SHA": head,
        "DIFF_PATH": str(out / "diff.patch"), "TIER": tier,
        "TIER_INSTRUCTIONS": TIER_INSTRUCTIONS[tier].format(escalations=", ".join(escalations)),
        "CI_RESULT": ci_result(args.repo, head),
        "ISSUE_BODY": sh("gh", "issue", "view", str(issue), "-R", args.repo,
                         "--json", "body", "--jq", ".body").strip(),
        "PR_BODY": pr["body"].strip(),
    }
    prompt = PROMPT.read_text()
    for key, value in values.items():
        prompt = prompt.replace("{{" + key + "}}", value)
    (out / "prompt.md").write_text(prompt)
    if args.dry_run:
        return

    review = validate(run_reviewer(args.reviewer, args.checkout, prompt, out))
    comment = conclude(review, tier, escalations, run)
    (out / "review.json").write_text(json.dumps(review, indent=2))
    (out / "comment.md").write_text(comment)
    print(out / "comment.md")


if __name__ == "__main__":
    main()
