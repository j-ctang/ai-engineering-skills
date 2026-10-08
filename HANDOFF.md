# HANDOFF

Last updated: 2026-10-07

## How to resume

Open `~/dev/ai-engineering-skills` in T3 Code. Start a new thread and say:
"Read HANDOFF.md and AGENTS.md, then start the next step."

## State

- Planning is done. All decisions are in `AGENTS.md` and the spec:
  `~/dev/superpowers-docs/ai-engineering-skills/specs/2026-10-07-harness-design.md`.
- Research reports (cited, verified by grilling Codex) are in `docs/research/`.
  Lauren Tan's harness notes are in `docs/notes/pstack.md`.
- Nothing has changed in `~/dev/claude-code-jev-prune` yet.

## Facts to remember

- Plans: Claude Pro (no API credits) + ChatGPT Plus. 1 implementer + 1 reviewer.
- jev-prune is public, has no `.github/`, and has no open issues.
- jev-prune calls the TypeSafe API: $0.042 per million input tokens. Its tests
  already inject fake responses, so CI can be offline and free.
- Known jev-prune issues for the seed backlog:
  - The client discards `usage.input_tokens`, so cost is not tracked.
  - A 32-question batch can exceed TypeSafe's 64K-token limit.

## Next steps

1. Write a plan for phase 1 with superpowers:writing-plans. Save it in
   `~/dev/superpowers-docs/ai-engineering-skills/plans/`.
2. Phase 1 in jev-prune: GitHub Actions CI running `npm run check` offline,
   a `staging` branch, branch protection, a PR template with an evidence
   section.
3. Phase 2: target-repo `AGENTS.md`, issue templates, risk labels.
4. Phase 3: file seed issues; start the jev-prune pain log.
5. Phase 4: run the first program by hand (coordination step 1).

## Open items

- Before/after evidence for PRs: the user supplies screenshots or output.
- Verify T3 Code worktree and per-thread PR features before step 2.
