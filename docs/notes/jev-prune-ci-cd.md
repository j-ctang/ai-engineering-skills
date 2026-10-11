# CI/CD for a local proxy

CI automatically checks proposed code changes. CD delivers a tested version
to users. For jev-prune, the running software is on the user's Mac; a release
or package is the delivery target. There is no shared production server to
deploy in this phase.

## The first pipeline

```text
PR to staging
  -> clean checkout and locked dependency installation
  -> prove external networking is disabled and loopback works
  -> lint, TypeScript build, all Jest tests
  -> independent review by the other model
  -> human review and merge
  -> human tests staging locally
  -> fast-forward the tested staging commit to main
```

The check job runs on GitHub-hosted Ubuntu. Action commits and the Node
container image are pinned. The workflow receives read-only repository
permission, does not retain checkout credentials, and uses a dummy TypeSafe
key. Dependency/image downloads happen before isolation. The full check
suite runs inside Docker with `--network none`, which retains loopback for
the proxy's local HTTP test servers.

Tests use injected API responses rather than live TypeSafe calls. A passing
check demonstrates the existing tests pass; it does not establish complete
coverage, real-provider compatibility, or reliable installation on every Mac.

Branch protection makes the check a merge requirement after the bootstrap
has been reviewed and landed. Until protection is configured, a red check
does not itself prevent an administrator from merging.

## What production-grade delivery would add

There is no universal checklist that makes a pipeline production-grade.
For this proxy, the meaningful additions are:

| Concern | Evidence or gate |
|---|---|
| Local compatibility | Check supported Node versions and macOS; smoke-test a clean installation and launch. |
| Proxy correctness | Exercise streaming, cancellation, shutdown, restart, malformed upstream responses, and pruning integrity with offline fixtures. |
| API compatibility | Separate scheduled live canary with a fixed budget and scoped credentials. Never require live API spend for ordinary PRs. |
| Supply-chain security | Triage dependency alerts, scan for committed secrets, and update pinned workflow/image dependencies through reviewed PRs. |
| Reproducible releases | Produce a versioned installable artifact from the approved commit, test that artifact, and attach checksums/provenance. |
| Controlled delivery | Human-approved release from tested main; document install, upgrade, and downgrade paths. |
| Recovery | Preserve previous releases and revert bad staging changes promptly. |
| Quality over time | Replay real failures as fixtures and track escaped bugs, reverts, and first-pass acceptance. |

These are later increments, not checks already delivered by Phase 1. The
first useful gate is the existing full suite, run predictably without paid
API calls. Release automation should follow a decision about how users
install jev-prune.

## Sources

- [GitHub: continuous integration](https://docs.github.com/en/actions/get-started/continuous-integration)
- [GitHub: continuous deployment](https://docs.github.com/en/actions/get-started/continuous-deployment)
- [GitHub: workflow security guidance](https://docs.github.com/en/code-security/tutorials/secure-your-organization/protect-against-threats)
- [Docker: none network driver](https://docs.docker.com/engine/network/drivers/none/)
