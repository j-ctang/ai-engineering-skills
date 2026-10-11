# HANDOFF

Last updated: 2026-10-10

Start here. Then read `AGENTS.md` (repo rules) and `~/.codex/AGENTS.md`
(global rules for every agent; Claude imports it from `~/.claude/CLAUDE.md`).

## Goal

Build a reusable delivery kit that an agent can apply to a team repo in one
small setup PR: agent instructions, contribution guide, issue/PR templates,
CI, independent review, labels, and release flow. The target repo
`~/dev/claude-code-jev-prune` is the proving ground. Prove each piece on real
changes before turning it into a template.

The eventual flow prepares a verified PR for a human to land:
triage -> implement -> CI -> independent review by the other model ->
bounded fixes -> evidence and labels -> human merge. The reviewer is always
a fresh agent, never the implementer. No unattended loops, no bots, no agent
credentials in GitHub Actions.

## Current state

### jev-prune (target repo)

- CI: required `offline-check` (lint, build, Jest, external network blocked)
  on `staging` and `main`. GitHub-hosted runners only.
- Flow: PRs target `staging`; the human merges; `main` moves only by an
  ancestry-checked fast-forward from `staging`. `main` and `staging` are both
  at `8974f03`.
- Repo has `AGENTS.md`, bug/chore/feature issue templates, and a short PR
  template (issue and risk, Summary, Before/After, Commit History, Sensitive
  Changes, Rollback). Labels `risk:low` and `risk:feature` exist.
- Open issue: #12, intermittent macOS 404 in a shadow proxy test.
- No open PRs. Worktree `/tmp/jev-prune-phase-1-worktree` is detached on an
  old commit; fetch and check out before reuse, or make a fresh worktree.

### This repo (harness)

- `scripts/review_pr.py` + `prompts/review-pr.md` + `prompts/review-schema.json`:
  independent PR review that runs Codex or Claude read-only.
  - `scripts/review_pr.py <codex|claude> <owner/repo> <pr> <clean checkout at PR head> [--dry-run]`
  - The script pins the head commit, saves the diff, picks a tier, fills the
    prompt, runs the model, validates JSON, computes the verdict, and writes
    `/tmp/review/<repo>-<pr>-<sha>-<time>/` (diff, prompt, review.json,
    comment.md, run.json).
  - Severity guard (PR #7): each finding has a `category`
    (`wrong-behavior`, `security`, `weakened-gate`, `unmet-acceptance`,
    `none`). A blocker with `none` becomes should-fix; `run.json` records
    `downgraded`. Known gap: the script trusts the label, so a model can still
    tag a minor finding `wrong-behavior`.
  - Posting is a separate step: `gh pr comment <pr> -R <repo> -F <dir>/comment.md`.
  - Tests: `python3 -m unittest discover -s scripts -p 'test_*.py'`.
- Tiers (merged in #4/#5): S one pass; M per-file; M+ adds a safety pass for CI, agent
  rules, dependencies, test gates, secrets, or deleted tests; L (over 300
  lines or 10 files) is not reviewed and asks for a split. Tests, lockfiles,
  and generated files do not count toward size.
- Notes: `docs/notes/phase-1-lessons.md`, `docs/notes/jev-prune-ci-cd.md`,
  `docs/notes/t3code-delivery-research.md`, `docs/notes/pstack.md`,
  `docs/research/`.
- This repo is public and has no CI or branch protection. Notes and HANDOFF
  go straight to `main`; code goes through PRs.

## What we learned

- Codex review takes 40-50 seconds per PR and finds real bugs (a Claude
  reviewer could write files through `git diff --output`; renames hid risky
  paths; runs overwrote each other).
- Codex inflates severity: 12 of 15 findings were marked blocker, most were
  should-fix by the prompt's own definition.
- Round 2 reviews move the goalposts: new edge cases instead of checking the
  round 1 fixes.
- The size limit caught my own 317-line PR. Counting tests toward size
  punished tests, so tests no longer count.
- Stacked PRs: #4 merged into its base branch, not `main`, because #3 landed
  first. Before merging the base PR, retarget the child to `main`, or turn on
  "Automatically delete head branches" so GitHub retargets it.
- `gh pr view` reports no closing issues for PRs into a non-default branch;
  the script reads `Closes #N` from the body instead.
- In zsh, `$S:r...` is a modifier. Quote as `"${S}:refs/heads/main"`.
- PR #7 was the first harness PR reviewed by `review_pr.py` itself (Codex).
  Round 1 found one valid blocker (an acceptance item had no test); round 2
  passed. Each Codex run took 20-25 seconds.
- Prefer mechanical checks over extra agent passes. Re-running a model to
  judge severity costs quota every review; a script rule costs nothing.

## Next steps

1. Review tool hardening, one PR under 300 lines:
   - Keep the run record when a run fails (status and error).
   - Read CI results for the pinned head commit, not the PR's current head.
   - Parse git output with `-z`; measure size with rename detection on, but
     escalate on both sides of a rename.
2. Scoped re-review, its own PR: round 2+ checks only earlier findings plus
   the diff since the last reviewed commit.
   - Optional, only if inflation persists: a script rule that the category
     fits the check (for example `weakened-gate` only under `tests`).
3. Run the Claude reviewer path end to end on a PR that Codex wrote. It is
   unit-tested and the schema output shape is verified, but no real review
   has run through it yet.
4. Start real work in jev-prune:
   - File the two seed issues with the new templates: discarded
     `usage.input_tokens` blocks cost tracking; a 32-question batch can exceed
     TypeSafe's 64K-token limit. Reproduce before fixing.
   - Start the human's daily pain log (one line per item) as the work source.
   - Run one program of 3-5 small PRs by hand, one at a time, alternating
     which model implements. Review every PR with `review_pr.py` and record
     first-pass acceptance.
5. Later, in order: let the reviewer run tests in a disposable sandbox with
   no network; aggregate `run.json` files into metrics; seeded-bug PRs to
   measure reviewer catch rate after each prompt change; session-replay
   fixtures and a budgeted live canary for jev-prune; then a thin supervisor
   around `claude -p` and `codex exec`.

## Rules the human set this session

- GitHub text (issues, PRs, comments): short, conclusive, first person "I";
  never name the human, Claude, or Codex; "All tests pass" with no counts; no
  internal phase labels; no links to private plans, `/tmp`, or agent
  conversations; never add specs or plans to a PR.
- Before opening or updating a PR, reread every changed Markdown file and fix
  anything later commits made outdated.
- PR format: the repo template wins; otherwise Summary, Before/After, Commit
  History, Sensitive Changes. Commits are short bullets. No AI attribution
  lines anywhere.
- The human prefers our own review tool over vendor `/code-review` commands.
- Two review rounds per PR, then stop and report.
- Budget: Claude Pro + ChatGPT Plus. One implementer and one reviewer at a
  time.

## References

- Design spec: `~/dev/superpowers-docs/ai-engineering-skills/specs/2026-10-07-harness-design.md`.
- Past plans: `~/dev/superpowers-docs/ai-engineering-skills/plans/`.
