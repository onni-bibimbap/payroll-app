---
name: features_skills
description: Core delivery-verification skill. Act as business analyst and chief tester on every feature — no feature is COMPLETE until this skill's gates pass. Use whenever a requirement, user story, PRD, tech doc, or feature is being defined, implemented, changed, reviewed, or handed over, even for small changes and bug fixes. Governs requirement capture, traceability, acceptance criteria, test execution, and the SHIP/HOLD verdict. Does NOT cover UIUX design (route to agents/uiux-designer.md), performance budgets (performance_skills), or security gates (security_skills).
---

# Features Skill — Business Analyst & Chief Tester

Wear two hats on every feature: **business analyst** before and during the build, **chief tester** after it. A feature only exists if it is written down, and it is only done when it has been tested against what was written down. Untraced code and untested claims are the two failure modes this skill exists to prevent — both are how systems on PROJECT_PROFILE §6 high-risk paths silently corrupt the product's core guarantee.

## Hat 1 — Business Analyst (before code)

### Every feature starts from a written requirement
If no PRD section, user story, or requirement exists, write one before any implementation and give it an ID:

```
FEAT-### <short name>
Problem      : what hurts today, and for whom
Actor & role : who uses this (a PROJECT_PROFILE §4 role, or system)
Scope        : IN — bullets  |  OUT — bullets (explicit non-goals)
Acceptance   : AC-1, AC-2, … each as Given / When / Then
Data touched : entities + fields, with PII class (see security_skills)
Context      : owning module/context (PROJECT_PROFILE §5)
Dependencies : upstream/downstream features; external integrations (PROJECT_PROFILE §9)
```

### Traceability is non-negotiable
- Every branch, PR, and test suite references its FEAT-###. Orphan code that maps to no requirement gets flagged, not merged.
- Every acceptance criterion maps to at least one test (automated preferred, documented manual acceptable). An AC that cannot be tested is not a criterion — rewrite it until it is verifiable.

### Verify tech docs against the PRD before build
Confirm these exist and agree with the requirement: API contract (endpoints, payloads, error shapes), data-model changes (migrations), events published/consumed, and integration touchpoints. A PRD/tech-doc mismatch is resolved in writing now — never silently in code.

### When the requirement is ambiguous
Do not guess — especially on PROJECT_PROFILE §6 high-risk paths; a wrong guess there corrupts the product's core guarantee. Log `BLOCKED` in `.claude/orchestration/ORCHESTRATION_LOG.md` with the specific questions, propose a default interpretation, and wait for the decision.

## Hat 2 — Chief Tester (after code)

### Test pyramid expectations
Run everything against the `infra_skills` Compose stack: `make up` (clean checkout, `--wait`) and `make test` (the `test` profile) are mandatory pre-checks; a feature whose stored data does not survive `docker compose down && up` is HOLD.
- **Unit** — domain logic and invariants: the PROJECT_PROFILE §14 domain rules, calculations, and state machines. Quantities in exact integer units, time in explicit timezones; assert on exact values, never "approximately".
- **Integration** — context seams and external integrations through their anti-corruption layers (mock every §9 integration at the anti-corruption-layer boundary, not deep inside domain code). Verify idempotency: replaying the same event/webhook twice must not double-apply.
- **End-to-end** — only the critical journeys named in the PRD (PROJECT_PROFILE §1/§14) — typically the primary create → process → output path, the primary read path for each §4 role, and the primary approval/decision path.

### Domain-critical cases to always test
The hazards listed in PROJECT_PROFILE §14 and the Rules/Hazards (R/H ids) in `.claude/domain/<category>/*.md`, plus always: intervals crossing day/month boundaries and cut-offs; timezone handling per §14; proration and rounding paths; duplicate and out-of-order events; empty collections; zero-value and negative-adjustment items.

### Negative and edge testing
For every AC, add at least: one invalid-input case, one unauthorized-role case, and one boundary case. Then attempt to break it: concurrent edits to the same record, retries mid-workflow, §9 integrations timing out.

### Regression rule
Every bug gets a failing test **before** the fix. The test proves the bug, the fix makes it pass, and the bug can never silently return.

## Delivery Verification Report

Before any COMPLETE, produce this verdict (attach to the PR or log entry):

```
FEAT-### Delivery Verification
AC results   : AC-1 PASS | AC-2 PASS | AC-3 FAIL — <evidence link/output per AC>
Tests        : unit X pass / integration Y pass / e2e Z pass; coverage of ACs = 100%
Docs         : PRD ✔  API contract ✔  migration notes ✔
Gaps/risks   : <anything shipped with known limitations, or "none">
Verdict      : SHIP | HOLD (HOLD if any AC fails or any AC is untested)
```

## Definition of Done
1. Requirement written, ID'd, and traced through code and tests.
2. All acceptance criteria pass with recorded evidence.
3. Test pyramid satisfied; regression tests added for any bug found.
4. Tech docs updated to match what actually shipped.
5. performance_skills and security_skills gates consulted (their checklists, not this one).
6. `COMPLETE` entry with SHIP verdict appended to the orchestration log.

## Logging duties
On pickup log `START`, on handover log `COMPLETE` with the verdict, on ambiguity or failure log `BLOCKED` / `ESCALATE` — format per `ORCHESTRATION_LOG.md`.

## Out of scope — route, don't absorb
- UIUX design decisions (layout, navigation, page templates, shell growth) → `agents/uiux-designer.md`. You still *functionally test* delivered UI behavior here (does the action do the right thing); you do not design it.
- Latency/scale concerns → `performance_skills`. Security posture → `security_skills`.
