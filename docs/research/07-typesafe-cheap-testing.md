**TypeSafe is paid, but routine proxy verification can run with $0 in inference charges.** Research checked October 7, 2026; no paid API calls made.

**1. Service, pricing, and “now costs money”**

- **VERIFIED:** This is **TypeSafe AI’s Jev decision-model API**, hosted at `https://api.typesafe.ai/v1/systemone`, authenticated with a Bearer key. It returns typed choices, scores, and yes/no probabilities. Your [client](/Users/justin_tang/dev/claude-code-jev-prune/src/services/jevService.ts:55) matches the [official API reference](https://docs.typesafe.ai/api).
- **VERIFIED:** Current direct pricing is **$0.042 per million input tokens**, equivalently **$42 per billion**. Outputs are free. Exact official lines: “Price (per Btok / per Mtok) | $42 / $0.042” and “Output tokens are free.” `jev-latest` currently resolves to `jev-1.13.0`. [Official model documentation](https://docs.typesafe.ai/models)
- **VERIFIED, historical report:** VentureBeat reported signup access with “$5 in free credit” on September 20. **UNVERIFIED:** Whether that credit remains available to new accounts today; it is signup credit, not evidence of an ongoing free tier. [September 21 report](https://venturebeat.com/security/companies-are-putting-jev-in-charge-of-ai-agent-decisions-and-prompt-injection-can-influence-the-verdict)
- **VERIFIED:** Vercel offered a temporary free promotion: “Jev is free on Vercel AI Gateway until September 25, 2026.” That date has passed. [Vercel Academy](https://changelog.vercel.com/academy/make-decisions-with-jev)
- **UNVERIFIED:** A recent increase in **direct TypeSafe pricing**. An expired gateway promotion or exhausted signup credit could explain “now costs money,” but neither proves a direct price increase.

**2. Cost for jev-prune**

**VERIFIED locally:** The [architecture](/Users/justin_tang/dev/claude-code-jev-prune/docs/ARCHITECTURE.md) says:

> “Batches contain at most 32 questions.”

> “Scoring only runs on a new user turn.”

Each batch sends the current goal, candidate tool inputs/results, and question definitions—not the entire Claude conversation. Protection, cached decisions, and deterministic rewrites reduce the candidates requiring inference.

**ESTIMATE—actual token totals UNVERIFIED:**

`prune cost = sum(batch input_tokens) × $0.042 / 1,000,000`

| Billable input per batch | Cost per API call | Cost for 1,000 calls |
|---:|---:|---:|
| 1,000 tokens | $0.000042 | $0.042 |
| 8,000 tokens | $0.000336 | $0.336 |
| 32,000 tokens | $0.001344 | $1.344 |

For example, **96 eligible candidates → three batches**. Assuming 8,000 billable tokens each, one prune costs **$0.001008**, about **0.10¢**. That token assumption needs measurement.

The 120K Claude-context trigger is **not** 120K TypeSafe billable tokens. Additional routing and opt-in skill-completion calls must be counted separately. The official response exposes `usage.input_tokens`; the current client discards usage, so actual cost instrumentation would need to retain metadata. [API usage schema](https://docs.typesafe.ai/api)

**VERIFIED limitation:** TypeSafe allows 32K tokens for state plus the longest question, and 64K total. A 32-candidate batch can exceed that limit if tool outputs are large. [Official limits](https://docs.typesafe.ai/models)

**3. Practical $0-per-run verification**

**VERIFIED locally:** The repo already documents this separation:

> “The optional live Jev check uses synthetic content and is excluded from the default suite.”

Client tests inject `fetchFn`; proxy tests use local HTTP servers. [Verification strategy](/Users/justin_tang/dev/claude-code-jev-prune/docs/ARCHITECTURE.md:188), [client tests](/Users/justin_tang/dev/claude-code-jev-prune/test/jevService.test.ts:67). I inspected these; I did not run the suite.

**Recommended approach:**

| Layer | Implementation | What it proves |
|---|---|---|
| Every PR/agent run | Existing injected responses; dummy keys; external network blocked | Thresholds, caching, protection, immutability, fail-open behavior |
| HTTP integration | Local TypeSafe stub plus local Anthropic/SSE upstream | Serialization, headers, aborts, streaming, multi-batch failures |
| Record/replay | Commit sanitized request/response fixtures; replay only in CI | Compatibility with previously observed provider responses |
| Contract tests | Assert endpoint, auth, request shape, matching answer IDs, `noul ∈ [0,1]` | Protocol correctness; live calls still needed to detect provider drift |
| Scheduled canaries | Small labeled synthetic set, fixed call/token budget | Current service compatibility and pruning quality |

**VERIFIED tool capabilities:** Nock documents a strict replay mode:

> “lockdown: use recorded nocks, disables all http calls even when not nocked, doesn't record”

[Nock documentation](https://github.com/nock/nock#nock-back). Polly.js explicitly supports “Record, Replay, and Stub HTTP Interactions.” [Polly.js](https://github.com/Netflix/pollyjs). [MSW](https://github.com/mswjs/msw) is another option for reusable request handlers. **Recommendation:** Keep the existing injection/local-server approach unless recording adds useful coverage; verify any interception library against this repo’s native Node `fetch`.

Record once, remove credentials and private content, retain model/version metadata, and **fail on fixture misses**. Include synthetic responses around `0.50`/`0.70`, malformed JSON, missing answers, timeouts, and later-batch failures.

**VERIFIED mature-project example:** LangChain states:

> “We separate SDK unit and integration tests”

Its Deep Agents team also runs selected evaluation categories to control cost. [LangChain engineering account](https://www.langchain.com/blog/how-we-build-evals-for-deep-agents)

**Recommendation:** Run `npm run check` offline for every change; reserve live inference for targeted canaries. Twenty calls at 8K tokens each cost an estimated **$0.00672** in TypeSafe inference. Pin a version and judge labeled keep/drop outcomes rather than requiring identical floating-point scores. Replay proves proxy behavior; live labeled evaluations assess decision quality.