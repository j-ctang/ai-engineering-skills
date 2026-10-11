# HANDOFF

Last updated: 2026-10-10

## End goal and latest direction

The user wants a reusable delivery kit that Codex or Claude can apply to a team
repository through a small setup PR: agent instructions, human contribution guide,
intake/PR templates, stack-appropriate CI, review, labels, and release workflow.
Jev-prune is the first proving ground. Prove the workflow on real changes before
extracting portable templates; preserve destination conventions and checks.

Desired eventual automation prepares a verified PR for final human review:
triage -> implement -> CI -> fresh independent review -> bounded fixes/rechecks
-> evidence and labels -> human landing. User explicitly requires a new reviewer
separate from the implementer on every change. This direction does not authorize
unattended loops, protected-file edits, installing bots, or Phase 2 merges.

## State

Phase 1 is complete. The user authorized the bootstrap CI edit, merge,
assisted smoke verification, and promotion. No independent manual user smoke
result is claimed; the startup/health/shutdown verification was agent-assisted.

- Bootstrap PR #13 merged: https://github.com/j-ctang/claude-code-jev-prune/pull/13.
- Main and staging both point to `1052057818660523fca4bea98404677000d41d10`.
  Main moved by ancestry-checked fast-forward with no force push/new commit.
- Final main CI passed: https://github.com/j-ctang/claude-code-jev-prune/actions/runs/37903557293.
  Lint, build, 29 Jest suites and 246 tests passed with external networking
  disabled; isolation probe demonstrated loopback works and external TCP fails.
- CI uses GitHub-hosted Ubuntu, Node 22.23.3, SHA-pinned actions, a digest-pinned
  Node image, read-only repository permission, no retained checkout credentials,
  and a dummy TypeSafe key. Dependency/image downloads occur before isolation.
- Claude Code independently reviewed the CI diff after green CI; no blocking
  findings. Review evidence is attached to #13.
- Both branches require `offline-check` from GitHub Actions, including admins,
  and block force pushes/deletion. Staging requires PRs. Main allows checked
  fast-forward promotion. Policy readback evidence is on issue #11.
- Disposable PR #14 failed its intentional lint check and had GitHub merge
  state BLOCKED. It was closed without merge; remote branch deleted.
  https://github.com/j-ctang/claude-code-jev-prune/pull/14.
- Fresh local full suite passed. Fresh staging smoke returned HTTP 200/status=ok,
  with API/pruning disabled, then shut down cleanly with exit 0.
- Assisted proxy on port 5599 was no longer running when resumed; fresh smoke
  used a temporary port and stopped its owned process. No test proxy left running.
- Original target checkout's staged doc deletions were preserved. Isolated
  worktree `/tmp/jev-prune-phase-1-worktree` is clean on
  `chore/phase-2-task-intake` at `d5e8a93` (reused for Phase 2).
  Temporary local evidence is under `/tmp/jev-prune-phase-1-evidence/`; important
  acceptance evidence is also attached to the GitHub issues/PRs.

## Limits and remaining signals

- Current CI runs lint, TypeScript compilation, and Jest; it does not measure or
  enforce coverage. No CONTRIBUTING.md exists in the target. The Phase 2 issue
  templates and target AGENTS.md remain unmerged in PR #16.
- Offline verification allows local fake HTTP servers while blocking external
  networking during checks. Dependency/image downloads happen beforehand.
- Main protection does not mechanically enforce staging ancestry; the checked
  human-controlled promotion procedure provides that constraint in Phase 1.
- AI review is evidence, not a GitHub required approving-review account. Staging
  has zero required GitHub approving reviews; authorization remains procedural.
- Smoke verified startup/health/shutdown, not live API pruning. Release packaging,
  publishing, macOS install coverage, replay fixtures and a live canary remain later.
- Issue #12 remains open for an intermittent Mac shadow-test 404. Tests were
  not weakened or skipped: https://github.com/j-ctang/claude-code-jev-prune/issues/12.
- Local Linux full check once exited 137 under a 2GB Docker VM with little free
  memory. Existing services were preserved; hosted offline checks passed.
