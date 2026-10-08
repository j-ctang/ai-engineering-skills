**VERIFIED** means the linked primary source explicitly documents the claim; it does **not** mean I independently reproduced its results. **UNVERIFIED** marks inference, recommendations, or claims without independent evidence. Sources checked October 7, 2026; GitHub `main` links can change.

**The main finding:** separate planning, implementation, verification, and landing authority. The strongest practical pattern is a durable program record, narrow worker briefs, one pilot through the complete workflow, bounded fan-out, and verification tied to the reviewed revision.

1. **pstack: four distinct workflows**

| Workflow | VERIFIED behavior | Human approval and exact source excerpt |
|---|---|---|
| **Orchestrate** | Standing coordinator owns briefs, scheduling, completion queue, decisions, and merge frontier; never writes code. Decomposition is project-specific tracks and verifiable units. Pilot one unit through implementation, verification, integration, and merge before fan-out; then use a rolling window. One writer per branch; one stacker per stack. | Escalates irreversible actions, unresolved product choices, contradictory standing orders, and program dead ends. Routine retries and stack mechanics proceed autonomously. Exact line: **“A dependency is a context relay, not just ordering.”** [Upstream, lines 10–87](https://raw.githubusercontent.com/cursor/plugins/main/pstack/skills/poteto-mode/playbooks/orchestrate.md) |
| **Autopilot-full** | One owner per independent PR handles implementation, proof, CI, review triage, and readiness. Root owns independent verification. Independent PRs branch from trunk; dependencies normally use merge-then-branch, with a short private stack exception. | **Upstream allows owner merges** under full-autonomy authorization plus root verdict; operator-designated items remain manual. Exact line: **“Operator-named items stop at merge-ready and wait for the operator's click.”** [Upstream, lines 10–18](https://raw.githubusercontent.com/cursor/plugins/main/pstack/skills/poteto-mode/playbooks/autopilot-full.md) |
| **Autopilot-stack** | Owners build independently where possible; root alone writes topology. Deliver one linear parent-base chain. Rebase bottom-up, rerun CI and mergeability, and reassess verdict validity after rewrites. This playbook explicitly avoids `gt`. | Operator reviews and lands the chain. Exact line: **“No owner merges, arms auto-merge, or closes.”** [Upstream, lines 10–16](https://raw.githubusercontent.com/cursor/plugins/main/pstack/skills/poteto-mode/playbooks/autopilot-stack.md) |
| **Multi-phase-plan** | Produces a plan, not implementation: one section per PR with dependencies, files, build checklist, observable outcome, unit/live/performance evidence, and review gate. A script validates the plan. Dependents wait for parent merge or branch from the parent in stacking mode. | Explicit go starts execution; interaction changes require human review with screenshots/video. Exact line: **“Execution starts on the operator's explicit go, under the execution playbook the plan names.”** [Upstream, lines 10–46](https://raw.githubusercontent.com/cursor/plugins/main/pstack/skills/poteto-mode/playbooks/multi-phase-plan.md) |

**VERIFIED — brief and durable state.** Orchestrate’s brief fields are `GOAL`, `SCOPE`, `CONTEXT`, `ACCEPTANCE`, `VERIFY`, `TIMEBOX`, `FORBIDDEN`, `REPORT`, and `STANDING`. Missing fields block dispatch; upstream reports travel into downstream briefs. Durable records include standing orders, unit table, inbox, decisions, gates, computed frontier, and verification ledger. Verdicts are keyed to PR and head SHA; changed heads require renewed verification. [Orchestrate, lines 18–47 and 71–76](https://raw.githubusercontent.com/cursor/plugins/main/pstack/skills/poteto-mode/playbooks/orchestrate.md)

**VERIFIED — the Claude port is a policy fork, not merely translated syntax.**

- Orchestrate uses background agents and separate worktrees rather than Cursor cloud workers; its persistent store lives outside the session. [Port Orchestrate, lines 12–24](https://raw.githubusercontent.com/michael-denyer/pstack-claude/main/plugins/pstack/skills/poteto-mode/playbooks/orchestrate.md)
- Autopilot-full requires **every merge to be human-clicked**. Exact line: **“No owner runs the merge itself.”** It also caps fix-forwards at two; unresolved blockers return to the operator. [Port Autopilot-full, lines 18–22](https://raw.githubusercontent.com/michael-denyer/pstack-claude/main/plugins/pstack/skills/poteto-mode/playbooks/autopilot-full.md)
- Autopilot-stack adds explicit cancellation of auto-merge and queue membership before affected-chain rewrites, plus captured-SHA leases. [Port Autopilot-stack, lines 11–16](https://raw.githubusercontent.com/michael-denyer/pstack-claude/main/plugins/pstack/skills/poteto-mode/playbooks/autopilot-stack.md)
- The port’s plan skeleton says: **“The operator reviews before merge.”** Upstream distinguishes interaction-changing PRs from non-review-gated ones. [Port plan, line 107](https://raw.githubusercontent.com/michael-denyer/pstack-claude/main/plugins/pstack/skills/poteto-mode/playbooks/multi-phase-plan.md)

2. **Sourcegraph Agentic Batch Changes**

**VERIFIED.** Coordinator researches repositories and proposes scope, per-repository changes, branch/title/commit metadata, and a canary repository. Approval starts the one-repository execution; inspect its diff, optionally publish a draft for CI, then expand in paused stages. Exact sentence: **“When you trust the change, ‘run everything else’ fans out the remainder.”** The source uses straight quotation marks around that command. The agent can remediate CI/conflicts when configured, but cannot merge from the conversation. [Workflow documentation](https://sourcegraph.com/docs/agentic-batch-changes)

**VERIFIED.** Approval boundaries can be authorized upfront; execution, publication, expansion, and full fan-out otherwise may require replies. New or changed secret-using steps require approval. Deterministic edits can use scripts; context-sensitive work can delegate to Claude Code or Codex. Work runs in isolated per-repository containers. [Configuration and approvals](https://sourcegraph.com/docs/agentic-batch-changes/configuration)

**UNVERIFIED — inference:** this is closest to repeatable migration rollout across repositories; the cited workflow does not establish a general scheduler for arbitrarily dependent stacked PRs.

3. **Cursor planner/worker/judge experiments**

**VERIFIED — January experiment.** Flat self-coordination through shared state and locks caused waiting, stale locks, brittle updates, and avoidance of difficult work. Recursive planners created tasks; workers implemented without coordinating with siblings; a judge decided whether another cycle should run, followed by a fresh iteration. Exact line: **“No agent took responsibility for hard problems or end-to-end implementation.”** Workers pushed to a shared branch, so this was not a demonstrated multi-PR review workflow. [Scaling agents, lines 38–59](https://cursor.com/blog/scaling-agents)

**VERIFIED — July revision.** Planners retain design decisions; workers execute narrower instructions. Shared design documents address contradictory designs; neutral agents resolve merge conflicts; multiple review perspectives catch different errors. Exact line: **“In a swarm, a planner never implements”**. The article identifies split-brain design, planner contention, merge conflicts, megafiles, and ossification. It argues that detailed frontier-model planning can enable cheaper workers. [Agent-swarm model economics](https://prod.cursor.com/blog/agent-swarm-model-economics)

**VERIFIED — changed finding:** January removed an integrator bottleneck; July introduced neutral conflict resolution. These are different experimental configurations, not a universal rule against integration roles. [January](https://cursor.com/blog/scaling-agents), [July](https://prod.cursor.com/blog/agent-swarm-model-economics)

**UNVERIFIED:** production readiness and transfer of reported swarm economics to a solo developer’s PR program. Cursor itself describes the browser as a proof of concept that fell short of polished software.

4. **Anthropic task locks and Lingxi Li’s fleet guide**

**VERIFIED — Anthropic.** Each agent has an isolated container/clone. A committed file under `current_tasks/` claims work; Git synchronization rejects duplicate claims. Agents pull, merge, push, and remove locks, then restart fresh. Exact sentence: **“I don’t use an orchestration agent.”** The kernel build initially defeated parallelism because everyone hit the same blocker; a GCC oracle partitioned failures into independently diagnosable subsets. Regression gates, concise logs, progress documents, and test sampling supported autonomy. [C-compiler experiment, lines 51–79](https://www.anthropic.com/engineering/building-c-compiler)

**VERIFIED — fleet guide.** Domain-specific bots launch coding agents with expected proof, inspect transcripts/artifacts, and send corrective follow-ups. A shared Notion PR database survives context limits; bots check every 30 minutes for findings, CI failures, and conflicts. Exact sentence: **“If the review is highly confident and the blast radius is low, the PR is merged automatically.”** Otherwise the human reviews proof and decides. Postmortems update shared playbooks. [Grok Bot for Engineering](https://x.ai/bot/guides/grok-bot-for-engineering)

**UNVERIFIED:** independently audited fleet productivity, review accuracy, or bug escape rates. The guide is a practitioner account; fleet size and PR counts alone do not establish safety.

5. **Stacked-PR tools**

**VERIFIED:** these tools manage branch/PR topology; coordinating a program still requires scope, scheduling, evidence, and approval policy.

| Tool | Documented mechanics | Short exact excerpt |
|---|---|---|
| **Graphite** | `gt create`, `gt submit --stack`, `gt modify`, `gt restack`, `gt sync`; modifying a lower layer updates branches above. | **“automatically restack all the branches above it”**. [Quick start](https://graphite.com/docs/cli-quick-start) |
| **GitHub `gh stack`** | Official `github/gh-stack` extension: init/add/submit/sync; parent-base PRs, linked stacks, agent skill. Native stacked PRs are public preview. | **“Each PR's base is set to the branch below it in the stack”**. [Repository](https://github.com/github/gh-stack), [preview documentation](https://docs.github.com/en/pull-requests/get-started/stacked-prs-quickstart) |
| **git-spice** | Tracks branch relationships locally; restacks dependent branches; submits stacks and retargets children after merges; supports several forges. | **“It works with Git instead of trying to replace Git.”** [Documentation](https://abhinav.github.io/git-spice/) |

6. **Concrete solo-dev learning path**

**UNVERIFIED — proposed synthesis**, informed by the workflows above. Start with a real ranked-backlog goal, claim its issues, and preserve your repository’s protected-path and independent-review rules.

| Step | What you coordinate | Artifact and advancement condition |
|---|---|---|
| **1. By hand, sequentially** | One goal → 3–5 small PRs; you write briefs, dispatch one worker, inspect evidence, and merge. | `program.md`, one brief per PR, dependency graph, evidence ledger. Finish one complete program with rollback documented. |
| **2. By hand, with dependencies** | Independent leaves run concurrently; dependent PRs wait or stack. You alone restack. | Unit table with owner, dependencies, branch/base/head, PR, state; decision log. Demonstrate a lower-layer change without accepting stale verification. |
| **3. Delegate monitoring** | Agent checks CI, conflicts, review findings, stalled workers, and receipts; you retain scheduling and merges. | Durable inbox, scheduled audit, bounded retry policy, status generated from records. Every worker is accounted for after restart. |
| **4. Delegate coordination** | Agent proposes decomposition and briefs, runs a canary, dispatches ready units, relays dependency context, and aggregates evidence. | Approved program contract, machine-readable graph, standing orders, verification ledger, human-gate queue. Begin with two workers. |
| **5. Grant limited landing authority** | Coordinator may land only an explicitly authorized class of small, reversible changes after independent review and automated gates. | Merge policy, staging smoke evidence, rollback command, escape/revert/cost metrics. Expand only when measured outcomes justify it. |

Use these minimal artifacts:

```text
PROGRAM
Goal + linked claimed issues:
Done predicate:
In scope / excluded / protected paths:
PR units + acceptance criteria:
Dependency graph + shared interface decisions:
Worker cap / cost budget / deadline:
Verification + independent reviewer:
Canary + expansion rule:
Who may publish / restack / merge:
Rollback:
Stop conditions:
```

```text
BRIEF
Goal:
Allowed paths + exclusive branch/worktree:
Dependencies: exact parent revision + upstream report/contracts
Acceptance:
Exact verification commands + required receipts:
Timebox + forbidden actions:
Report: status, PR, base/head SHA, evidence, deviations, blockers
Standing orders:
```

```text
GRAPH
A: shared contract
B: consumer one    depends_on: [A]
C: consumer two    depends_on: [A]
D: remove legacy  depends_on: [B, C]

Readiness requires dependency evidence and compatible revisions.
B and C may run together only with separate write ownership.
```

**UNVERIFIED — proposed canary rule:** complete one representative unit through worker → independent review → full checks → merge → staging smoke → rollback check before expanding. Use another canary for a materially different unit shape. Expand concurrency from one to two, then four only if coordination and verification remain reliable.

**UNVERIFIED — proposed stop conditions:** stop new dispatch on invalid upstream contracts, failing canary, unavailable required verification, protected-path requests, exhausted budget, or repeated infrastructure failure. Block a PR after two unsuccessful fix-forwards. Any head/base change invalidates readiness until evidence is checked against the new context. Preserve state and reconcile late workers before accepting their output.

**Failure modes that recur most often**

**UNVERIFIED — qualitative ranking; the sources provide no comparable frequency dataset.**

1. **Overlapping ownership and incompatible designs:** duplicate effort, shared-file collisions, contradictory interfaces. Appears in both Cursor reports and Anthropic. [Cursor January](https://cursor.com/blog/scaling-agents), [Cursor July](https://prod.cursor.com/blog/agent-swarm-model-economics), [Anthropic](https://www.anthropic.com/engineering/building-c-compiler)
2. **Weak proof and regressions:** green checks or confident summaries substitute for demonstrated behavior. Addressed by pstack receipts, Anthropic verifier design, and the fleet feedback loop. [pstack](https://raw.githubusercontent.com/cursor/plugins/main/pstack/skills/poteto-mode/playbooks/orchestrate.md), [Anthropic](https://www.anthropic.com/engineering/building-c-compiler), [fleet guide](https://x.ai/bot/guides/grok-bot-for-engineering)
3. **Context loss, drift, and stalled work:** missing directives, dead workers, repeated orientation, uncontrolled retries. Addressed through durable state, fresh briefs, observable progress, and audits. [pstack](https://raw.githubusercontent.com/michael-denyer/pstack-claude/main/plugins/pstack/skills/poteto-mode/playbooks/orchestrate.md), [fleet guide](https://x.ai/bot/guides/grok-bot-for-engineering)
4. **Coordination becoming the bottleneck:** coarse locks, blocking batches, excessive hierarchy, integration deferred until the end. [Cursor January](https://cursor.com/blog/scaling-agents), [Orchestrate](https://raw.githubusercontent.com/cursor/plugins/main/pstack/skills/poteto-mode/playbooks/orchestrate.md)