Reopened all five sources. Quotes below are short exact excerpts.

1. **VERIFIED — API credits and date, across two articles.**

   The [SDK support article](https://support.claude.com/en/articles/15036540-use-the-claude-agent-sdk-with-your-claude-plan) literally contains:

   > “Update October 7, 2026:”

   > “Claude Max and Team plans now include monthly API credits”

   > “Claim them into a Claude Console organization”

   The linked [credits article](https://support.claude.com/en/articles/17154008-monthly-api-credits-for-max-and-team-plans) shows:

   > “Updated today”

   > “Plan | Monthly credit”  
   > “Max 5x | $100”  
   > “Max 20x | $200”

   **Clarification:** the explicit October 7 date appears in the SDK article; the amounts appear in the credits article. No retraction of the amounts or dated announcement.

2. **Personal `claude -p`: supported functionality; Max-subscription authorization remains UNVERIFIED.**

   [Consumer terms, §3(7)](https://www.anthropic.com/legal/consumer-terms) restrict automated access, with this exception:

   > “Except when you are accessing our Services via an Anthropic API Key or where we otherwise explicitly permit it,”

   The restriction covers:

   > “automated or non-human means”

   **Correction:** the version retrieved identifies itself as the **EEA/Switzerland consumer terms**, effective October 8, 2025. I should have disclosed that regional scope.

   [Claude Code legal guidance](https://code.claude.com/docs/en/legal-and-compliance) says:

   > “Advertised usage limits for Pro and Max plans assume ordinary, individual usage of Claude Code and the Agent SDK.”

   [Headless documentation](https://code.claude.com/docs/en/headless) explicitly says:

   > “You can wrap a non-interactive call in a script to use Claude as a project-specific linter or reviewer.”

   **Distinction:** your own local script is a documented use case, separate from offering a Claude-powered product to others. But these passages do **not explicitly establish that personal `claude -p` may consume Max OAuth subscription allowance**. API-authenticated scripting is clearly supported. I retract any implication that your personal script is categorically forbidden merely because it is automated; I cannot give an unconditional “Max subscription permits it” from these passages.

3. **VERIFIED — Codex ChatGPT authentication on self-hosted CI.**

   The [official CI authentication guide](https://learn.chatgpt.com/docs/auth/ci-cd-auth) refers to:

   > “ChatGPT-managed Codex auth”

   and requires:

   > “trusted private infrastructure”

   Its self-hosted section says:

   > “The simplest fully automated setup is a self-hosted GitHub Actions runner with a persistent `CODEX_HOME`.”

   It also requires preserving refreshed credentials and serializing use of each credential-file copy. **Correction:** the document explicitly excludes public/open-source repositories; my earlier answer omitted that restriction. API keys remain its recommended default.

4. **VERIFIED — model name and estimate.**

   [Pricing page](https://learn.chatgpt.com/docs/pricing):

   > “The estimates below show local messages per five-hour period for Plus and Standard Business.”

   Its table contains:

   > “GPT-6.1 Sol | 15-160 | 15-160”

   Thus **GPT-6.1 Sol** and **15–160 local messages per five hours** are literally present. The page describes estimates, not fixed guaranteed limits or completed-agent counts.

5. **VERIFIED retrievability; results remain self-reported.**

   The [Quinn Leng LinkedIn article](https://www.linkedin.com/pulse/dug-my-5-months-claude-code-codex-sessions-quinn-leng-jsiwc) is retrievable through the browser tool and says:

   > “Published Aug 7, 2026”

   > “1,387 pull requests, of which 1,247 merged, across 20 weeks”

   **89.9% is my calculation** from those counts, not a quoted percentage. It measures eventual merging, not first-pass human acceptance. I retain the attribution as a firsthand report, not independently verified performance.