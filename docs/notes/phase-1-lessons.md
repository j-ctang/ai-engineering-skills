# Phase 1: what to learn

Phase 1 builds the delivery environment for jev-prune: a way to check changes,
review them, test a candidate locally, and promote the same commit to main.
The important skill is deciding what evidence earns the next step.

## The path we exercised

```text
Claimed issue -> isolated branch -> local checks -> PR to staging
-> hosted offline CI -> independent Claude review -> authorized merge
-> protected branches -> deliberate failed-check proof
-> staging startup/health/shutdown -> authorized fast-forward promotion
-> main CI -> acceptance evidence and handoff
```

### 1. Define completion before implementation

The task was not complete when a workflow file existed. Completion meant the
workflow ran, the suite passed offline, GitHub enforced it, a deliberately
bad PR was blocked, and the tested staging commit reached main unchanged.
Write observable acceptance conditions in the task brief. An agent can then
work toward a measurable stop condition.

### 2. Use several kinds of evidence

- Lint catches configured code-quality violations.
- The TypeScript build checks compilation and types.
- Jest checks the behaviors encoded in the existing tests.
- A smoke check proves the proxy starts, responds to /health, and stops.
- Independent review evaluates concerns outside those automated assertions.

No one item proves the whole product is correct. All 246 tests passing means
the tested scenarios passed; it does not establish full coverage or live API
compatibility. The smoke check used pruning disabled and no API key, so it
does not verify a real pruning request.

### 3. Make checks repeatable and affordable

The lockfile, exact Node version, action SHAs, and container digest limit
uncontrolled changes in the environment. Dependency and image downloads
happen online first. The full check suite then runs without external
networking, while retaining loopback for local HTTP test servers.

This keeps normal PR verification independent of paid TypeSafe calls and
provider availability. Pinned dependencies still require maintained updates;
pinning is not a promise that old versions stay safe forever.

### 4. Test the enforcement mechanism

A visible red check is only a result. A required red check prevents landing.
Disposable PR #14 intentionally violated the existing lint rule. CI failed,
GitHub reported BLOCKED, and the PR was closed without merging. That is
evidence that the gate works. We did not disable or weaken a test.

### 5. Preserve the candidate you tested

Staging is a branch in this project, not a deployed server. We tested its
local proxy and promoted by fast-forward. Equal main/staging commit IDs
establish that main contains the same commit accepted on staging.

Main protection does not automatically enforce staging ancestry. The checked
promotion procedure provides that constraint in Phase 1. Likewise, Claude's
review is attached evidence, not a required GitHub approving-review account.
Those limits must remain visible when landing authority expands.

### 6. Diagnose failures without hiding them

One Mac run returned an intermittent 404 in a shadow proxy test. We recorded
issue #12, preserved the assertions, and kept the investigation separate.
One local Linux run was killed with exit 137 while the Docker VM had very
little available memory; the hosted run passed. A red result requires
investigation of application, test, and environment before choosing a fix.

### 7. Keep changes isolated and reversible

Worktrees protected the user's staged changes. The merged bootstrap changed
two delivery files, with 113 inserted lines. A small focused PR is easier to
understand and revert. If this workflow is removed, its required branch check
also needs an authorized settings change so the branch is not left waiting
for a check that can never run.

### 8. Human attention is a resource

This bootstrap required several pauses for merge authority and staging
acceptance. Before routine work, put the allowed actions, review owner,
manual test, rollback, and stop condition in the brief. Clear authority
reduces repeated clarification while retaining meaningful human decisions.
The user authorized assisted smoke verification and promotion; we should not
describe that as an independently performed manual user test.

## How this relates to high-throughput engineers

xAI's September 2026 engineering guide reports Lauren Tan shipping 2,000+
PRs in a month. It describes bots managing coding agents and maintaining
feedback loops. This is a company-reported example, not an independently
audited benchmark with equivalent PR sizes or budgets. [Source](https://x.ai/bot/guides/grok-bot-for-engineering).

OpenAI reports roughly 1,500 merged PRs and an average of 3.5 PRs per engineer
per day in an agent-first project. Its account describes investment in the
environment and growing pressure on human QA. [Source](https://openai.com/index/harness-engineering/).

Anthropic's compiler experiment used 16 agents and nearly $20,000 in API
costs. It found that workers converging on the same blocker limited
parallelism; better task decomposition and tests enabled progress.
[Source](https://www.anthropic.com/engineering/building-c-compiler).

My interpretation: the transferable advantage is a reliable flow of useful,
independent tasks with cheap verification. Copying a worker count alone
does not reproduce that system.

For this sandbox, measure first-pass acceptance, escaped bugs, reverts,
quota per accepted PR, and human effort. First run a small program of real
tasks sequentially. Then parallelize independent work, measure the result,
and expand low-risk landing authority only after the gates prove useful.

## What comes next

Phase 2 adds the target-repo instructions, issue templates, and risk labels.
Phase 3 supplies real work from the pain log and observed API problems.
Phase 4 exercises one program of 3–5 small PRs. Replay fixtures, a budgeted
live canary, metrics, and more coordination follow.

Phase 1 provides the foundation. Release packaging, publishing, comprehensive
macOS installation checks, and live-provider verification remain later work.
