# ORCHESTRATION LOG — single source of truth

This file is the **only coordination bus** between orchestrators, worker agents, the llm-judge, and the human. If it isn't logged here, it didn't happen.

## Protocol
1. **Append-only.** Never edit or delete an existing entry — correct with a new entry referencing the old one.
2. Every orchestrator registers here on spawn (`SPAWN` + `CLAIM`) before doing anything else.
3. Structural changes are **propose-only**: `RESTRUCTURE`, `UIUX-UPGRADE`, and security-gate exceptions enter as `PENDING-APPROVAL` and act only after a human `DECISION` marks them APPROVED.
4. Entries carry evidence (numbers, refs), not adjectives.
5. `ASSIGN` details lead with a distribution mode tag — `[PIPE n/N]` `[ROUTE→agent]` `[FANOUT xN]` `[SUPER]` `[HIER→ORCH-NN]` `[EVAL i/max]` — per the orchestrator's six mindsets. Hierarchical children register like any orchestrator, with `parent=ORCH-XX` noted in their Scope.
6. **Judge verdicts are binding.** An unresolved FAIL/REVISE `VERDICT` blocks `COMPLETE` on its target; orchestrators cannot override. The only waiver is a human `DECISION` naming the criterion. Full verdict JSON lives in `.claude/evaluation/verdicts/VERDICTS.jsonl`; this log carries the one-line summary with the V-### ref.

**Entry format** — one line per event:
```
| <UTC ISO timestamp> | <ORCH-ID> | <agent or -> | <EVENT> | <ref or -> | <detail> | <status> |
```

**Event vocabulary**

| Event | Meaning |
|---|---|
| SPAWN / CLOSE | Orchestrator instance starts / ends its mission |
| CLAIM | Scope or shared-asset ownership claimed (first valid claim wins) |
| ASSIGN / START / COMPLETE | Task given to a worker / work begun / done with verdict + gate evidence |
| VERDICT | llm-judge ruling — SHIP / REVISE / ESCALATE with rubric, tier, and V-### ref; FAIL blocks COMPLETE |
| BLOCKED | Work stopped — specific questions or failure attached |
| ESCALATE | Needs the human or crosses another orchestrator's scope |
| DECISION | A recorded choice — human approvals/rejections/waivers use this event |
| RESTRUCTURE | Scale Ladder / architecture change proposal (propose-only, + ADR ref) |
| UIUX-UPGRADE | Shell Growth Ladder (SH0–SH4) level change, or new template/component/shell-region proposal (propose-only) |
| DOMAIN | Domain knowledge captured into `domain/<category>/<area>.md` (per domain_skills) |
| INFRA | Compose/datastore scaffold or change (per infra_skills) |
| SECURITY-FLAG | Security gate failure or exception request — blocks release |

---

## Orchestrator Registry

| ORCH-ID | Scope | Spawned (UTC) | Status | Closed (UTC) |
|---|---|---|---|---|
| ORCH-01 | Payroll 2.0 revamp — whole repo: backend/, ui/, supabase/, compose/infra, docs, tests (webapp/ = read-only reference) | 2026-09-03T14:30Z | ACTIVE | — |

---

## Pending Approvals (awaiting human DECISION)

| Entry ref (timestamp) | Type | Summary | Status |
|---|---|---|---|
| 2026-09-03T14:42Z | SECURITY-FLAG | Real employee PII tracked in git (xlsx/db/sql); trial builds default to prod Supabase DATABASE_URL | PENDING-APPROVAL |

---

## Decision Record

| Date | Ref | Decision | Decided by |
|---|---|---|---|
| 2026-07-23 | GENESIS | Governance adopted: 3 core skills gate every feature; orchestrators propose-only on RESTRUCTURE / UIUX-UPGRADE / security exceptions | Human (Head of AI Solutions) |
| 2026-07-23 | GENESIS-2 | Six distribution mindsets adopted (PIPE, ROUTE, FANOUT, SUPER, HIER, EVAL); ASSIGN entries carry mode tags | Human (Head of AI Solutions) |
| 2026-07-23 | GENESIS-3 | llm-judge adopted: FAIL blocks COMPLETE; tiered models (FAST routine / STRONG for §6 high-risk paths, §7 sensitive data, security); calibration target ≥90% agreement | Human (Head of AI Solutions) |

---

## Activity Log (append below — newest last)

