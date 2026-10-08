# Study notes: pstack and its Claude Code / Codex port

## Scope and reading conventions

These notes cover the upstream guide’s ten chapters, all 23 upstream playbooks, and the port’s runtime adaptations, autonomy policies, orchestration state, and merge safeguards.

Sources were retrieved from the repositories’ mutable `main` branches. Links identify the files studied; they are not commit-pinned snapshots.

- **Upstream** means [Cursor’s pstack](https://github.com/cursor/plugins/tree/main/pstack).
- **Port** means [michael-denyer/pstack-claude](https://github.com/michael-denyer/pstack-claude).
- **Inferred** identifies a synthesis for building a smaller harness, rather than a documented pstack requirement.

The workspace is read-only, so the Markdown is delivered here rather than saved to a file.

## 1. Overview

pstack is an opinionated collection of agent instructions, workflow playbooks, supporting scripts, and reviewer roles. Its main entry point, `poteto-mode`, matches a request to a workflow and invokes supporting skills as needed. Its stated aim is less code with stronger verification. [Upstream README](https://github.com/cursor/plugins/blob/main/pstack/README.md)

The intended user input is a goal, a checkable completion condition, useful evidence, and constraints. The agent supplies the workflow.

> “Give the agent a goal and a way to check it”  
> — [Guide introduction](https://github.com/cursor/plugins/blob/main/pstack/docs/guide/README.md)

The port shares a skills tree across runtimes, translates tools and model configuration, and adds named policy forks. It is therefore more than a mechanical translation. [Port README](https://github.com/michael-denyer/pstack-claude/blob/main/README.md)

**Inferred minimal architecture:** separate the workflow instructions from runtime adapters and durable state:

```text
Request + constraints
        ↓
Workflow router
        ↓
Playbook + visible checklist
        ↓
Scoped work in an isolated checkout
        ↓
Executable verification + evidence
        ↓
Independent review when required
        ↓
PR / handoff / authorized landing
```

This synthesis combines the routing guide, build playbooks, and shipping rules. [Routing](https://github.com/cursor/plugins/blob/main/pstack/docs/guide/02-poteto-mode.md), [Shipping](https://github.com/cursor/plugins/blob/main/pstack/skills/poteto-mode/playbooks/shipping.md)

## 2. Core concepts and vocabulary

| Term | Meaning in the docs |
|---|---|
| **Skill** | A reusable instruction file, usually `SKILL.md`, for a particular activity or principle. |
| **Mode / router** | `poteto-mode` selects a playbook and applies cross-cutting triggers. |
| **Playbook** | Ordered steps, verification requirements, and a reporting contract for a task class. |
| **Principle** | A named rule that changes a specific decision; applying one requires reading its leaf skill. |
| **Done predicate** | A condition an agent can check, rather than a duration or subjective aspiration. |
| **Throughput checkpoint** | Blocking prerequisites, independent workstreams, shared mutable state, and the smallest safe decomposition. |
| **Owner** | The role accountable for a change; the role can continue through fresh agent instances. |
| **Arena** | Multiple attempts at the same brief, followed by judging, base selection, and grafting useful parts. |
| **Swarm** | Parallel coverage of different slices or declared race arms, followed by aggregation. |
| **Interrogate** | Adversarial review of a diff by different models; findings are triaged rather than automatically applied. |
| **Merge frontier** | The lowest unmerged PR currently governing progress through a stack. |
| **Verified ceiling** | The first gap above the contiguous verified run rooted at the bottom. |
| **Receipt** | Inspectable evidence of a run, such as output, screenshot, trace, or stored value. |
| **Standing orders** | Durable constraints carried into worker briefs and resumes. |
| **Verification ledger** | Recorded verdicts associated with a PR and revision. |

Sources: [Mode rules](https://github.com/cursor/plugins/blob/main/pstack/skills/poteto-mode/SKILL.md), [Design guide](https://github.com/cursor/plugins/blob/main/pstack/docs/guide/04-design.md), [Feature](https://github.com/cursor/plugins/blob/main/pstack/skills/poteto-mode/playbooks/feature.md), [Orchestrate](https://github.com/cursor/plugins/blob/main/pstack/skills/poteto-mode/playbooks/orchestrate.md).

### The principle vocabulary

The guide groups 24 principles into five families:

- **Core:** Laziness Protocol; Foundational Thinking; Redesign from First Principles; Attack the Premise; Subtract Before You Add; Minimize Reader Load; Outcome-Oriented Execution; Experience First; Exhaust the Design Space; Build the Lever.
- **Architecture:** Model the Domain; Boundary Discipline; Type System Discipline; Make Operations Idempotent; Migrate Callers Then Delete Legacy APIs; Separate Before Serializing Shared State.
- **Verification:** Prove It Works; Fix Root Causes; Sequence Work into Verifiable Units; Test Behavior, Not Implementation; Explain the Number.
- **Delegation:** Guard the Context Window; Never Block on the Human.
- **Meta:** Encode Lessons in Structure.

Names serve as steering vocabulary. A meaningful application identifies the decision changed by the principle. [Chapter 8](https://github.com/cursor/plugins/blob/main/pstack/docs/guide/08-principles.md)

## 3. Each guide chapter summarized

| Chapter | Main lesson |
|---|---|
| [1. Setup](https://github.com/cursor/plugins/blob/main/pstack/docs/guide/01-setup.md) | Install, configure models by role and reasoning budget, and start with a small real task. Setup offers a project verification skill when none exists. Panel size and reasoning settings affect cost. `auto` and `inherit-parent` mean omitting the subagent model field. |
| [2. Routing](https://github.com/cursor/plugins/blob/main/pstack/docs/guide/02-poteto-mode.md) | Prompt with the goal, done check, requested proof, known facts, and constraints. Playbook steps become visible todos; skipped steps retain a reason. Say “new task” when changing subjects. Isolate parallel work in cloud environments or local worktrees. |
| [3. Understanding](https://github.com/cursor/plugins/blob/main/pstack/docs/guide/03-understand.md) | Investigate before editing. `how` traces current mechanics; `why` reconstructs historical intent; `teach` combines explanations; `recall` rebuilds recent context. Session pickup resumes a particular interrupted effort. Evidence, inference, and missing historical records must remain distinguishable. |
| [4. Design](https://github.com/cursor/plugins/blob/main/pstack/docs/guide/04-design.md) | Settle caller usage, types, signatures, and module boundaries before implementation. Use arena for competing solutions, swarm for coverage, and interrogate for diffs. Answer empirical questions with prototypes. Write multi-PR plans after the design settles. |
| [5. Build and clean](https://github.com/cursor/plugins/blob/main/pstack/docs/guide/05-build-and-clean.md) | Bug work starts with reproduction; refactoring pins existing behavior; performance work starts with measurement. TDD applies when a cheap test path exists. Clean code before committing and use separate eyes for comment review. Forensics returns diagnosis before a fix. |
| [6. Verify and ship](https://github.com/cursor/plugins/blob/main/pstack/docs/guide/06-verify-and-ship.md) | Match proof to the changed artifact. Generate and maintain a project verification skill. Vet benchmark numbers. Open focused PRs, babysit to merge-ready, and use independent verification before shipping the contiguous safe portion of a stack. |
| [7. Overnight](https://github.com/cursor/plugins/blob/main/pstack/docs/guide/07-overnight.md) | Earn trust before unattended looping. A handoff needs a goal, finish condition, permissions, isolation, decision trail, and escape hatch. Each iteration verifies and keeps or discards its change. Queue-scale workflows add owners and coordinator audits. |
| [8. Principles](https://github.com/cursor/plugins/blob/main/pstack/docs/guide/08-principles.md) | Use precise principle names to redirect work. The names encode rules about simplicity, domain structures, proof, isolation, and structural enforcement. A citation without a changed decision is insufficient. |
| [9. Customization](https://github.com/cursor/plugins/blob/main/pstack/docs/guide/09-make-it-yours.md) | Start small and add machinery when failures recur. `automate-me` derives a personal mode from history. `reflect` proposes skill improvements; `correct` changes the environment to prevent repeated mistakes. Test skill changes with blinded evaluations. |
| [10. Recipes and pitfalls](https://github.com/cursor/plugins/blob/main/pstack/docs/guide/10-recipes-and-pitfalls.md) | Practical prompts reinforce the same habits. Avoid vague completion conditions, premature theories, untested plans, shared worktrees, unvetted numbers, automatic acceptance of review comments, and success claims based only on compilation. |

## 4. All 23 playbooks

These tables summarize **upstream**. “Exit” describes the intended deliverable. Where a file provides no separate abort rule, that is stated instead of inventing one.

### Investigation, diagnosis, and experiments

| Playbook | Entry and work | Exit | Stop conditions / boundaries |
|---|---|---|---|
| [Investigation](https://github.com/cursor/plugins/blob/main/pstack/skills/poteto-mode/playbooks/investigation.md) | A read-only question. Use `how`, plus `why` for motivation; produce a cited explanation or recommendation with tradeoffs. | Answer and judgment, grounded in sources. | No code, PR, or babysit. A resulting implementation task gets rerouted. |
| [Runtime forensics](https://github.com/cursor/plugins/blob/main/pstack/skills/poteto-mode/playbooks/runtime-forensics.md) | A live leak, CPU spin, or glitch. Capture instrumentation, reduce the signal, experimentally confirm the mechanism, and map it to source. | Cited diagnosis with artifacts and source location. | No fix unless requested. No separate retry limit specified. |
| [Trace forensics](https://github.com/cursor/plugins/blob/main/pstack/skills/poteto-mode/playbooks/trace-forensics.md) | An existing profile, trace, spindump, or heap capture. Parse into a queryable representation, narrow the cause, resolve symbols, and compare paired captures when available. | Artifact-based diagnosis and confirmation status. | Do not recapture the fixed dataset. Missing symbols remain a limitation; without paired confirmation, label the strongest supported hypothesis. |
| [Prototype](https://github.com/cursor/plugins/blob/main/pstack/skills/poteto-mode/playbooks/prototype.md) | A design or empirical choice. Build cheap alternatives in a scratch directory, observe them, and compare tradeoffs. | Recommendation plus throwaway artifacts. | No decision to settle means route to Feature. Production implementation belongs to a subsequent workflow. |
| [Eval](https://github.com/cursor/plugins/blob/main/pstack/skills/poteto-mode/playbooks/eval.md) | A proposed skill or prompt variant. Use organic requests, sanitized environments, hidden criteria, and a blinded judge. Inspect actual transcripts and outputs. | Evaluation evidence and promotion recommendation. | Prevent candidate awareness of evaluation or competitors. Judge disagreement requires synthesis; no explicit iteration cap specified. |

### Building and changing artifacts

| Playbook | Entry and work | Exit | Stop conditions / boundaries |
|---|---|---|---|
| [Bug fix](https://github.com/cursor/plugins/blob/main/pstack/skills/poteto-mode/playbooks/bug-fix.md) | A defect. Reproduce on the matching surface, eliminate hypotheses with runtime evidence, confirm the mechanism, delegate the fix, and rerun the original case. | Small justified fix, failure/pass evidence, and PR. | Wrong-surface or inconclusive verification is not success. Revert changes motivated by refuted hypotheses. User reproduction is a narrow access exception. |
| [Perf issue](https://github.com/cursor/plugins/blob/main/pstack/skills/poteto-mode/playbooks/perf-issue.md) | Measured slowness. Capture and vet a baseline, trace the mechanism, change it, and compare post-fix artifacts. | Vetted before/after result and PR. | Stop when the earliest applicable performance strategy meets the target. Inconclusive measurement is not a pass. |
| [Hillclimb](https://github.com/cursor/plugins/blob/main/pstack/skills/poteto-mode/playbooks/hillclimb.md) | Sustained improvement of one metric. Prove and freeze a measurement harness; run one hypothesis per attempt with regression gates and a decision row. | Accepted improvements, measurements, iteration counts, and ordered commits. | Stop at the agreed predicate or when remaining ideas are marginal. Do not relax the target or quit with cheap hypotheses untried. Revert noisy or incorrect wins. |
| [Feature](https://github.com/cursor/plugins/blob/main/pstack/skills/poteto-mode/playbooks/feature.md) | New or changed behavior. Understand the subsystem, design the data shape, write the throughput checkpoint, delegate implementation, verify, and order commits. | Verified behavior, design choices, open decisions, and PR. | Inconclusive verification is not a pass. Multiple valid implementation shapes require arena under this playbook; no separate abort budget specified. |
| [Refactoring](https://github.com/cursor/plugins/blob/main/pstack/skills/poteto-mode/playbooks/refactoring.md) | Structural change with unchanged behavior. Pin the contract before edits, simplify, move in small steps, and prove equivalence. | Simpler structure with preserved behavior and PR. | Split discovered bugs/features out. Revert speculative cleanup or changes that do not reduce reader load. Large cross-cutting work routes to `figure-it-out`. |
| [Visual parity](https://github.com/cursor/plugins/blob/main/pstack/skills/poteto-mode/playbooks/visual-parity.md) | Exact equivalence between visual implementations. Freeze a baseline and migrate component by component with image diffs. | Zero-diff components and PRs. | No baseline means no parity claim. Nonzero diff fails. Stop and ask if the baseline seems wrong; do not alter it or the harness to pass. |
| [Authoring a skill](https://github.com/cursor/plugins/blob/main/pstack/skills/poteto-mode/playbooks/authoring-a-skill.md) | Create or edit `SKILL.md`. Use authoring guidance; validate frontmatter, files, and links; test structural changes. | Validated skill and PR. | Subjective changes may skip test cases. Keep instructions that affect decisions; no separate abort budget specified. |
| [Opening a PR](https://github.com/cursor/plugins/blob/main/pstack/skills/poteto-mode/playbooks/opening-a-pr.md) | A change ready for publication. Use a worktree, small ordered commits, cleanup, Conventional Commit titles, and a concise evidence-bearing body. | Ready PR URL. | Opening does not start babysitting. A stack child targets its parent branch. Read-only and throwaway workflows have their own exit rules despite the file’s general “every other playbook” wording. |

### PR maintenance and landing

| Playbook | Entry and work | Exit | Stop conditions / boundaries |
|---|---|---|---|
| [Babysit](https://github.com/cursor/plugins/blob/main/pstack/skills/poteto-mode/playbooks/babysit.md) | A requested PR-status or maintenance task. Declare `check`, `threads-only`, `background`, or `drive`; work the frontier; handle conflicts, threads, then CI. | Status report or merge-ready frontier. | Never grants merge authority. Report conflicts to the topology owner. GitHub `READY`, queued `WAITING/merge-queue`, or `COMPLETE` end the applicable drive. One fresh build for a suspected flake; identical recurrence requires reclassification. |
| [Shipping](https://github.com/cursor/plugins/blob/main/pstack/skills/poteto-mode/playbooks/shipping.md) | An explicit landing request. Independently verify each PR, establish the contiguous passing run, reassess patch identity, and land bottom-up one at a time. | Confirmed landings and the remaining ceiling. | Stop at the first verification gap. Reverify changed patches as required. Do not prepare descendants before the current bottom lands. Diagnose stalls before changing the queue. |

### Long-running work and handoffs

| Playbook | Entry and work | Exit | Stop conditions / boundaries |
|---|---|---|---|
| [Autonomous run](https://github.com/cursor/plugins/blob/main/pstack/skills/poteto-mode/playbooks/autonomous-run.md) | One long task. Define a checkable predicate, choose event wakes or heartbeat, and iterate through change, verification, keep/discard, and logging. | Predicate met and final report. | Plateau means pivot. Surface genuine dead ends; never relax the predicate. Irreversible actions and uncovered product choices remain escalation points. |
| [Orchestrate](https://github.com/cursor/plugins/blob/main/pstack/skills/poteto-mode/playbooks/orchestrate.md) | A program that outlives one agent. Coordinator authors briefs, pilots a unit, runs rolling workers, drains completions, records verdicts, and integrates continuously. | Reconciled units, verified landings, final predicate, preserved store. | Collapse to Autonomous run if one agent can finish within budget. Missing brief fields block spawning. Bound retries, stop refill on systemic failure, and reconcile late workers before accepting output. |
| [Autopilot-full](https://github.com/cursor/plugins/blob/main/pstack/skills/poteto-mode/playbooks/autopilot-full.md) | Independent PR queue with landing authority. One owner carries each PR; the root independently swarm-verifies rounds and audits liveness. | Upstream: merged PRs, verdicts, trails, and reconciled delegated work. | A stated protocol is not permission to execute. Operator-reserved items wait for operator action. A stop reaches all owners as zero-writes. No merge without the root’s clean applicable verdict. |
| [Autopilot-stack](https://github.com/cursor/plugins/blob/main/pstack/skills/poteto-mode/playbooks/autopilot-stack.md) | Queue to build and verify for operator landing. Owners build; the root alone changes stack topology and reassesses rewritten patches. | One verified linear parent-branch chain. | No owner merges, arms auto-merge, or closes. Nothing enters unverified. Execution waits for go; operator stop means zero-writes. |
| [Session pickup](https://github.com/cursor/plugins/blob/main/pstack/skills/poteto-mode/playbooks/session-pickup.md) | Interrupted work. Read the prior trail, reconstruct branch/todos/decisions, identify the resume point, and route remaining work. | Explicit resume point and appropriate continuation. | Avoid redoing completed investigations. Prior self-report does not replace verification of inherited claims against the original goal. |
| [Pause safely](https://github.com/cursor/plugins/blob/main/pstack/skills/poteto-mode/playbooks/pause-safely.md) | Pause/interruption, rather than “keep going.” Finish or back out of the atomic step, cancel children, commit WIP, and externalize a resume note. | Durable checkpoint and first resume action. | Start nothing new. No new PR or push merely to pause. Report a broken tree honestly. |
| [Multi-phase plan](https://github.com/cursor/plugins/blob/main/pstack/skills/poteto-mode/playbooks/multi-phase-plan.md) | Work spanning phases or PRs. Prototype open questions, explore source, fill the prescribed plan skeleton, and run its validator. | Plan, dependencies, review gates, prototype evidence, validator output. | Do not implement. Skip an unnecessary obvious one/two-file plan. Execution requires explicit go. Its prescribed verification includes unit, ten live lanes, and perf gates. |
| [Worktree cleanup](https://github.com/cursor/plugins/blob/main/pstack/skills/poteto-mode/playbooks/worktree-cleanup.md) | Disk reclamation. Audit actual worktree paths, check active/pinned use, classify candidate loss, prune confirmed candidates, and measure reclaimed space. | Pruned set, before/after disk use, held-back reasons. | Audit buckets are advice. In-use trees and tracked uncommitted work pause for a decision. Upstream labels named scratch files discardable; see the port discrepancy below. |

## 5. Verification approach

> “The baseline is the spec. You do not touch it.”  
> — [Visual parity](https://github.com/cursor/plugins/blob/main/pstack/skills/poteto-mode/playbooks/visual-parity.md)

The guide matches evidence to the changed surface:

| Change | Expected proof |
|---|---|
| CLI | Execute the real command and inspect output. |
| UI | Drive the changed flow in the running app. |
| Exact visual migration | Compare screenshots against the frozen baseline. |
| Parser or migration | Replay saved input. |
| Storage | Read back the written value. |
| Performance | Compare captures and vetted measurements. |

A generated verification skill records **Launch, Doctor, Drive, Evidence, and Cleanup**, plus a feature map. The generator must demonstrate one complete working flow. Maintenance combines source inspection with a live pass and returns `clean`, `changed`, or `blocked`; product regressions are reported rather than concealed by documentation edits. [Verification chapter](https://github.com/cursor/plugins/blob/main/pstack/docs/guide/06-verify-and-ship.md)

Benchmark checking covers the limiting factor, production tuning, physical plausibility, correctness/errors, alternating repeated runs, end-to-end relevance, and whether the timed region contains the work. [Build chapter](https://github.com/cursor/plugins/blob/main/pstack/docs/guide/05-build-and-clean.md)

Verification is workflow-dependent:

- Bug fixes must make the original same-surface reproduction pass.
- Refactors must preserve their pinned contract.
- Hillclimbs require an improvement beyond noise and green regression gates.
- Shipping requires a verifier who did not write the change.
- Orchestrate permits worker-run cheap commands with receipt spot-checking, reserving dedicated verifiers for costly, judgment-heavy, or high-impact units.

Sources: [Bug fix](https://github.com/cursor/plugins/blob/main/pstack/skills/poteto-mode/playbooks/bug-fix.md), [Refactoring](https://github.com/cursor/plugins/blob/main/pstack/skills/poteto-mode/playbooks/refactoring.md), [Hillclimb](https://github.com/cursor/plugins/blob/main/pstack/skills/poteto-mode/playbooks/hillclimb.md), [Orchestrate verification](https://github.com/cursor/plugins/blob/main/pstack/skills/poteto-mode/playbooks/orchestrate.md#verification).

## 6. Autonomy and merge rules

### General upstream policy

Reversible work proceeds without confirmation. The explicit always-pause list includes shared-branch force pushes, deployments, data deletion, and customer messages. Session instructions such as “run until done” sustain execution; named operator gates remain meaningful. These are policies being studied, not permissions granted by these notes. [Mode autonomy](https://github.com/cursor/plugins/blob/main/pstack/skills/poteto-mode/SKILL.md#autonomy)

### Workflow-specific authority

| Workflow | Landing authority |
|---|---|
| Opening a PR | Publication only; does not initiate babysitting. |
| Babysit | Maintenance to merge-ready; never independently authorizes merging. |
| Upstream Shipping | Explicit user landing request, independent verdicts, bottom-up advancement. |
| Upstream Autopilot-full | Full-autonomy grant plus root verdict authorizes owner merges, except operator-reserved items. |
| Upstream Autopilot-stack | Builds a reviewed chain; operator lands it. |
| Port Autopilot-full | **Every PR stops at merge-ready for the operator’s explicit merge click.** |
| Port Shipping | Separate workflow requiring user landing authority and stronger revision safeguards. |

Sources: [Opening](https://github.com/cursor/plugins/blob/main/pstack/skills/poteto-mode/playbooks/opening-a-pr.md), [Babysit](https://github.com/cursor/plugins/blob/main/pstack/skills/poteto-mode/playbooks/babysit.md), [Upstream autopilot](https://github.com/cursor/plugins/blob/main/pstack/skills/poteto-mode/playbooks/autopilot-full.md), [Port autopilot](https://github.com/michael-denyer/pstack-claude/blob/main/plugins/pstack/skills/poteto-mode/playbooks/autopilot-full.md), [Port Shipping](https://github.com/michael-denyer/pstack-claude/blob/main/plugins/pstack/skills/poteto-mode/playbooks/shipping.md).

### Important port safeguards

The port’s Shipping workflow:

1. Records head, base, destination, and patch identity.
2. Cancels pending automatic/queued merges before changing an affected chain.
3. Reassesses review applicability after history or destination changes.
4. Uses a service-enforced head condition for immediate merging.
5. Allows future merging only behind durable repository verification gates.
6. Confirms the actual merge in the intended destination before advancing.

Matching patch identity can preserve substantive review, but does not establish applicability to changed dependencies or destinations. [Port Shipping](https://github.com/michael-denyer/pstack-claude/blob/main/plugins/pstack/skills/poteto-mode/playbooks/shipping.md)

Its safety reference specifies explicit remote-SHA leases and preserving the old parent boundary when replaying child commits after a squash. It also states that GitHub’s head condition does **not** atomically guard the base branch. [Merge safety](https://github.com/michael-denyer/pstack-claude/blob/main/plugins/pstack/skills/poteto-mode/references/merge-safety.md)

Required independent review remains closed when no reviewer can run; self-review is not a substitute. [Port mode](https://github.com/michael-denyer/pstack-claude/blob/main/plugins/pstack/skills/poteto-mode/SKILL.md#subagents)

## 7. Task queue and decision-log formats

### Three distinct kinds of state

**Task checklist:** the matched playbook’s steps come first, copied verbatim. A skipped step remains with `skip: <reason>`. The port uses native task tools or an uncommitted `todo.md` fallback. [Port adaptation](https://github.com/michael-denyer/pstack-claude/blob/main/plugins/pstack/skills/poteto-mode/SKILL.md#platform-adaptation)

**Work registry:** tracks units and their current state.

**Decision trail:** append-only history explaining consequential choices.

These are separate artifacts in the documented orchestration layout. [Port Orchestrate](https://github.com/michael-denyer/pstack-claude/blob/main/plugins/pstack/skills/poteto-mode/playbooks/orchestrate.md#store-layout)

### Program store

| Artifact | Documented content |
|---|---|
| `preferences.md` | Numbered standing constraints; preserve human rulings’ wording and attribution. |
| `overview.md` | Append-oriented PR and issue record. |
| `units.tsv` | Unit ID, track, state, branch, PR, head SHA, brief path; rows updated in place. |
| `frontier.json` | Computed stack frontier. |
| `ledger.tsv` | Verification verdicts. |
| `inbox/` | Completion pointers. |
| `gates.md` | Human questions, options, defaults. |
| `decisions.tsv` | Decision history. |
| `status.md` | Derived from tables rather than manually narrated. |

The port locates this store at `~/.claude/orchestrate/<project-slug>/`, outside the repository and session. Each file has one writer. [Port store layout](https://github.com/michael-denyer/pstack-claude/blob/main/plugins/pstack/skills/poteto-mode/playbooks/orchestrate.md#store-layout)

**Illustrative header, inferred from the documented field list; not a claimed literal CLI schema:**

```tsv
id	track	state	branch	pr	head_sha	brief_path
```

The upstream ledger identifies verdicts by **PR plus head SHA**, with these labels:

```text
live-ui-verified
unit-test-verified
type-check-only
verifier-blocked
verifier-failed
```

A new head invalidates the old row; blocked is not passing. [Upstream ledger](https://github.com/cursor/plugins/blob/main/pstack/skills/poteto-mode/playbooks/orchestrate.md#verification)

### Completion queue

> “Completions are queue events, not interrupts.”  
> — [Orchestrate](https://github.com/cursor/plugins/blob/main/pstack/skills/poteto-mode/playbooks/orchestrate.md)

Notifications enqueue pointers. Drains occur after critical sections, track rollups, watcher wakes, and before operator reports. Classify completions, update records, regenerate status, and refill ready work. Review is its own unit rather than hidden inside a drain. [Queue and drain](https://github.com/cursor/plugins/blob/main/pstack/skills/poteto-mode/playbooks/orchestrate.md#queue-and-drain)

### Worker brief

The documented fields are:

```text
GOAL
SCOPE
CONTEXT
ACCEPTANCE
VERIFY
TIMEBOX
FORBIDDEN
REPORT
STANDING
```

A brief names exclusive writable paths, executable acceptance criteria, verification commands, runtime cap, prohibitions, and reporting requirements. Missing scope information blocks spawning. Tiny units may use a compressed paragraph retaining the essentials. [Brief format](https://github.com/cursor/plugins/blob/main/pstack/skills/poteto-mode/playbooks/orchestrate.md#the-brief)

### General decision log

The literal documented header is:

```tsv
ts	phase	decision	why	evidence	result
```

Use ISO8601 timestamps, single-line cells, and evidence pointers. Append corrections as superseding rows. Default locations are `decisions.tsv` or `.audit/<task-slug>.tsv`; logs normally stay uncommitted. Audit decisions against the run’s transcript, then obtain cross-model trail review. [Decision-log skill](https://github.com/cursor/plugins/blob/main/pstack/skills/show-me-your-work/SKILL.md)

The logging helper sanitizes tabs/newlines and protects spreadsheet-sensitive cell prefixes. New/replacement runs use `start` rows to distinguish authorship stretches. [Logging rules](https://github.com/cursor/plugins/blob/main/pstack/skills/show-me-your-work/SKILL.md#logging-a-row)

Hillclimb additionally describes an experiment ledger:

```tsv
id	hypothesis	change	before	after	delta	tests	verdict	note
```

This header renders its documented fields; verdict records kept or reverted attempts. [Hillclimb](https://github.com/cursor/plugins/blob/main/pstack/skills/poteto-mode/playbooks/hillclimb.md)

## 8. Cursor-specific versus portable

| Mechanism | Cursor-specific form | Port / portable form |
|---|---|---|
| Persistent routing | Custom Mode attached across turns. | Port session-start routing hooks; skills-only installs require explicit invocation or standing instructions. |
| Model configuration | Auto-applied `~/.cursor/rules/pstack-models.mdc`. | Runtime-specific Markdown sheets and explicit loading. |
| Delegation | Cursor Task fields and `poteto-agent`. | Claude `Agent` with namespaced agent; Codex `spawn_agent` with instructions to read mode rules. |
| Isolation | Cloud workers with separate VMs, or worktrees. | Local worktree/branch per writer. |
| App driving | `cursor-team-kit` `control-ui` / `control-cli`. | Claude `run` or project `verify`; Codex shell or available UI automation. |
| Wake mechanism | Built-in `/loop`. | Runtime adaptation required; the Codex mapping does not claim a native loop skill. |
| Skill authoring | Built-in `create-skill`. | Claude `plugin-dev` guidance or platform-specific authoring guidance. |
| Transcripts | Workspace `agent-transcripts/`. | Runtime-specific transcript formats or supplied digests. |
| Checklists | Native todo tools. | Native task tools or `todo.md`. |
| State files | TSV, JSON, Markdown. | Same portable formats. |
| Verification rules | Real-surface checks, baselines, receipts. | Portable; the driver and environment change. |

Sources: [Setup guide](https://github.com/cursor/plugins/blob/main/pstack/docs/guide/01-setup.md), [Port runtime reference](https://github.com/michael-denyer/pstack-claude/blob/main/docs/reference.md#runtime-support), [Codex mapping](https://github.com/michael-denyer/pstack-claude/blob/main/plugins/pstack/skills/poteto-mode/references/codex-tools.md).

### Configuration details for Claude Code and Codex

The port writes:

- Claude: `<config>/pstack-models.md`, explicitly included from `CLAUDE.md`.
- Codex: `<codex-home>/pstack-models.md`; model rows and default effort are copied into its `AGENTS.md`. The hook reads its setting directly from the sheet.

Models must come from the runtime’s available choices. Claude names cannot be assumed to resolve on Codex. [Port setup](https://github.com/michael-denyer/pstack-claude/blob/main/plugins/pstack/skills/setup-pstack/SKILL.md)

The Codex mapping requires enabled multi-agent support for fan-out. Capacity errors are distinct from model-name failures. Some sequential fallbacks are permitted, but required independent review cannot degrade to self-review. [Codex mapping](https://github.com/michael-denyer/pstack-claude/blob/main/plugins/pstack/skills/poteto-mode/references/codex-tools.md)

### Additional port policies to notice

The port’s Autopilot-full bounds review work: full swarm first, targeted fix-forward verification afterward, and at most two fix-forwards before reporting a surviving blocker. Pre-existing trunk defects are separated from regressions caused by the PR. [Port Autopilot-full](https://github.com/michael-denyer/pstack-claude/blob/main/plugins/pstack/skills/poteto-mode/playbooks/autopilot-full.md)

Pause/pickup uses a shared checkpoint locator under the repository’s Git common directory. Publication validates linked artifacts and hashes before updating `latest.json`; malformed checkpoints require diagnosis rather than silent fallback. This survives session interruption, but not deleting/recloning the repository without transfer. [Resume storage](https://github.com/michael-denyer/pstack-claude/blob/main/plugins/pstack/skills/poteto-mode/references/resume-storage.md)

### Source inconsistencies worth retaining

- Shipping and autopilot say not to require Graphite. Orchestrate’s frontier machinery explicitly uses `gt`. Dependency policy is workflow-specific. [Port dependencies](https://github.com/michael-denyer/pstack-claude/blob/main/docs/reference.md#configuration-and-dependencies)
- The fetched port cleanup playbook retains permissive scratch-file wording. Its fork manifest describes newer holds for untracked files, locks, and submodule risks. The fetched sources therefore disagree; these notes do not assume which installed version applies. [Cleanup playbook](https://github.com/michael-denyer/pstack-claude/blob/main/plugins/pstack/skills/poteto-mode/playbooks/worktree-cleanup.md), [Fork manifest](https://github.com/michael-denyer/pstack-claude/blob/main/tools/forks.json)

## 9. Ideas to steal for a minimal harness

**Inferred selections for a smaller Claude Code + Codex harness.** Each is grounded in a documented mechanism; this selection is not an official pstack minimal specification.

1. **Require a checkable finish condition.** Store the goal, acceptance command, and required evidence before execution. [Routing guide](https://github.com/cursor/plugins/blob/main/pstack/docs/guide/02-poteto-mode.md)
2. **Start with a few workflows.** Investigation, bug fix, feature, and refactoring cover the guide’s common routes. Add more when recurring failures justify them. [Customization guide](https://github.com/cursor/plugins/blob/main/pstack/docs/guide/09-make-it-yours.md)
3. **Build the project verifier early.** Give it reproducible launch, health checks, driving, evidence, and cleanup instructions. [Verification guide](https://github.com/cursor/plugins/blob/main/pstack/docs/guide/06-verify-and-ship.md)
4. **Give every writer an exclusive worktree.** Also account for processes and resources shared on the same machine. [Port Feature policy](https://github.com/michael-denyer/pstack-claude/blob/main/tools/forks.json)
5. **Keep runtime adapters small and explicit.** Translate tools, model names, task tracking, transcript lookup, and wakes separately from workflow policy. [Codex mapping](https://github.com/michael-denyer/pstack-claude/blob/main/plugins/pstack/skills/poteto-mode/references/codex-tools.md)
6. **Bind review to the revision and destination.** Keep the verified head, base, patch identity, and evidence together. [Port Shipping](https://github.com/michael-denyer/pstack-claude/blob/main/plugins/pstack/skills/poteto-mode/playbooks/shipping.md)
7. **Fail closed on unavailable independent review.** Preserve partial reviewer results, but do not replace the missing gate with author confidence. [Port mode](https://github.com/michael-denyer/pstack-claude/blob/main/plugins/pstack/skills/poteto-mode/SKILL.md#subagents)
8. **Use an append-only decision TSV.** Log choices, rejected experiments, blockers, and verification results with resolvable evidence. [Decision-log skill](https://github.com/cursor/plugins/blob/main/pstack/skills/show-me-your-work/SKILL.md)
9. **Make status derived.** Generate it from work and verification records rather than maintaining a second narrative truth. [Port Orchestrate](https://github.com/michael-denyer/pstack-claude/blob/main/plugins/pstack/skills/poteto-mode/playbooks/orchestrate.md)
10. **Bound retries and review rounds.** Preserve a concrete blocked result instead of allowing indefinite repair churn. [Port Autopilot-full](https://github.com/michael-denyer/pstack-claude/blob/main/plugins/pstack/skills/poteto-mode/playbooks/autopilot-full.md)
11. **Treat merge-ready and merge authority separately.** Make landing an explicit workflow with its own evidence and race protections. [Merge safety](https://github.com/michael-denyer/pstack-claude/blob/main/plugins/pstack/skills/poteto-mode/references/merge-safety.md)
12. **Turn repeated mistakes into enforced structure.** Prefer architecture, types, checks, and tests before adding more agent prose. [Customization guide](https://github.com/cursor/plugins/blob/main/pstack/docs/guide/09-make-it-yours.md)

For this repository, those ideas remain subordinate to its supplied rules: claimed issues, protected paths, unchanged test gates, separate review, full local checks, and acceptance criteria linked in the PR body.