- T3 PR linking verified. Native worktree UI flow still not verified; Git fallback used.
- Seed signals: discarded `usage.input_tokens` prevents cost tracking; a 32-question
  batch can exceed TypeSafe's 64K-token limit. Reproduce before fixing.

## Next steps

0. 2026-10-10: PR #16 merged by the user; main fast-forwarded to `795c01c`;
   main CI green; #15 closed; old branch deleted. Shared global agent rules now
   live in `~/.codex/AGENTS.md` (imported by `~/.claude/CLAUDE.md`). PR #18
   (issue #17, `risk:feature`) shortens the PR template and adds GitHub
   writing rules to target AGENTS.md (user authorized). Offline-check passed.
   Next: Codex review of #18, human merge, promote, then Phase 3.
1. (Done) Phase 2 implemented: issue #15, branch `chore/phase-2-task-intake` in
   `/tmp/jev-prune-phase-1-worktree`, commit `d5e8a93`. User authorized target
   AGENTS.md creation exactly as drafted; other protected paths remain protected.
   Four approved files add 154 lines; two risk labels created and read back.
   Baseline and final full checks passed 29 suites/246 tests. PR #16 targets staging:
   https://github.com/j-ctang/claude-code-jev-prune/pull/16.
   Hosted offline-check passed 29 suites/246 tests; independent Claude static
   review found no blockers and marked ready for human landing. Review/evidence:
   https://github.com/j-ctang/claude-code-jev-prune/pull/16#issuecomment-6077897618.
   Human merge, staging acceptance, promotion, and default-branch chooser checks
   remain pending; no Phase 2 landing authority has been delegated. Evidence: `/tmp/jev-prune-phase-2-evidence/`.
   Plan: `~/dev/superpowers-docs/ai-engineering-skills/plans/2026-10-09-phase-2-task-intake.md`.
2. Phase 3: file seed issues and start the user's daily jev-prune pain log.
3. Phase 4: one real program of 3–5 small PRs, by hand and sequentially.
4. Later: replay fixtures, budgeted live canary, metrics, dependency-aware
   coordination, then a thin supervisor and limited low-risk landing authority.

Phase 2 implementation was authorized by the user; do not advance into Phase 3 yet.
Budget remains Claude Pro + ChatGPT Plus, one implementer and one reviewer.
No unattended loops, agent credentials in Actions, or public self-hosted runners.

## T3 Code research and proposed kit improvements

See `docs/notes/t3code-delivery-research.md` for sources and concrete PR examples.
Observed size/vouch labeling, CodeRabbit and Macroscope review, detailed CI and
change-specific evidence. A review/fix/recheck example was verified; fully unattended
looping was not established. Current contribution policy has no universal size
cutoff: one underlying problem, approved direction when needed, and adequate proof.
Do not infer contributor acceptance rates from the small qualitative sample.

Proposals only: CONTRIBUTING.md, required-field issue forms, metadata label
automation, and one hosted reviewer. Keep changes separate and small; never reduce
useful tests to earn a smaller size label. Risk labels do not confer authority.
GitHub Actions label automation can be free; path labels do not establish low risk.
CodeRabbit public-repo reviews are a candidate; small repos require manual triggers.
No bot installed or CI changed. Recheck vendor terms before adoption. Team/private
repository access, costs, and ownership must be considered during adaptation.

## References

- Phase 1 plan: `~/dev/superpowers-docs/ai-engineering-skills/plans/2026-10-08-phase-1-foundation.md`.
- Design: `~/dev/superpowers-docs/ai-engineering-skills/specs/2026-10-07-harness-design.md`.
- Learning summary: `docs/notes/phase-1-lessons.md`.
- CI/CD explanation: `docs/notes/jev-prune-ci-cd.md`.
- Research: `docs/research/`, `docs/notes/pstack.md`, and
  `docs/notes/t3code-delivery-research.md`.

Phase 2 review lesson: validate substantive brief answers, not retained template
placeholders; confirm triage even when a feature template supplies its risk label.
