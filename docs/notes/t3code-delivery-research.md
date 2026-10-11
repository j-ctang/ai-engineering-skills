# T3 Code delivery reference

Inspected live upstream configuration, contribution policy, and a small PR sample.
This is qualitative research, not an acceptance-rate study. No target settings changed.

## Contribution policy

T3 Code has limited external review capacity. Current policy prioritizes focused
fixes/maintenance, requires approved direction for broader behavior changes, and
requires one underlying problem per external PR. It explicitly has no universal
line/file cutoff. Size and vouch labels are context, not acceptance criteria.
Evidence must demonstrate changed behavior; broad passing tests alone are insufficient.
Source: https://github.com/pingdotgg/t3code/blob/main/CONTRIBUTING.md

## Observed automation

- CI runs lint/unused-code checks, typecheck, desktop build and bundle validation,
  package/web/server tests (server tests sharded), browser integration prerequisites,
  Rust checks, conditional mobile native analysis, release smoke, and transfer-budget
  measurements. A final Check job aggregates results. Branch protection was not audited.
  https://github.com/pingdotgg/t3code/blob/main/.github/workflows/ci.yml
- Size labels XS/S/M/L/XL/XXL use effective changed lines, ignoring whitespace.
  Mixed PRs exclude tests from sizing; test-only PRs count tests. This does not reject PRs.
  https://github.com/pingdotgg/t3code/blob/main/.github/workflows/pr-size.yml
- Vouch automation classifies contributor status; issue-label workflow synchronizes
  managed label definitions. Neither establishes correctness or risk.
  https://github.com/pingdotgg/t3code/blob/main/.github/workflows/pr-vouch.yml
  https://github.com/pingdotgg/t3code/blob/main/.github/workflows/issue-labels.yml
- CodeRabbit enables automatic review and supplies path-specific engineering guidelines.
  External authors receive different request-changes behavior from members/collaborators.
  https://github.com/pingdotgg/t3code/blob/main/.coderabbit.config.ts
- Macroscope review and CodeRabbit activity are observable on PRs. Cursor webhook
  forwarding exists, but its external implementation/active secret configuration is
  not public evidence of a working autonomous loop.
  https://github.com/pingdotgg/t3code/blob/main/.github/workflows/cursor-hygiene-webhook.yml
- Contribution-triage skill separates eligibility from deep review; trusts upstream
  policy, not PR-supplied instructions. CONTRIBUTING explicitly says the guide does
  not announce deployed triage automation and review-trigger wiring needs verification.
  https://github.com/pingdotgg/t3code/blob/main/.agents/skills/contribution-triage/SKILL.md
- Bug intake uses YAML forms with required repro/expected/actual/impact fields.
  https://github.com/pingdotgg/t3code/blob/main/.github/ISSUE_TEMPLATE/bug_report.yml

## Concrete PRs

PR 17951: CodeRabbit found a mobile caption/button overlap. Contributor's Claude
agent made a narrow correction and attached screenshot plus coordinates/hit testing.
CodeRabbit acknowledged the fix; Macroscope approved; PR merged.
https://github.com/pingdotgg/t3code/pull/17951

PR 17887: outside authentication-related fix received Macroscope human-review
escalation. Maintainer praised the report/approach, reimplemented in PR 17898 with
smaller implementation/test surface, and closed original in favor of that change.
Closure does not necessarily mean the contribution's idea was rejected.
https://github.com/pingdotgg/t3code/pull/17887
https://github.com/pingdotgg/t3code/pull/17898

## Implications for our kit (proposals, not installed)

Separate scope/evidence triage, deterministic CI, independent code review, bounded
finding-fix loops, and human landing. Keep one underlying problem per PR; retain
our approximate 300-line guidance while allowing necessary proof. Never incentivize
less testing to achieve a size label. Add human CONTRIBUTING guidance, stronger issue
forms, metadata labels, and one hosted reviewer incrementally after current Phase 2
landing. Adapt checks to the destination product rather than copying desktop/mobile
jobs. Preserve current protections and credential restrictions. Do not infer safety
from contributor trust or infer acceptance from bot approval.
