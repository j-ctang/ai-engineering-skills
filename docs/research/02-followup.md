**1) Source credibility and transcript — partly VERIFIED**

- **redreamality.com:** Its author identifies himself as **Remy**, an AI scientist and Fudan PhD graduate; these are self-descriptions, not independently verified credentials. His Tan article explicitly derives from **X automatic captions**, with corrected proper names—not the Matt Pocock YouTube transcript. [About](https://redreamality.com/about/), [article](https://redreamality.com/blog/lauren-tan-poteto-trust-before-parallel/)
- **CarlStack:** Identifies its author as **李卡爾**, linking GitHub `CarlLee1983`. Its Tan article supplies video timestamps but acknowledges lacking a complete, verbatim-checkable transcript of the later interview. [About](https://carlstack.gravito.dev/about/), [article](https://carlstack.gravito.dev/blog/agent-work-requires-verifiable-codebase/)
- **AI-generated? UNVERIFIED for both Tan articles.** CarlStack discloses cloud-model assistance for a different article; that does not establish how its Tan summary was written. Neither summary should substitute for a primary transcript. [Disclosure](https://carlstack.gravito.dev/blog/local-ai-agent-execution-boundaries/)
- **Transcript retrieval: unsuccessful.** I retried [YouTube](https://www.youtube.com/watch?v=MN9dGgmLyso), [YouTubeToTranscript](https://youtubetotranscript.com/transcript?v=MN9dGgmLyso), [WithTranscript](https://www.withtranscript.ai/video/MN9dGgmLyso) and [Filmot](https://filmot.com/video/MN9dGgmLyso). No usable transcript returned. **I cannot responsibly quote Tan on setup time, counts or autonomous merging.** My earlier internal-setup claims remain secondary-source reports.

**2) Monthly versus daily counts — correction**

- **VERIFIED arithmetic:** 2,000–2,500 over 30 days = **67–83/day**; over 22 working days = **91–114/day**. Neither establishes sustained “hundreds/day.” The underlying monthly totals remain **self-reported, unaudited**. [Source comparison](https://carlstack.gravito.dev/blog/agent-work-requires-verifiable-codebase/)
- I should have rejected that formulation more directly. Peak-day throughput and the claimed **1–2-month setup period remain UNVERIFIED**.

**3) Does full autopilot merge without human approval? — VERIFIED documentation, conditional**

**Without per-PR human approval: yes, after an explicit autonomy grant. Without any human authorization: no.** Exact excerpts:

> “On a clean verdict the owner merges”

> “The operator's full-autonomy grant plus the root's clean verdict is the merge authorization”

[Official playbook, lines 16 and 18](https://github.com/cursor/plugins/blob/main/pstack/skills/poteto-mode/playbooks/autopilot-full.md)

The playbook uses `origin/main` in merge-preparation checks and directs the owner to squash-merge through the selected forge. It requires passing CI, valid independent verification and conflict checks. Operator-reserved items still await a human click; forge-enforced approvals cannot be bypassed. **This verifies intended workflow, not observed production execution.** [Full playbook](https://github.com/cursor/plugins/blob/main/pstack/skills/poteto-mode/playbooks/autopilot-full.md)

**4) Cursor-only or portable? — VERIFIED distinction**

- **Original distribution:** Cursor plugin. **Community ports exist for Claude Code and Codex CLI**, including Michael Denyer’s port; these include adaptations and declared policy forks, so they are not identical upstream distributions. [Original guide](https://github.com/cursor/plugins/blob/main/pstack/docs/guide/README.md), [port](https://github.com/michael-denyer/pstack-claude)
- **Portable concepts/content:** Markdown workflows, acceptance criteria, investigation/design/review procedures, verification scripts and evidence logs.
- **Harness-dependent machinery:** Tool/model mappings, plugin registration, startup hooks, subagent dispatch, wakeups/`/loop`, transcript access and cloud-agent orchestration. The port explicitly excludes Cursor-specific automations, sticky-mode metadata and Grok Bot UI workflows. **End-to-end equivalence remains UNVERIFIED here.** [Port scope and runtime adapters](https://github.com/michael-denyer/pstack-claude/blob/main/docs/reference.md)

**5) Minimum solo TypeScript/GitHub environment — recommended order, not a verified universal ranking**

1. **Executable correctness checks:** Repeatable install/start/build, TypeScript checking, lint and meaningful behavior tests; encode recurring architectural mistakes as mechanical checks. [OpenAI architecture enforcement](https://openai.com/index/harness-engineering/)
2. **Agent-driven runtime verification:** A repeatable browser/control script that reproduces bugs and checks fixes, preserving screenshots/video and logs. [pstack verification infrastructure](https://github.com/cursor/plugins/blob/main/pstack/docs/guide/06-verify-and-ship.md)
3. **Isolated runnable workspace per task:** Separate checkout, ports and test data; sandbox unattended commands and restrict network/credentials. [pstack overnight isolation](https://github.com/cursor/plugins/blob/main/pstack/docs/guide/07-overnight.md), [sandbox rationale](https://www.anthropic.com/engineering/claude-code-sandboxing)
4. **Small repository knowledge map:** Short `AGENTS.md` pointing to architecture, commands, product behavior and acceptance criteria. [OpenAI repository knowledge](https://openai.com/index/harness-engineering/)
5. **Independent verification plus a PR repair loop:** Fresh reviewer verifies the final patch; owner handles conflicts, review findings and CI through `gh`. [pstack shipping](https://github.com/cursor/plugins/blob/main/pstack/docs/guide/06-verify-and-ship.md)
6. **Explicit task queue and autonomy contract:** Defined outcomes, permissions, stopping conditions and decision logs before overnight execution. [pstack overnight contract](https://github.com/cursor/plugins/blob/main/pstack/docs/guide/07-overnight.md)
7. **Safe automated landing when concurrency warrants it:** Required checks and a merge queue testing current trunk plus preceding changes. This is an additional recommendation, **not OpenAI’s stated minimal-gates policy**. [GitHub merge queues](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-a-merge-queue)

**6) OpenAI’s human role, review and merge policy — VERIFIED**

Exact excerpts, kept short:

> “Humans steer. Agents execute.”

> “Humans may review pull requests, but aren’t required to.”

> “The repository operates with minimal blocking merge gates.”

[OpenAI post](https://openai.com/index/harness-engineering/)

Humans prioritize work, define acceptance criteria and validate outcomes. Codex performs local self-review plus additional agent reviews, addresses feedback, and often merges its own PRs. Flakes receive follow-up runs rather than indefinite blocking. OpenAI explicitly limits generalization to repositories with comparable tooling and structure. **My earlier answer underemphasized how permissive its merge policy is.** [Same primary source](https://openai.com/index/harness-engineering/)