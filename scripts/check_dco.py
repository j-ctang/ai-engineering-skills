#!/usr/bin/env python3
"""Fail if a commit in base..head lacks a Developer Certificate of Origin sign-off.

Usage: scripts/check_dco.py <base> <head> [<checkout-dir>]

Each non-merge commit needs a `Signed-off-by:` trailer with its author's
email; `git commit -s` adds one. Bot commits, such as Dependabot's, are exempt.
"""

import re
import subprocess
import sys
from pathlib import Path

BOT = re.compile(r"\[bot\]@users\.noreply\.github\.com$")


def git(checkout: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=checkout, check=True, capture_output=True, text=True
    ).stdout


def unsigned(checkout: Path, base: str, head: str) -> list[tuple[str, str]]:
    """Return (sha, author email) for each commit without the author's sign-off."""
    missing = []
    for sha in git(checkout, "rev-list", "--no-merges", "--reverse", f"{base}..{head}").split():
        email, trailers = git(
            checkout, "show", "-s", "--format=%ae%x00%(trailers:key=Signed-off-by,valueonly,unfold)", sha
        ).split("\0", 1)
        signers = re.findall(r"<([^>]+)>", trailers)
        if email not in signers and not BOT.search(email):
            missing.append((sha, email))
    return missing


def main() -> None:
    if len(sys.argv) not in (3, 4):
        sys.exit(__doc__)
    checkout = Path(sys.argv[3]) if len(sys.argv) == 4 else Path.cwd()
    missing = unsigned(checkout, sys.argv[1], sys.argv[2])
    for sha, email in missing:
        print(f"{sha[:7]} has no Signed-off-by for its author {email}")
    if missing:
        sys.exit("Sign off each commit with `git commit -s`, then force-push.")
    print("All commits are signed off.")


if __name__ == "__main__":
    main()
