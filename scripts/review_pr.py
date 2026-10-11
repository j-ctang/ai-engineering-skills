#!/usr/bin/env python3
"""Run an independent, read-only PR review with Codex or Claude.

Usage: scripts/review_pr.py <codex|claude> <owner/repo> <pr> <checkout-dir>
       [--dry-run]

The script decides everything that can be decided mechanically: the pinned
commit, the output shape, and the verdict. The model only
reports findings. Output goes to /tmp/review-<pr>/: prompt.md, review.json,
comment.md, and run.json. Posting the comment is a separate, deliberate step:
gh pr comment <pr> -R <repo> -F /tmp/review-<pr>/comment.md
"""

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
PROMPT = HERE / "prompts" / "review-pr.md"
SCHEMA = HERE / "prompts" / "review-schema.json"

MAX_NITS = 3


def sh(*args, cwd=None):
    return subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True).stdout


def gh_json(*args):
    return json.loads(sh("gh", *args))


def validate(review):
    """Reject output that breaks rules the schema cannot express."""
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


def render(verdict, review):
    out = [f"**Verdict:** {verdict}", ""]
    findings = sorted(
        review["findings"],
        key=lambda f: ["blocker", "should-fix", "nit"].index(f["severity"]),
    )
    if not findings:
        out.append("No blocking findings.")
    for f in findings:
        out.append(f"- **{f['severity']}** `{f['path']}:{f['line']}`: {f['problem']} {f['fix']}")
    if review["follow_ups"]:
        out += ["", "Follow-ups (outside this PR):"]
        out += [f"- {item}" for item in review["follow_ups"]]
    return "\n".join(out) + "\n"


def run_reviewer(reviewer, checkout, prompt, out):
    if reviewer == "codex":
        with open(out / "log.txt", "w") as log:
            subprocess.run(
                ["codex", "exec", "-C", str(checkout), "-s", "read-only", "--ephemeral",
                 "--output-schema", str(SCHEMA), "-o", str(out / "raw.txt"), "-"],
                input=prompt, text=True, stdout=log, stderr=log, check=True,
            )
        return json.loads((out / "raw.txt").read_text())
    result = subprocess.run(
        ["claude", "-p", "--output-format", "json",
         "--json-schema", SCHEMA.read_text(),
         "--disallowedTools", "Edit,Write,NotebookEdit",
         "--allowedTools", "Read,Grep,Glob,Bash(git diff:*),Bash(git show:*),Bash(git log:*)"],
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

    out = Path(f"/tmp/review-{args.pr}")
    out.mkdir(exist_ok=True)
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
    base = sh("git", "merge-base", f"origin/{pr['baseRefName']}", head, cwd=args.checkout).strip()

    if not sh("git", "diff", "--name-only", f"{base}..{head}", cwd=args.checkout).strip():
        sys.exit(f"PR #{args.pr} has an empty diff against {pr['baseRefName']}")

    run = {
        "reviewer": args.reviewer, "repo": args.repo, "pr": args.pr, "head": head,
        "prompt_version": sh("git", "rev-parse", "--short", "HEAD", cwd=HERE).strip(),
    }

    # gh exits non-zero while checks are pending or failing, or if none exist.
    result = subprocess.run(["gh", "pr", "checks", str(args.pr), "-R", args.repo,
                             "--json", "name,state"], capture_output=True, text=True)
    checks = json.loads(result.stdout) if result.stdout.strip() else []
    values = {
        "REPO": args.repo, "PR": str(args.pr), "BASE_SHA": base, "HEAD_SHA": head,
        "CI_RESULT": ", ".join(f"{c['name']}: {c['state']}" for c in checks) or "none",
        "ISSUE_BODY": sh("gh", "issue", "view", str(issue), "-R", args.repo,
                         "--json", "body", "--jq", ".body").strip(),
        "PR_BODY": pr["body"].strip(),
    }
    prompt = PROMPT.read_text()
    for key, value in values.items():
        prompt = prompt.replace("{{" + key + "}}", value)
    (out / "prompt.md").write_text(prompt)
    if args.dry_run:
        print(json.dumps(run, indent=2))
        return

    started = time.time()
    review = validate(run_reviewer(args.reviewer, args.checkout, prompt, out))
    run["seconds"] = round(time.time() - started)
    blockers = any(f["severity"] == "blocker" for f in review["findings"])
    verdict = "Changes needed" if blockers else "Ready to merge"
    comment = render(verdict, review)

    run["verdict"] = verdict
    run["findings"] = {s: sum(f["severity"] == s for f in review["findings"])
                       for s in ("blocker", "should-fix", "nit")}
    (out / "review.json").write_text(json.dumps(review, indent=2))
    (out / "comment.md").write_text(comment)
    (out / "run.json").write_text(json.dumps(run, indent=2))
    print(out / "comment.md")


if __name__ == "__main__":
    main()
