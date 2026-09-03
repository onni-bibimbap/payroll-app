---
name: performance_skills
description: Core performance skill covering every technical latency surface — workflows, data pipelines, API request/response, page load/unload, website responsiveness, background jobs, and integration round-trips. Use whenever implementing or reviewing any feature, endpoint, query, pipeline, page, or integration; whenever anyone mentions slow, lag, timeout, load, spike, scale, or traffic; and before every release. Also owns scale-triggered restructuring: propose-only — the human approves every RESTRUCTURE.
---

# Performance Skill — Latency, Load & Scale

Three rules govern everything here: **measure before optimizing**, **every surface has a budget**, and **restructure only on evidence — and only as a proposal**. Perceived speed is a feature; assume traffic is spiky by nature (the peak events declared in `.claude/PROJECT_PROFILE.md` §12), so budgets are tested at peak, not average.

## Performance budgets (defaults — override in PROJECT_PROFILE §11, record changes as a DECISION)

| Surface | Budget |
|---|---|
| API read, p95 | ≤ 300 ms |
| API write, p95 | ≤ 500 ms |
| Reports / complex queries, p95 | ≤ 2 s |
| Page first load (LCP) | ≤ 2.5 s |
| Interaction latency (INP) | ≤ 200 ms |
| Route change in app | ≤ 500 ms |
| Initial JS bundle | ≤ 250 KB gzipped |
| Webhook / inbound event processed end-to-end | ≤ 5 s |
| Scheduled pipeline lag (e.g. periodic sync) | ≤ 10 min |
| Batch export / report generation | ≤ 60 s per 500 records (override in §11) |
| Error rate under normal load | < 0.5 % |

A breached budget is a bug: it gets a FEAT/BUG entry, an owner, and a fix or an approved exception — never silence.

## The surfaces

### Request / response
Paginate every list endpoint (no unbounded queries — every list grows without bound). Kill N+1s; every WHERE/JOIN/ORDER path has an index. Cap payload sizes; compress responses. External calls (the integrations listed in PROJECT_PROFILE §9) always carry timeout + retry with backoff + circuit breaker so one slow SaaS cannot stall a workflow.

### Workflows & pipelines
Anything over ~2 s of work goes async (queue/job), with the UI acknowledging immediately. Consumers are idempotent; publication uses the outbox pattern (aligned with the project's architecture stance, §5) so retries never double-post side effects. Monitor queue depth and consumer lag; define backpressure behavior before it's needed. Batch jobs declare their window and their SLA.

### Website responsiveness
Code-split by route; lazy-load heavy modules (report builders, charts). Virtualize long tables — data grids and list views will hit thousands of rows. Skeletons/optimistic UI for perceived speed; debounce searches; cache static assets aggressively (CDN + cache headers).

### Load / unload
This covers all four meanings — treat each explicitly:
1. **Initial load** — meet LCP/bundle budgets above; measure on mid-range mobile unless PROJECT_PROFILE §12 says otherwise.
2. **Data loading** — progressive loading with visible states; never block the whole dashboard on one slow widget.
3. **Unload / teardown** — clean up listeners, timers, subscriptions on route change; an SPA kept open all day must not leak memory. Verify with a heap snapshot before/after 50 navigations.
4. **Load testing** — before prod release, run a scripted load test (k6/Artillery) at **2× expected peak** of the peak events declared in PROJECT_PROFILE §12. Budgets must hold at that level.

## Measurement protocol
Profile first — never optimize on a hunch. Every performance PR includes before/after numbers from the same environment. Instrument the seams: structured logs with duration, traces across context boundaries and SaaS calls, RED metrics (rate, errors, duration) per endpoint and per queue. Staging perf checks run against production-like data volume, not a 10-row seed database.

## Scale Ladder — the sense to restructure

Do not restructure by fashion; climb only when a trigger fires, and only by proposal. This ladder implements the modular-monolith-first default; §5 records the project's actual style.

**S1 — Modular monolith (default start).** One deployable, module boundaries mirror bounded contexts, no cross-module table access.
→ *Climb when:* any budget breached at p95 sustained 7 days despite query/index fixes, or DB CPU > 70 % sustained, or a hot table passes ~5 M rows with degrading queries.

**S2 — Hardened monolith.** Add caching (with explicit invalidation), read models for heavy dashboards, read replicas, and move remaining synchronous heavy work to async jobs.
→ *Climb when:* one module dominates load and needs independent scaling (typically high-volume event ingestion), or deploys queue behind each other, or a second team needs an independent release cadence.

**S3 — Selective service extraction.** Extract only the forced context(s) behind published events; everything else stays in the monolith. Each extraction gets its own ADR.
→ *Climb when:* cross-context event volume, replay/audit requirements, or divergent read/write shapes justify it — not before.

**S4 — Event-driven / CQRS where justified.** Applied per context, never system-wide by default.

### Restructure protocol (PROPOSE ONLY)
1. A trigger fires → gather 7 days of evidence (metrics, traces, load-test output).
2. Append a `RESTRUCTURE` entry to `ORCHESTRATION_LOG.md`: current stage, target stage, trigger evidence, blast radius, migration sketch — status `PENDING-APPROVAL`. Draft the ADR (template per the project's architecture references, §5).
3. **Stop.** Only a human `DECISION` entry converts it to APPROVED.
4. On approval, migrate incrementally (strangler pattern) — never big-bang, and never inside a §12 business-critical window.

## Release gate (prod)
Before any production release: all budgets verified on staging with production-like volume; load test at 2× peak passed; no unresolved budget breaches; queue lag and error dashboards green. Log the result as part of the release `COMPLETE` entry.

## Logging duties
`RESTRUCTURE` proposals, budget breaches (`BLOCKED` or `ESCALATE` with numbers), and load-test results at release all go to the orchestration log with evidence attached — numbers, not adjectives.