| Timestamp (UTC) | ORCH | Agent | EVENT | Ref | Detail | Status |
|---|---|---|---|---|---|---|
| 2026-07-23T00:00Z | - | - | DECISION | GENESIS | Log initialized; protocol above in force | ACTIVE |
| 2026-09-03T14:30Z | ORCH-01 | - | SPAWN | - | mission: revamp payroll app to Payroll 2.0 — audit everything, fix every item, pass 3 gates | ACTIVE |
| 2026-09-03T14:31Z | ORCH-01 | - | CLAIM | - | scope: whole repo (backend/, ui/, supabase/, compose, docs, tests); webapp/ read-only reference; no sibling claims exist | ACTIVE |
| 2026-09-03T14:32Z | ORCH-01 | - | START | - | boot: 6 skills read; PRD (prompt/agent-prompt-employee-db-pwa.md), READMEs, statutory core, compose read; PROJECT_PROFILE.md + domain/ missing → binding first | ACTIVE |
| 2026-09-03T14:40Z | ORCH-01 | - | DOMAIN | - | .claude/PROJECT_PROFILE.md generated (§1–§16) from PRD + README + code | DONE |
| 2026-09-03T14:41Z | ORCH-01 | - | DOMAIN | - | payroll/statutory.md (R1–R7,H1–H6,W1–W3) · payroll/runs-and-exports.md · employee-master/lifecycle.md · _shared/{glossary,actors,integrations,compliance}.md · index updated | DONE |
| 2026-09-03T14:42Z | ORCH-01 | - | SECURITY-FLAG | - | REAL employee PII git-tracked: *.xlsx (registrations, monthly payrolls), webapp/payroll.db, backups/*.sql+.db; default DATABASE_URL targets prod Supabase in trial builds — violates TRIAL tier rules 1; remediation (history rewrite / untrack) needs human DECISION | PENDING-APPROVAL |
| 2026-09-03T14:45Z | ORCH-01 | workflow wf_aae45b23-c85 | ASSIGN | - | [FANOUT x6] payroll2-audit: dims STAT/SEC/INFRA/DATA/QUAL/UI → 2 adversarial refuters per dim batch → completeness critic (~19 agents) | ASSIGNED |
| 2026-09-03T15:08Z | ORCH-01 | workflow wf_aae45b23-c85 | COMPLETE | - | audit done: 93 verified findings (83 confirmed 2/2 refuters, 10 critic gaps, 0 plausible); 19 agents, 1.76M tokens; inventory docs/audit-findings-2026-09-03.json; worklog ERR-004..096 | DONE |
| 2026-09-03T15:12Z | ORCH-01 | - | DECISION | - | plan: FEAT-001 statutory engine [PIPE 1/3] → FEAT-002 run integrity [PIPE 2/3] → FEAT-003 security+HR/data [PIPE 3/3]; FEAT-004 infra + FEAT-005 frontend [FANOUT x2] parallel to the pipe (disjoint files); FEAT-006 docs/traceability after. Proration policy default: calendar-day (worklog DEC-006). Payroll tables stay NUMERIC(12,2) RM (sen unification = proposal P-3) | ACTIVE |
| 2026-09-03T15:12Z | ORCH-01 | - | UIUX-UPGRADE | GAP-05 | P-2: PRD role model (staff self-service, outlet-scoped manager) unimplemented — new product scope, propose as Payroll 2.1 | PENDING-APPROVAL |
| 2026-09-03T15:12Z | ORCH-01 | - | RESTRUCTURE | STAT-15 | P-3: unify payroll tables to integer sen (currently NUMERIC(12,2) RM — exact on Postgres, only SQLite floats); big migration + UI blast radius | PENDING-APPROVAL |
| 2026-09-03T15:12Z | ORCH-01 | - | RESTRUCTURE | QT-09 | P-4: delete legacy engine copies (webapp/, build_payroll.py) after PII scrub — 3 diverged statutory implementations today | PENDING-APPROVAL |
| 2026-09-03T15:14Z | ORCH-01 | wf backend-1 | ASSIGN | FEAT-001 | [PIPE 1/3] statutory engine: STAT-01/02/03/05/06, GAP-01, QT-01/02 + pyproject + tests/ harness + golden tests | ASSIGNED |
| 2026-09-03T15:14Z | ORCH-01 | wf backend-2 | ASSIGN | FEAT-002 | [PIPE 2/3] run integrity: STAT-07/08/09/10/11/12/13/14, DL-01/04/08/11/15, SEC-06, QT-05/07, GAP-03/10 + migration + tests | ASSIGNED |
| 2026-09-03T15:14Z | ORCH-01 | wf backend-3 | ASSIGN | FEAT-003 | [PIPE 3/3] security+HR/data: SEC-01/02/03/04/05/07/08/11/13/14, DL-02/03/05/06/12/13/14/16, QT-06/08/10/11/12/13/14, GAP-02/06, INFRA-04(code)/11(code) + migration + tests | ASSIGNED |
| 2026-09-03T15:14Z | ORCH-01 | wf infra | ASSIGN | FEAT-004 | [FANOUT x2] infra: INFRA-01/02/03/05/06/07/08/09/10/12/13, SEC-09/10, FE-10, GAP-07 (untrack PII + synthetic seeds; history rewrite stays P-1) | ASSIGNED |
| 2026-09-03T15:14Z | ORCH-01 | wf frontend | ASSIGN | FEAT-005 | [FANOUT x2] frontend/PWA: FE-01..09/11/13, SEC-12, GAP-06(UI) — no shell/template changes (no UIUX-UPGRADE trigger) | ASSIGNED |
