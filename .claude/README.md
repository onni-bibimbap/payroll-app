# .claude — Agent Operating System

The execution and governance layer for every project. Domain knowledge lives in each project's `.claude/PROJECT_PROFILE.md` (generated from the project's PRD per `features_skills` § Project Binding) and the project's `.claude/domain/<category>/<area>.md` files (captured per `domain_skills`), plus any project-specific skills it lists in §16; this layer defines **how agents build, how they are judged, and how they coordinate**.

## Layout
```
.claude/
├── skills/
│   ├── features_skills/SKILL.md      # BA + chief tester — requirements met, tested, SHIP/HOLD
│   ├── performance_skills/SKILL.md   # workflows, pipelines, req/resp, load/unload, responsiveness,
│   │                                 #   all latency + Scale Ladder (restructure = propose-only)
│   └── security_skills/SKILL.md      # TRIAL relaxed baseline / PROD hard gate — never compromisable
│   ├── workflow_skills/SKILL.md      # Workflow-tool (ultracode) fan-out: mindsets → scripts, verify rules
│   ├── domain_skills/SKILL.md        # capture every domain fact into domain/<category>/<area>.md
│   └── infra_skills/SKILL.md         # Docker Compose by default; all state persistent in PostgreSQL on named volumes
├── agents/
│   ├── orchestrator.md               # spawnable template → ORCH-01 … ORCH-N; 6 distribution mindsets
│   ├── llm-judge.md                  # independent judge — blind, evidence-bound, FAIL blocks COMPLETE
│   └── uiux-designer.md              # console-shell doctrine + Shell Growth Ladder SH0–SH4
├── evaluation/
│   ├── EVALUATION_PROTOCOL.md        # pipeline, verdict schema, authority, calibration rules
│   ├── rubrics/                      # code-quality · requirements-conformance · io-contract ·
│   │                                 #   security-review · domain · ui-shell (versioned, binary+evidence)
│   ├── golden/GOLDEN_SET.md          # calibration & regression references (synthetic data only)
│   └── verdicts/VERDICTS.jsonl       # append-only verdict ledger
├── domain/                           # per-project domain knowledge by category/area (empty in the library)
│   └── README.md                     # index — one line per file
├── orchestration/
│   └── ORCHESTRATION_LOG.md          # the base log — single coordination bus, append-only
└── README.md
```

## The three gates (every feature, every project)
1. **features_skills** — a written FEAT-### requirement exists, every acceptance criterion is tested, verdict is SHIP.
2. **performance_skills** — latency budgets met on every surface, with evidence; load-tested at 2× peak before prod.
3. **security_skills** — TRIAL baseline for trials (synthetic data only), full hard gate for any production release.

No agent marks anything COMPLETE without all three. Every project runs on the `infra_skills` default stack — `docker compose up` with PostgreSQL on named volumes — and `make up` / `make test` are pre-checks for all three gates. UIUX design is not a gate — it's the `uiux-designer` agent's doctrine, applied whenever screens change. Fan-out itself is governed by `workflow_skills`: every mindset-tagged ASSIGN runs as a Workflow script with adversarial verification.

## The judge
Acceptance runs through `llm-judge`: deterministic pre-checks first (tests, scans, lint — machines verify what machines can), then a blind, evidence-bound judgment against a versioned rubric. Rulings are SHIP / REVISE / ESCALATE, and **FAIL blocks COMPLETE** — no orchestrator override; only a human `DECISION` waiver. Models are tiered by risk: FAST for routine conformance, STRONG (always) for PROJECT_PROFILE §6 high-risk paths, §7 sensitive data, and security, with an escalation ladder of FAST → STRONG → human. The judge is calibrated against a golden set (target ≥ 90% agreement with human rulings) and never fixes code.

## Governance — propose-only
Orchestrators and agents may execute freely *inside their claimed scope*, but may only **propose** structural change: `RESTRUCTURE` (Scale Ladder climbs, extractions), `UIUX-UPGRADE` (Shell Growth Ladder level changes; new template, component, or shell-region proposals), and security-gate exceptions. Proposals sit in the log as `PENDING-APPROVAL` until the human writes a `DECISION`. Approved restructures are recorded as ADRs and migrated incrementally.

## Spawning orchestrators
Spawn one per workstream, as many in parallel as needed:
> "Act as an orchestrator per `.claude/agents/orchestrator.md`. Mission: <goal>. Scope: <contexts/dirs/features>."

Each instance claims the next `ORCH-NN`, registers its scope in the log (first valid claim wins), and coordinates with siblings **only** through `ORCHESTRATION_LOG.md`.

When distributing tasks, every orchestrator chooses among **six mindsets** per work package and tags each `ASSIGN` with the mode: **Sequential Pipeline** `[PIPE]` (forced order), **Routing Handoff** `[ROUTE]` (one clear specialist), **Parallel Fan-out** `[FANOUT]` (independent + fast; sampling winners picked by the judge pairwise), **Supervisor/Workers** `[SUPER]` (emergent shape — the default), **Hierarchical** `[HIER]` (spawn child orchestrators for sub-scopes), **Evaluator-Optimizer** `[EVAL]` (generate→judge loops, capped at 3). Details and selection guide in `agents/orchestrator.md`.

## A mission, end to end
Spawn → CLAIM scope → decompose into FEAT-### with a mindset per package (BA hat) → ASSIGN workers (mode-tagged) → build → pre-checks → llm-judge VERDICTs → three gates verify → COMPLETE with verdict ids → any fired triggers become PENDING-APPROVAL proposals → human DECISIONs → CLOSE with summary.
