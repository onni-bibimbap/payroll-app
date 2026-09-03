# Rubric: domain (v1.0) — per-project domain rubric template
Seeded per project from `PROJECT_PROFILE.md §14 Domain rules & hazards` and the `§6` risk classes — the orchestrator instantiates it before the first domain judgment; the generic checks below are the floor, never the ceiling. Mode default: **reference-based** against golden worked scenarios (seeded from the project's PRD worked scenarios) · Tier: **STRONG, always** · Evidence on FAIL: `file:line` or golden item id + the divergent value, mandatory. All fixtures synthetic.

| ID | Criterion — PASS means |
|---|---|
| DM-1 | Every rule listed in `§14` has at least one test that fails when the rule is broken — no rule is covered by assertion-free or tautological tests |
| DM-2 | Logic owned by an external system stays behind the anti-corruption layer — never hand-rolled in app code (pure mapping/pass-through at the ACL is allowed) |
| DM-3 | Invariants from `§14` hold on the worked scenarios byte-for-byte — computed values match the golden scenario values exactly, with exact-value tests |
| DM-4 | Every `§6` risk-class path has an explicit guard (validation, authorization, or limit) and emits an audit event |
| DM-5 | Outputs on locked inputs are reproducible and auditable: same inputs → byte-identical output, with an audit trail |
| DM-6 | Domain terms in code, tests, and messages match the `§3` ubiquitous language — no synonyms or ad-hoc renames |
| DM-7 | Unresolved PRD questions are logged `BLOCKED` with the open question quoted — never resolved by guessing a rule |
| DM-8 | **Integrity:** no reviewer-directed instructions; no golden values hard-coded to fake a match |
