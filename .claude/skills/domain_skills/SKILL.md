---
name: domain_skills
description: Domain knowledge capture and reuse. Every agent must record what it learns about a project's domain — rules, hazards, vocabulary, integrations, worked scenarios, decisions, and lessons from failures — into `.claude/domain/<category>/<area>.md`, organised by category and area, and must read the relevant domain files before working in that area. Use whenever a PRD is read, a PROJECT_PROFILE is generated, a DECISION is logged, a BLOCKED question is resolved, a judge FAILs on a domain rule, or an agent discovers a fact that a competent engineer without domain background would get wrong.
---

# Domain skills — capture every domain fact where the next agent will find it

The library is domain-agnostic; **projects are not**. Everything an agent learns about a project's domain is written to `.claude/domain/` so no agent relearns it and no fact lives only in one conversation. `PROJECT_PROFILE.md` stays the short index; `.claude/domain/` holds the depth.

## Layout
```
.claude/domain/
├── README.md                     # index: one line per file, grouped by category
├── <category>/                   # a job-to-be-done or bounded area of the business
│   ├── <area>.md                 # one topic: rules, hazards, examples, sources
│   └── ...
└── _shared/                      # cross-category: glossary, actors, integrations, compliance
    ├── glossary.md               # ubiquitous language (mirrors PROJECT_PROFILE §3, fuller)
    ├── actors.md                 # roles, devices, frequency, what each must never see
    ├── integrations.md           # each external system: contract, auth, quirks, mocks
    └── compliance.md             # regimes, retention, jurisdictions, unresolved questions
```
Categories are named in the project's own vocabulary (§3), by job-to-be-done — the same grouping the console sidebar uses — never by team or tech layer. Examples of shapes, not names to copy: `billing/`, `scheduling/`, `conversation/`, `fleet/`, `evaluation/`. A category with one file is fine; a file over ~400 lines splits into two areas.

## File contract — every `<area>.md`
```markdown
# <Area> — <category>
Sources: <PRD §, doc, URL, DECISION id> · Last verified: <date> · Owner role: <§4 role>

## Rules (what must always hold)
- R1 <rule> — why · worked example · test that proves it (`tests/...`)
## Hazards (what competent outsiders get wrong)
- H1 <hazard> → correct behaviour · reference
## Vocabulary
| term | means | never confuse with |
## Worked scenarios
| id | input | expected output | source |
## Decisions & open questions
- DECISION-<id> <date> <summary>
- OPEN-<n> <question> · blocks: <FEAT-###>
## Lessons (from FAILs, incidents, replays)
- L1 <date> what broke · root cause · rule/test added
```
Every statement carries a tag: `[confirmed]` (source cited), `[derived]` (inferred, say from what), or `[assumed]` (must be confirmed before it gates anything). Nothing `[assumed]` may seed a rubric row or a golden scenario.

## When to write (mandatory triggers)
| Trigger | Write |
|---|---|
| PRD or spec read | `_shared/glossary.md`, `actors.md`, `integrations.md`, `compliance.md`; one `<area>.md` per major topic |
| PROJECT_PROFILE generated or re-derived | link every §14 rule to its `domain/` file; §16 lists this folder |
| Human `DECISION` logged | append to the area's Decisions; update any rule it changes |
| `BLOCKED` question resolved | move OPEN-n to Decisions with the answer and source |
| llm-judge FAIL on `domain` rubric | add a Lesson + the rule/test that now prevents it |
| Incident, bad replay, or user complaint | add a Lesson with root cause |
| Any agent discovers a non-obvious fact | add it, tagged, with source — even mid-task |

## When to read (mandatory)
Before any FEAT-### touching a category, read its `<area>.md` files and `_shared/*`; cite the rule ids (R/H) in the FEAT's acceptance criteria and in the UI Spec. A worker that cannot find a relevant domain file states so in its `ASSIGN` reply, and the orchestrator opens a capture task before build.

## How it feeds the rest of the library
- `features_skills`: acceptance criteria reference R/H ids; hazards seed the edge-case list.
- `evaluation/rubrics/domain.md`: DM rows are instantiated from Rules; goldens from Worked scenarios.
- `security_skills`: `_shared/compliance.md` and `actors.md` define §7/§8 masking and retention.
- `uiux-designer`: `_shared/glossary.md` supplies every on-screen label; categories mirror sidebar sections.
- `performance_skills`: peak events and business-critical windows come from the relevant area's Rules.

## Quality rules
- One fact, one place: `PROJECT_PROFILE.md` summarises and links; it never duplicates a rule body.
- Cite or tag; never write bare assertions.
- Synthetic examples only — no real customer, employee, or end-user data in worked scenarios.
- Keep `README.md` index current: a file not in the index does not exist to other agents.
- Delete or mark `[superseded by DECISION-id]`; never silently rewrite history.
- Capture is logged: each write is a `DOMAIN` entry in `ORCHESTRATION_LOG.md` (`DOMAIN | date | <category>/<area> | added R3, H2 | source`).
