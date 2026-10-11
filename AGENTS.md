# AGENTS.md

Instructions for any AI coding agent working in this repo.

## Purpose

This repo is a learning sandbox for production-grade, agent-driven software
delivery. The harness (workflow, gates, coordination, verification) is the
prod-level system being built. Agents use it to ship changes to a target repo.

- Primary goal: learning. Basics before big systems. No deadline.
- Target repo: `~/dev/claude-code-jev-prune` (public, TypeScript, Jest).
- The harness lives here. Each target repo gets only its own `AGENTS.md`,
  CI, and verification scripts.

## Principles

- The environment is the product. Agents only use it.
- Quality comes from automated gates. LLM review is an extra signal.
- Reproduce first. No confirmed repro or failing test means no fix.
- Agents never review their own code. The reviewer is the other model.
- Work comes from real signals, never invented by the agent.
- Small PRs: one concern, under ~300 changed lines.
- Every merge must be cheap to roll back.
- Turn repeated mistakes into types, lints, and tests, not more prose.

## Agents and machines

- Implementer and reviewer: Codex CLI (ChatGPT Plus) and Claude Code (Claude
  Pro). Swap roles per task to compare models.
- Quotas are small: 1 implementer + 1 reviewer at a time.
- Agents run locally on the Mac, semi-interactive, in T3 Code threads with one
  git worktree per thread. No unattended loops yet.
- CI runs on GitHub-hosted runners only. Never add a self-hosted runner to a
  public repo. Never put agent credentials in GitHub Actions.
- On a quota limit: stop, write a handoff note in the task file (state, next
  step), and resume after reset.

## Workflow

```
signal -> triage + spec + risk label -> claim
-> repro / failing test (mandatory) -> implement
-> CI gates -> evidence attached to PR
-> AI review by the other model
-> PR targets `staging`:
     low-risk  -> auto-merge after gates and review
     feature   -> human review required
-> human tests `staging` -> fast-forward promote to `main` on a cadence
-> post-merge lessons go into AGENTS.md, lints, or tests
```

- Low-risk: reproduced bug fixes, tests, refactors, lint/type debt,
  dependency patches. Everything else is a feature.
- A broken `staging` is reverted within the hour, never fixed forward.
- `main` only moves by fast-forward from `staging`.
- CI gates run before AI review.

## Work sources

1. The user's daily jev-prune pain log (one line per item).
2. Automated signals: errors, coverage gaps, mutation survivors, lint.
3. Later: an agent that reads Claude Code session logs where jev-prune failed.

## Coordination

Follow the five-step path. Advance only when the current step's exit
condition holds. See `docs/research/08-program-coordination.md`.

1. By hand, sequential: one goal, 3-5 PRs, human writes briefs and merges.
2. By hand, with dependencies: parallel leaves, stacked dependents.
3. Agent monitors CI, conflicts, and stalls. Human schedules and merges.
4. Agent coordinates: writes briefs, runs a canary, starts with 2 workers.
5. Limited landing authority for the low-risk class only.

Every brief has these fields. A missing field blocks dispatch:
`GOAL`, `SCOPE`, `CONTEXT`, `ACCEPTANCE`, `VERIFY`, `TIMEBOX`, `FORBIDDEN`,
`REPORT`.

The orchestrator path: T3 Code for steps 1-2, then a self-built thin
supervisor around `claude -p` and `codex exec --json`. No other third-party
orchestrators.

## Verification (jev-prune)

- Every PR runs offline. Network blocked, dummy keys, injected or stub
  TypeSafe responses.
- Session-replay fixtures act as automated staging.
- A small scheduled live canary checks the real TypeSafe API on a fixed budget.
- Track first-pass acceptance separately from the eventual merge rate.

## Rules for agents

- Claim an issue before starting. Never work on someone else's claim.
- Do not edit protected paths: CI config, test gates, auth, this file.
  Open an issue instead.
- Never weaken, skip, or delete a test to make CI pass.
- Cap fix-forward attempts at two, then report the blocker.
- CodeRabbit comments are low-precision advice (likely under 45%). Verify
  each before acting; never treat one as a blocker alone.
- Run the full local check suite before opening a PR.
- The PR body links the issue and states acceptance criteria and evidence.

## Metrics

First-pass acceptance, eventual merge rate, revert rate, bugs escaped to
staging, quota used per merged PR, time to merge.

## Reference

- `HANDOFF.md`: current state and next steps.
- `docs/research/`: cited research reports (Codex, Oct 2026).
- `docs/notes/pstack.md`: notes on Lauren Tan's public pstack harness.
- Spec: `~/dev/superpowers-docs/ai-engineering-skills/specs/2026-10-07-harness-design.md`.
