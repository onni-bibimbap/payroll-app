# EVALUATION PROTOCOL — how judging works here

Governs every LLM-judge evaluation: code reviews, request↔output conformance, I/O contract checks, security review, and project domain rules (§14). The judge's operating behavior lives in `agents/llm-judge.md`; this file owns the pipeline, schema, authority, and calibration.

## Principles
1. **Deterministic first, LLM second.** Machines verify what machines can verify; the judge rules only on what tools cannot (logic vs requirement, design soundness, domain correctness).
2. **Binary criteria + mandatory evidence.** No numeric scores — they drift. PASS/FAIL per criterion; every FAIL cites `file:line`, an AC id, or a sample id.
3. **Blind grading.** The judge sees requirement + artifact + tool output, never the builder's narrative.
4. **Judge ≠ generator.** Fresh subagent context always; different model tier where risk demands.
5. **Reason, then rule.** Chain-of-thought first, structured JSON verdict after; the JSON is the record.
6. **PII rule holds.** Synthetic fixtures only; real RESTRICTED data in a briefing is an immediate `SECURITY-FLAG`.

## Pipeline
```
change ready → deterministic pre-checks → green? → assemble briefing → judge (FAST or STRONG tier)
             → red: fix first                → verdict JSON → VERDICTS.jsonl + VERDICT log line
                                             → SHIP → COMPLETE may proceed
                                             → REVISE → back to generator ([EVAL i/3])
                                             → ESCALATE → STRONG tier or human
```

## Deterministic pre-check harness (run before every code judgment, in order)
1. Build / typecheck
2. Unit + integration tests (with AC-mapped test ids)
3. Lint + format
4. Dependency audit — critical/high CVEs fail
5. Secret scan
6. Targeted perf numbers when the change touches a budgeted surface (per performance_skills)

Package each as `{tool, command, exit_code, raw_tail}` in the briefing's `prechecks` block. Any red → fix before invoking the judge (conformance-only briefs with no code may skip 1–6). Reds on 4 or 5 also auto-FAIL the mapped security criteria (SR-7, SR-3) — no judge tokens needed to know a leaked secret is a leak.

## Verdict schema (one JSON object per line in `verdicts/VERDICTS.jsonl`)
```json
{
  "verdict_id": "V-0001",
  "timestamp": "2026-07-23T04:00:00Z",
  "orch": "ORCH-01",
  "target": { "ref": "FEAT-014", "artifact": "PR#42 / src/attendance/* / sample-set S-3" },
  "rubric": { "name": "code-quality", "version": "1.0" },
  "mode": "single | pairwise | reference",
  "tier": "FAST | STRONG",
  "judge_model": "<model id used>",
  "iteration": "EVAL 2/3",
  "prechecks": "green | red | n/a",
  "criteria": [
    { "id": "CQ-5", "result": "FAIL",
      "evidence": "src/attendance/dedup.ts:41 — retry re-inserts row; no idempotency key",
      "requires": "replay-safe upsert keyed on event id" }
  ],
  "overall": "SHIP | REVISE | ESCALATE",
  "confidence": "high | medium | low",
  "notes": ""
}
```

## Authority — binding FAIL
- An unresolved FAIL/REVISE verdict **blocks `COMPLETE`** on its target. The orchestrator cannot override.
- The only waiver is a human `DECISION` naming the specific criterion waived and the risk accepted; the waiver id goes into the next verdict's notes.
- Escalation ladder: FAST → one STRONG re-judgment → human. STRONG rulings are revisited only by human `DECISION`.
- `[EVAL]` iterations stay capped at 3 (per the orchestrator's mindset 6); iteration 3 failing → ESCALATE with all verdict ids.

## Rubric versioning
Rubrics live in `rubrics/` with a version header. Minor bump (1.0 → 1.1) for wording/evidence clarifications; major bump (1.x → 2.0) for adding/removing/redefining criteria. Every verdict pins the version it used. A major bump triggers re-calibration before the new version rules on anything on PROJECT_PROFILE §6 high-risk paths or §7 sensitive data.

## Calibration — judging the judge (rules; registry + logs live in `golden/GOLDEN_SET.md`)
- Maintain a golden set of 10–20 pre-judged items seeded from past human `DECISION` entries and the project's worked scenarios.
- **Agreement metric:** % of golden items where the judge's *overall* ruling matches the recorded human ruling. **Target ≥ 90%.**
- Re-baseline when: a rubric takes a major bump, the judge model for a tier changes, or agreement drops below target.
- Below target → freeze that rubric/tier pairing for PROJECT_PROFILE §6 high-risk or §7 sensitive-data targets, route those to STRONG or human, and review the failing golden items before unfreezing.
- Monthly spot-check: STRONG tier (or the human) re-judges ~10% of the month's FAST-tier SHIPs; disagreements become new golden items.
