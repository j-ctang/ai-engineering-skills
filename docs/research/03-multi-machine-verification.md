As of **October 7, 2026**. **VERIFIED** means supported by linked documentation or a firsthand report; reported results are not independently audited. **UNVERIFIED** means evidence is missing or the statement is an estimate.

**A. Multiple computers running coding agents**

**VERIFIED: concrete setups exist. UNVERIFIED: this is a widespread developer trend.** Evidence is stronger for “laptop + always-on host” than for large fleets of physical computers.

| Concrete example | Machines, orchestration, persistence |
|---|---|
| **Quinn Leng, August 2026 — VERIFIED firsthand report** | Claude Code/Codex on home Mac minis, **three accounts of each**, orchestrated through Morty/Kylon. Reports 8,504 sessions, 1,387 PRs, and ~$6,800 subscription spending versus ~$56,000 calculated API-equivalent usage. Those are self-reported figures, not audited savings. [Original article](https://www.linkedin.com/pulse/dug-my-5-months-claude-code-codex-sessions-quinn-leng-jsiwc) |
| **Jose and Goose, June 2026 — VERIFIED firsthand report** | Parallel Claude sessions on a Mac and always-on Linux server, using a worktree-management shell tool called cmux. One branch/worktree per task; describes four sessions sharing one Max subscription. [Workflow](https://joseandgoose.com/writing/how-i-run-parallel-claude-code-sessions) |
| **Samuel Huang, June–July 2026 — VERIFIED published setup** | MacBook controls a home Mac mini through Tailscale/SSH; GitHub stores code. This demonstrates remote persistence, rather than both Macs independently running a fleet. [Two Macs, One Workflow](https://samuelhuang.org/guide/multi-computer-setup) |
| **Blink Build Studios — VERIFIED documented implementation** | Claude workers run as GitHub Actions jobs on a Mac mini, using Colima, boot-started services, and persistent local caches. Documentation explicitly labels the setup work in progress. [Runner guide](https://github.com/Blink-Build-Studios/agentic-development-workflow/blob/main/docs/mac-mini-runner.md) |

**VERIFIED tools and state mechanisms:**

- **tmux + SSH/Tailscale:** preserves terminal processes across client disconnects. Old laptops/NUCs can host this stack. Process survival is different from crash recovery; durable progress still needs commits and checkpoints. [Home-server guide](https://github.com/felderi/claude-code-home-server)
- **claude-squad:** manages Claude/Codex sessions through tmux and isolated Git worktrees; primarily a host-local manager. [Repository](https://github.com/smtg-ai/claude-squad)
- **Vibe Kanban:** issues coordinate work; workspaces create separate Git branches/worktrees and retain sessions/notes. Remote access is documented. [Workspaces](https://www.vibekanban.com/docs/workspaces), [remote access](https://www.vibekanban.com/docs/remote-access)
- **Conductor:** local workspaces or cloud sandboxes running first-party agents. Current pricing: **local free; Pro $50/month; Teams $60/user/month**, with inference subscriptions/keys supplied separately. Its pricing page says customer-owned cloud machines are not yet supported. [Pricing](https://www.conductor.build/pricing)
- **Claude Remote Control:** another device controls an agent still executing on its original machine. **Teleport:** fetches a cloud session’s branch and conversation into a local terminal; subsequent local work is a separate session copy. [Remote Control](https://code.claude.com/docs/en/remote-control), [Teleport](https://code.claude.com/docs/en/claude-code-on-the-web)
- **Codex Cloud:** each task has its own workspace and continues while your computer sleeps. [Official documentation](https://learn.chatgpt.com/docs/cloud)

**Practical architecture — recommendation:** use Git commits/PRs for code, a durable task queue for ownership/status, and stored transcripts/evidence for recovery. Across computers, use separate clones and push/fetch; worktrees alone do not synchronize machines. Claim tasks atomically, isolate ports/databases, and integrate through CI.

**Costs — VERIFIED:** Tailscale has a free personal tier; GitHub says self-hosted runners are free to use, with hardware/maintenance costs borne by you. Reusing hardware avoids purchase cost, but electricity, builds, storage, and inference remain. [Tailscale](https://tailscale.com/pricing), [GitHub runners](https://docs.github.com/en/actions/concepts/runners/self-hosted-runners)

**Subscription limits and realistic concurrency**

| Plan | VERIFIED current constraints |
|---|---|
| **Claude Max 5x / 20x** | **$100 / $200 monthly**. Five-hour allowance plus weekly limits; usage across Claude and Claude Code is shared. No published guaranteed number of concurrent agents. [Max limits](https://support.claude.com/en/articles/11049741-what-is-the-max-plan), [shared usage](https://support.claude.com/en/articles/11145838-use-claude-code-with-your-pro-or-max-plan) |
| **Codex / ChatGPT Plus** | **$20 monthly**. Current estimates include **15–160 local GPT-6.1 Sol messages per five hours**, depending on workload. Cloud/local usage shares allowance; weekly limits may apply. These are messages, not completed tasks. [Official pricing](https://learn.chatgpt.com/docs/pricing) |
| **Codex / ChatGPT Pro** | Current tiers are **$100/$200/$500 monthly**. Pricing docs currently say Pro has no five-hour limit, but included allowance/model limits still apply. [Pricing](https://learn.chatgpt.com/docs/pricing), [Pro tiers](https://help.openai.com/en/articles/9793128-about-chatgpt-pro-tiers) |

**UNVERIFIED: a sustainable fixed agent count per plan.** Four interactive Max sessions are documented, but that proves neither four continuously busy agents nor 24/7 capacity. A reasonable **pilot recommendation**, not a measured entitlement: start with **1–2 active workers on Plus/Max 5x, 2–4 on Pro/Max 20x**, then measure quota consumption over a full week. More machines do not increase one account’s allowance.

**Headless CI and terms**

- **Codex — VERIFIED documented support:** OpenAI explicitly documents ChatGPT account authentication on **trusted private CI runners**, including persistent self-hosted GitHub runners. It requires one machine or serialized job stream per copied `auth.json`; API keys remain the recommended automation default. This is stronger evidence than a blanket “subscription CI is forbidden” claim. [CI authentication](https://learn.chatgpt.com/docs/auth/ci-cd-auth)
- **Claude — VERIFIED API-based automation; UNVERIFIED blanket Max-OAuth CI permission:** `claude -p` is documented for scripts/CI. However, legal guidance distinguishes ordinary subscription use from API-based products/services, and consumer terms restrict automated access unless explicitly permitted. Do not treat technical operability as unlimited subscription authorization. [Headless docs](https://code.claude.com/docs/en/headless), [credential policy](https://code.claude.com/docs/en/legal-and-compliance), [terms](https://www.anthropic.com/legal/consumer-terms)
- **Current change:** Anthropic’s October 7 update replaces June’s SDK credit with claimable API credits: **Max 5x $100/month; Max 20x $200/month**, separate from interactive quota. Use API authentication for the clearly documented automation route. Official Claude self-hosted cloud environments are also available for **Team/Enterprise**, billed against organizational usage. [API credits](https://support.claude.com/en/articles/17154008-monthly-api-credits-for-max-and-team-plans), [self-hosted environments](https://code.claude.com/docs/en/self-hosted-environments)

**B. Lauren Tan and pstack**

**VERIFIED:** the product is **Grok Bot**, with desktop/mobile clients, agent harness, infrastructure, and integrations. Her workflow is therefore broader than a conventional web app. xAI’s engineering account specifically associates Lauren’s PR output with the team building Grok Bot; it also describes Apple Accessibility, iOS Simulator screenshots, and system-audio testing. **UNVERIFIED:** her personal ownership of every client or Grok model-training component. [xAI engineering account](https://x.ai/bot/guides/grok-bot-for-engineering)

**VERIFIED pstack runtime verification:** [06-verify-and-ship](https://github.com/cursor/plugins/blob/main/pstack/docs/guide/06-verify-and-ship.md) requires checks against the **running artifact**:

- Execute actual CLI commands; walk changed UI flows; replay inputs; read back storage; compare performance profiles.
- Generate a project verification skill with **Launch, Doctor, Drive, Evidence, Cleanup**, plus a feature map.
- Prefer an existing harness; otherwise use browser/CDP, PTY, or HTTP. Capture commands/output, screenshots, video, or traces.
- Diff screenshots against frozen baselines for visual parity.
- Before shipping, a **fresh agent per PR** proves behavior live; the verifier is not the author.

Compilation and a plausible explanation do not constitute proof.

**C. Verifying desktop and robotics features**

The following are **engineering recommendations grounded in verified tooling**, not guarantees of agent success.

| Layer | What to implement |
|---|---|
| **State machines + property tests** | Model lifecycle, control ownership, actuator enablement, and episode identity separately. Generate sequences such as takeover → reset → reconnect → stale command. Check invariants after every transition. Hypothesis supports generated action sequences and invariant assertions. [Documentation](https://hypothesis.readthedocs.io/en/latest/stateful.html) |
| **Hardware fakes/mocks** | Put devices behind interfaces. Fakes should inject latency, missing acknowledgments, stale telemetry, disconnects, and retained actuator state. ROS mocks verify controller plumbing, but their ideal command-to-state mirroring cannot prove physical behavior. [ROS mock components](https://control.ros.org/master/doc/ros2_control/hardware_interface/doc/mock_components_userdoc.html) |
| **Simulation → hardware-in-the-loop → physical checks** | Exercise physics/control logic in simulation, then real firmware, timing, buses, and reboot behavior on hardware. Preserve firmware/build IDs and telemetry. HIL coverage has limits; it does not automatically test every physical failure. [PX4 simulation](https://docs.px4.io/main/en/simulation/), [HIL limitations](https://docs.px4.io/main/en/simulation/hitl) |
| **Native/desktop UI** | Drive the actual packaged app using XCTest/accessibility or platform equivalents; Playwright supports Electron. Verify focus, dialogs, permissions, persistence, and restart behavior—not just screenshots. [Apple UI automation](https://developer.apple.com/documentation/xcuiautomation/xcuiapplication), [Electron](https://playwright.dev/docs/api/class-electron) |
| **Visual regression** | Freeze OS/fonts/theme/viewport/data and compare approved baselines. Require separate approval for baseline changes. Pixel parity catches appearance regressions, not semantic correctness. [Playwright guidance](https://playwright.dev/docs/test-snapshots) |

**The energized-hand/reset example:** define what reset means physically. De-energizing may be required, or controlled holding may be safer; make that explicit. Assert **no autonomous commands after takeover**, reject commands from previous episodes, and require measured actuator feedback before declaring the safe state reached. Test lost acknowledgments and process restarts on the real device. A UI flag or successful `reset()` return is insufficient.

**VERIFIED distinction:** original **DAgger** collects expert corrections on learner-visited states; **HG-DAgger** specifically addresses human-controlled intervention. Neither algorithm proves reset/actuator safety. [DAgger](https://arxiv.org/abs/1011.0686), [HG-DAgger](https://arxiv.org/abs/1810.02890)

**UNVERIFIED: a general 85%+ human-acceptance guarantee.** It is a reasonable target for small, well-specified changes with repeatable environments and strong evidence. For subjective UX or hardware behavior, retain targeted human acceptance checks. Measure **first-pass acceptance across all attempted tasks**, separately from eventual merge rate, and track post-acceptance defects. Quinn’s reported ~90% eventual merge rate does not establish 90% first-pass feature acceptance. [Reported results](https://www.linkedin.com/pulse/dug-my-5-months-claude-code-codex-sessions-quinn-leng-jsiwc)