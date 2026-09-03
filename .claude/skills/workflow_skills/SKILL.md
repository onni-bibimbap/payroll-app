---
name: workflow_skills
description: How every agent in this library fans work out to many sub-agents using Claude Code's Workflow tool ("ultracode"). Use whenever an orchestrator ASSIGN carries a mindset tag ([FANOUT], [PIPE], [HIER], [EVAL]), whenever uiux-designer or any skill must delegate to ≥ 3 lens agents, and whenever a task is a sweep, audit, review, migration, or design that one context cannot hold. Maps the six distribution mindsets to deterministic workflow scripts and fixes the verification and budget rules.
---

# Workflow skills — deterministic fan-out with the Workflow tool

Agents in this library never single-thread substantive work. The orchestrator's six mindsets (`agents/orchestrator.md`) are executed with Claude Code's **Workflow** tool — a JavaScript script that spawns sub-agents deterministically (`agent()`, `pipeline()`, `parallel()`, `phase()`). "Ultracode" is the user's standing opt-in: when it is on, every substantive task runs as a workflow by default.

## When a workflow is mandatory
- Any `ASSIGN` tagged `[FANOUT]`, `[PIPE]`, `[HIER]`, or `[EVAL]`.
- Any UI task (uiux-designer requires ≥ 3 lens agents; the orchestrator may run 10+).
- Any review, audit, security scan, or migration touching more than ~5 files.
- Any design decision with a wide solution space (use a judge panel).

Opt-in rule: the Workflow tool spends many agents. Call it when the user said "ultracode", "use a workflow", or asked for multi-agent work in their own words, when ultracode is on for the session, or when a skill in this library instructs it (this file counts). Otherwise describe the fan-out and its rough cost and let the human decide.

## Mindset → script shape
| Tag | Shape | Script primitive |
|---|---|---|
| `[PIPE]` | forced order per item | `pipeline(items, s1, s2, s3)` — no barrier; item A can be in s3 while B is in s1 |
| `[ROUTE]` | one specialist | single `agent(prompt, {agentType: 'uiux-designer' | 'llm-judge'})` |
| `[FANOUT]` | independent slices | `parallel(items.map(i => () => agent(...)))`; pairwise winners picked by llm-judge |
| `[SUPER]` | emergent | scout inline first to get the work-list, then `pipeline()` over it |
| `[HIER]` | sub-scopes | `workflow('<saved-name>', args)` per child scope (one nesting level) |
| `[EVAL]` | generate → judge, ≤ 3 loops | `for (let i = 0; i < 3; i++) { draft = agent(...); verdict = agent(judge, {schema}) ; if (verdict.ship) break }` |

Default to `pipeline()`. Use `parallel()` only when a stage needs every prior result at once (dedup, early exit on zero findings, cross-comparison).

## Script rules
1. Start with a pure-literal `export const meta = { name, description, phases }`; phase titles match `phase()` calls exactly.
2. Plain JavaScript, no TypeScript, no `Date.now()` / `Math.random()`; pass timestamps via `args`.
3. Every finder returns a `schema` (JSON Schema) so results are validated objects, never parsed prose.
4. `.filter(Boolean)` every `parallel()` result — a skipped or dead agent is `null`.
5. Name every agent with `label` and `phase` so the progress tree reads like the ORCHESTRATION_LOG.
6. Use `isolation: 'worktree'` only when agents mutate files concurrently.
7. Log what was dropped (`log()`), never truncate silently.
8. Scale by ask: quick check → few finders, single vote; "thorough / audit / comprehensive" → larger pool, 3–5 vote adversarial verify, synthesis stage. Respect `budget.remaining()` when a token target is set.

## Verification is part of the workflow
No finding leaves a workflow unverified. Minimum: **adversarial verify** — 3 independent refuters per finding, keep only if ≥ 2 fail to refute. Use **perspective-diverse verify** (correctness / security / performance / reproduces) when a finding can fail in more than one way. Finish with a **completeness critic** agent ("what modality was not run, claim not verified, file not read?") whose output seeds the next round. For unknown-size discovery use **loop-until-dry** (stop after 2 empty rounds). Judge stages call `llm-judge` with a named, versioned rubric from `evaluation/rubrics/` and the tier from `PROJECT_PROFILE.md §15`.

## Canonical scripts

Review a change set (`[FANOUT]` → verify):
```js
export const meta = { name: 'review-changes', description: 'Review changed files across dimensions, verify each finding',
  phases: [{ title: 'Review' }, { title: 'Verify' }] }
const DIMS = [{key:'correctness', prompt:'...'}, {key:'security', prompt:'...'}, {key:'performance', prompt:'...'}]
const results = await pipeline(DIMS,
  d => agent(d.prompt, {label:`review:${d.key}`, phase:'Review', schema: FINDINGS}),
  r => parallel((r?.findings ?? []).map(f => () =>
    agent(`Try to refute: ${f.title}. Default refuted=true if uncertain.`, {label:`verify:${f.file}`, phase:'Verify', schema: VERDICT})
      .then(v => ({...f, verdict: v})))))
return { confirmed: results.flat().filter(Boolean).filter(f => f.verdict && !f.verdict.refuted) }
```

UI feature design (uiux-designer, ≥ 3 lenses → merge → rubric):
```js
export const meta = { name: 'ui-spec', description: 'Design one feature page through independent lenses, merge, judge',
  phases: [{ title: 'Lenses' }, { title: 'Merge' }, { title: 'Judge' }] }
const LENSES = ['IA & navigation', 'page template & states', 'tokens, components & accessibility', 'sensitive data', 'performance']
const views = (await parallel(LENSES.map(l => () =>
  agent(`As uiux-designer, lens "${l}": design ${args.feature}. Return ≤ 400 words.`, {label:`lens:${l}`, phase:'Lenses', agentType:'uiux-designer'})))).filter(Boolean)
const spec = await agent(`Merge these lens outputs into one UI Spec per the template:\n${views.join('\n---\n')}`, {phase:'Merge', agentType:'uiux-designer'})
const verdict = await agent(`Judge this UI Spec against rubric ui-shell v1.0:\n${spec}`, {phase:'Judge', agentType:'llm-judge', schema: VERDICT})
return { spec, verdict }
```

## Logging
Every workflow run is one `ASSIGN` in `ORCHESTRATION_LOG.md` with the mindset tag, the number of agents, the lenses or dimensions, and the run id; its verified output is the `COMPLETE` evidence. Resume a paused or edited run with `resumeFromRunId` rather than re-spending the agents.
