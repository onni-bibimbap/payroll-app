# Rubric: ui-shell (v1.0)
Mode default: single-artifact — run on every UI Spec before build and on every UI feature COMPLETE · Tier: FAST (STRONG when §7 sensitive fields appear on screen or UI-7/UI-8 fail) · Evidence on FAIL: the spec line or file:line quoted, mandatory. Source: `agents/uiux-designer.md` § UI review rubric.

| ID | Criterion — PASS means |
|---|---|
| UI-1 | Exactly one template (T1–T6) named per page; the page structure matches it and none of its forbids |
| UI-2 | Sidebar section/position follow the ordering rule (frequency, then lifecycle); no new section without a DECISION |
| UI-3 | Badge, if any, is New (≤ 30 d), Beta, or an attention count |
| UI-4 | Route mirrors the sidebar; ⌘K "Go to" + per-action entries registered |
| UI-5 | Labels use the project vocabulary, or placeholders are flagged (`Profile: ABSENT`) |
| UI-6 | All four states (loading, empty, error, populated) specified and implemented, with copy |
| UI-7 | §7 fields masked by default and absent from list/export/notification — or an explicit human DECISION covers the exception |
| UI-8 | Role visibility and device class declared and enforced |
| UI-9 | Virtualization / lazy-loading applied where thresholds are met; teardown on route change |
| UI-10 | Shell Growth counts recorded; UIUX-UPGRADE logged if a trigger fired |
| UI-11 | Only closed-set components and tokens used (or a logged, approved UIUX-UPGRADE for each addition) |
| UI-12 | ≥ 3 lenses delegated and listed in the spec |
