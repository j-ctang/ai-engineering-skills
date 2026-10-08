**As of October 7, 2026.** VERIFIED means supported by current primary documentation; UNVERIFIED means the docs did not establish it. Exact quotations appear in quotation marks. **“GA unverified” does not mean unavailable**—it means no explicit GA designation was found.

**1) Claude Code built-ins**

With a subscription login, agent model work consumes your shared Claude/Claude Code allowance. Parallel agents multiply consumption; worktree creation itself does not invoke a model. [Subscription billing](https://support.claude.com/en/articles/11145838-use-claude-code-with-your-pro-or-max-plan), [parallel-agent costs](https://code.claude.com/docs/en/agents).

| Feature | What it does; exact documentation evidence | Pro vs Max | Quota / maturity |
|---|---|---|---|
| **Subagents — VERIFIED** | Delegated workers with separate contexts, configurable models/tools, and results returned to their caller. Named subagents can also communicate. | Both; core CLI capability. | Yes. GA **UNVERIFIED**. [Docs](https://code.claude.com/docs/en/sub-agents) |
| **Background subagents — VERIFIED** | “Background subagents run concurrently while you continue working.” They belong to the parent session. | Both. | Yes. GA **UNVERIFIED**. [Docs](https://code.claude.com/docs/en/sub-agents) |
| **Detached background sessions — VERIFIED** | Full local sessions managed by a supervisor, surviving terminal closure. Start with `claude --bg`, or background an existing session with `/bg`. | No Max-only restriction documented; separate Pro entitlement **UNVERIFIED**. | Yes. Part of Agent View research preview. [Docs](https://code.claude.com/docs/en/agent-view) |
| **Agent teams / teammates — VERIFIED** | Lead coordinates independent teammates through shared tasks and messaging. “Agent teams are experimental and disabled by default.” Enable `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`. | No Max-only restriction documented. | Yes, substantially more tokens. **Experimental**; resume/coordination limitations. [Docs](https://code.claude.com/docs/en/agent-teams) |
| **SendMessage — VERIFIED** | Messages/resumes subagents and teammates; also messages other eligible sessions. “`SendMessage` doesn’t require … agent teams … to be enabled”¹ | Both; cross-machine/cloud discovery requires Remote Control. | Resulting agent turns consume quota. GA **UNVERIFIED**. [Subagents](https://code.claude.com/docs/en/sub-agents), [cross-session messaging](https://code.claude.com/docs/en/cross-session-messaging) |
| **FleetView / Agent View — VERIFIED distinction** | Official public feature is **Agent View**, opened with `claude agents`: dispatch, monitor, reply, attach, stop. “Agent view is in research preview.” **FleetView as its official public name is UNVERIFIED**; a separate third-party extension also uses that name. | No Max-only restriction documented. | Sessions consume quota independently; row summaries also make model requests. **Research preview**. [Docs](https://code.claude.com/docs/en/agent-view) |
| **Worktree isolation — VERIFIED** | Separate checkouts via `--worktree`; subagents can receive their own worktrees. Agent View dispatches move into worktrees before editing. | Both; no premium gate documented. | Agent work consumes quota; Git isolation itself does not. GA **UNVERIFIED**. [Docs](https://code.claude.com/docs/en/worktrees) |
| **Routines / scheduled cloud agents — VERIFIED** | Saved prompts/repos/connectors, triggered by schedule, HTTP API, or GitHub events; run while your laptop is closed. “Routines are in research preview.” | Explicitly **Pro and Max**, also Team/Enterprise. | Yes: “Routines draw down subscription usage the same way interactive sessions do.” **Research preview**. [Docs](https://code.claude.com/docs/en/routines) |
| **Claude Code on the web — VERIFIED** | Cloud sessions with independent environments; continue after laptop closure; steer through browser/mobile/desktop/terminal. “Cloud sessions are available on Pro, Max, and Team plans” | Both. | Yes. Current page has no preview label; GA **UNVERIFIED**. [Docs](https://code.claude.com/docs/en/claude-code-on-the-web) |
| **Remote Control — VERIFIED** | Browser/phone controls a session executing on your computer; computer/process must remain running. | Explicitly both. | Session work consumes quota. Current page has no preview label; GA **UNVERIFIED**. [Docs](https://code.claude.com/docs/en/remote-control) |
| **`/loop` — VERIFIED** | Repeats prompts within a running session, using fixed or adaptive intervals. “Recurring tasks automatically expire 7 days after creation.” Can continue in a background session. | Both; works across providers. | Each iteration consumes usage. GA **UNVERIFIED**. [Docs](https://code.claude.com/docs/en/scheduled-tasks) |

¹ Ellipses mark omissions from the exact source sentence.

Two additional built-ins matter for learning orchestration:

- **Dynamic workflows — VERIFIED:** JavaScript scripts orchestrate subagents and retain intermediate results outside the main context. Available on all paid plans; **Pro must enable them in `/config`**. Consume quota; GA unverified. [Docs](https://code.claude.com/docs/en/workflows).
- **Projects — VERIFIED:** Claude coordinates ongoing parallel threads in cloud or through Remote Control. **Public beta on Pro/Max, gradual rollout**; consumes session usage. [Docs](https://code.claude.com/docs/en/claude-projects).

**2) Codex CLI and cloud**

| Feature | Verified capability / exact evidence | Access, quota, maturity |
|---|---|---|
| **Subagents — VERIFIED** | “Current Codex releases enable subagent workflows by default.” Parent delegates and collects results; `/agent` inspects/switches threads. | ChatGPT Pro included; also other eligible plans/API authentication. More agents consume more tokens. GA **UNVERIFIED**. [Docs](https://learn.chatgpt.com/docs/agent-configuration/subagents) |
| **Cloud tasks — VERIFIED** | Independent remote workspaces: “Each task has its own workspace and can keep working while your computer is asleep.” | Included with Pro; shares local/cloud allowance. Current GA label **UNVERIFIED**. [Cloud](https://learn.chatgpt.com/docs/cloud), [pricing](https://learn.chatgpt.com/docs/pricing) |
| **`codex exec` — VERIFIED** | Headless scripts/CI; supports JSONL events, structured output and resume. “`codex exec` reuses saved CLI authentication by default.” | Subscription authentication consumes allowance; API authentication incurs API charges. GA **UNVERIFIED**. [Docs](https://learn.chatgpt.com/docs/non-interactive-mode) |
| **Worktrees — VERIFIED, surface distinction** | Desktop manages worktrees automatically. CLI can run inside worktrees you create yourself. | No separate model charge for Git operations. **Automatic per-subagent CLI worktree isolation is UNVERIFIED**. [Docs](https://learn.chatgpt.com/docs/environments/git-worktrees) |
| **Orchestrator — VERIFIED scope** | Built-in parent/subagent coordination exists. A separate managed **Agents API** supplies orchestration: “OpenAI manages sessions, orchestration, context compaction, and recovery”. | Agents API uses **API billing**, not ChatGPT Pro allowance. A general Claude/Codex fleet manager built into CLI is **UNVERIFIED**. [Agents API](https://developers.openai.com/api/docs/guides/agents-api/overview) |

**3) Plans and limits**

- **Claude Pro — VERIFIED:** $20/month US, or $200/year; includes Claude Code. Five-hour session limits plus weekly limits; workload/model/context determine consumption. Exact line: “Your session-based usage limit will reset every five hours.” **A fixed current prompts-per-window number is UNVERIFIED.** [Pro](https://support.claude.com/en/articles/8325606-what-is-the-pro-plan), [pricing](https://claude.com/pricing).
- **Claude Max — VERIFIED:** 5× or 20× Pro session usage, at $100/$200 monthly. Paid plans also have weekly limits. [Pricing](https://claude.com/pricing).
- **New monthly API credits — VERIFIED:** **Pro gets none.** Exact line: “No. The credits are available on Max and Team plans only.” Max 5× gets **$100/month**, Max 20× **$200/month**. Rollout takes several days; new subscribers need seven days on the plan. Credits expire each billing cycle. [Credit rules](https://support.claude.com/en/articles/17154008-monthly-api-credits-for-max-and-team-plans).
- **Credit distinction — VERIFIED:** These credits exclude interactive Claude Code and extra subscription usage. They **do cover your own `claude -p`/Agent SDK runs authenticated with a linked Console API key**—useful for building your orchestrator. [Credit rules](https://support.claude.com/en/articles/17154008-monthly-api-credits-for-max-and-team-plans).
- **ChatGPT Pro — VERIFIED:** Now **$100/$200/$500 monthly tiers**. Current Codex pricing says: “Pro plans currently have no five-hour limit.” Included allowance/model limits still apply; weekly limits may apply. Local/cloud usage shares allowance. **Unlimited Codex is UNVERIFIED.** Eligible existing Pro 200 subscribers retain their previous allowance through **October 29, 2026**. [Pricing](https://learn.chatgpt.com/docs/pricing), [Pro tiers](https://help.openai.com/en/articles/9793128-about-chatgpt-pro-tiers).

**4) Third-party comparison**

| Tool | VERIFIED strengths and exact evidence | Cost / tradeoff |
|---|---|---|
| **[claude-squad](https://github.com/smtg-ai/claude-squad)** | Small terminal manager wrapping multiple CLIs: “tmux to create isolated terminal sessions for each agent”. Git worktrees, diff review, configurable profiles. | Open-source AGPL-3.0; underlying agents retain their billing/authentication. Subscription-login compatibility is inferred from launching the CLI; README’s Codex instructions still suggest API keys. **Best source to study a small orchestrator.** |
| **[Vibe Kanban](https://github.com/BloopAI/vibe-kanban)** | Agent workspaces, diff comments, previews, multiple providers. | Open-source Apache-2.0. Company shut down April 10: “The Vibe Kanban project will live on, open source and community maintained.” Local workspaces continue; hosted services were withdrawn. [Announcement](https://www.vibekanban.com/blog/shutdown) |
| **[Conductor](https://www.conductor.build/pricing)** | Free Mac tier offers “Run multiple coding agents in parallel” and “Bring your own subscriptions and keys”. Runs first-party Claude Code/Codex underneath. | **$0 local tier**; model usage still draws from your subscriptions/API keys. Cloud/API features require paid tiers. **Best convenient mixed-provider GUI.** [Agent support](https://www.conductor.build/) |

**5) My recommendation**

For your **1–3 local agents**, start with **Conductor’s free local tier**, one Claude implementation agent and one Codex reviewer. Keep separate worktrees and use the independent reviewer plus automated gates required by your repository.

For learning, study **claude-squad**, then build a thin supervisor around `claude -p` and `codex exec --json`: task claims, process lifecycle, worktrees, persisted status, independent review and check results. Native Claude Agent View is also worth trying for Claude-only sessions; agent teams are useful experiments, but their documented recovery limitations make them a weaker foundation.

**Stay on Claude Pro initially.** Upgrade to **Max 5×** when observed limits constrain you or you begin API/Agent SDK experiments—the new $100 monthly API credit directly supports that learning path. This recommendation is my judgment, based on the verified capabilities above.