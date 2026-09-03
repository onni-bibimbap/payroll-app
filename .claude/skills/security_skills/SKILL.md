---
name: security_skills
description: Core security skill — the solution must be uncompromisable in any production release. Use whenever implementing auth, roles, endpoints, file uploads, integrations, or anything touching PROJECT_PROFILE §7 sensitive data; when adding dependencies; when reviewing code; and before EVERY release. Defines two tiers — trial/prototype builds get a relaxed baseline, production releases must pass the full hard gate with zero exceptions unless a human signs off a logged DECISION.
---

# Security Skill — Trial Baseline, Production Hard Gate

This system holds the sensitive data classes listed in `.claude/PROJECT_PROFILE.md` §7, under the compliance regime in §8 and at the criticality tier in §13. The rule is simple: **a trial can be light on hardening, but a production release can never be compromisable.** Relaxation applies to hardening depth only — it never applies to real personal data.

## The two tiers

### TRIAL tier (prototype / demo / internal trial)
Allowed relaxations: simplified auth (single shared test login), MFA off, no pen test, permissive CORS on local, self-signed certs locally, coarse rate limiting, seeded demo content.

**Never relaxed — even in trial:**
1. **Synthetic data only.** Real §7 sensitive data (any RESTRICTED or INTERNAL class listed there) never enters a trial build or trial database. Generate fake data.
2. No secrets committed to the repo — ever. `.env` + gitignore from commit one.
3. No known critical/high CVEs in dependencies.
4. Anything internet-exposed still requires authentication — no open admin panels "just for the demo".
5. No real execution of §6 high-risk actions (irreversible or externally-visible side effects) from a trial build.

### PRODUCTION tier — the hard gate
Every item below passes before release, or the release is blocked with a `SECURITY-FLAG`. An exception requires a human-signed `DECISION` entry in the orchestration log naming the risk accepted.

## Production hard gate checklist

**Identity & access**
- [ ] Server-side RBAC on every endpoint, deny-by-default; roles at minimum: the role set defined in PROJECT_PROFILE §5/§6, plus `system`.
- [ ] Tenancy isolation: every query scoped by the tenancy boundary defined in PROJECT_PROFILE §5; verified by tests that role X of tenant A cannot read tenant B (IDOR checks on all ID-taking endpoints).
- [ ] Sessions/tokens: short-lived access + refresh rotation, httpOnly + Secure cookies or equivalent; logout invalidates server-side.
- [ ] MFA available and enforced for admin/owner roles.

**Input & injection**
- [ ] All input validated at the boundary (schema validation); parameterized queries only — string-built SQL is an automatic block.
- [ ] Output encoding against XSS; CSRF protection on state-changing browser requests.
- [ ] File uploads: type + size allowlist, stored outside web root, never executed, virus-scanned if user-facing.

**Data & privacy (per the §8 compliance regime)**
- [ ] PII classified and handled by class: `RESTRICTED` = the §7 RESTRICTED classes → field-level encryption at rest, masked in UI by default, click-to-reveal is role-gated **and access-logged**. `INTERNAL` = the §7 INTERNAL classes → encrypted at rest, role-gated.
- [ ] RESTRICTED data travels as references, never as payloads, in events, logs, URLs, or error messages (per the project's architecture stance in PROJECT_PROFILE §5).
- [ ] TLS everywhere in transit; encrypted backups with a tested restore.
- [ ] Data minimization + a written retention schedule (records retained per the §8 compliance regime; everything else has an expiry).

**Secrets & supply chain**
- [ ] Secrets in a vault/managed store, injected at runtime, rotated on staff change; none in code, logs, or client bundles.
- [ ] Runtime per `infra_skills`: non-root images pinned by digest in prod, DB port unpublished, backups encrypted at rest, `docker compose down -v` only by human DECISION.
- [ ] Lockfiles committed; dependency scan clean of critical/high; pinned versions for anything touching §6 high-risk actions.

**Integrations & APIs**
- [ ] Webhook signatures verified for every inbound integration in §9 (mark n/a with the reason if none exist); unsigned = rejected.
- [ ] Rate limiting on auth and public endpoints; idempotency keys on every §6 high-risk endpoint so retries can't double-execute.
- [ ] Outbound SaaS credentials least-privilege and per-environment.

**Audit & monitoring**
- [ ] Append-only audit trail for §6 high-risk actions, role changes, RESTRICTED-field reveals, exports, and admin actions: who, what, when, from where.
- [ ] Auth failures, permission denials, and anomalous export volumes alert somebody.

**Infra & release hygiene**
- [ ] Security headers set (CSP, HSTS, X-Content-Type-Options, frame-ancestors); CORS locked to known origins.
- [ ] Prod/staging/trial fully separated — separate databases, separate credentials, no shared secrets.
- [ ] Debug endpoints, verbose errors, and default credentials removed.

## Release protocol
1. Run the gate → produce a Security Release Report: each item PASS/FAIL with evidence.
2. Any FAIL → `SECURITY-FLAG` entry in the orchestration log; release blocked until fixed or a human logs a `DECISION` accepting the named risk.
3. Attach the report to the release's `COMPLETE` entry. Tier (TRIAL/PROD) is stated on every release entry so nobody ships a trial build to production by accident.

## Code-review red flags — block on sight
String-concatenated SQL; PII in log lines or URLs; authorization checked only client-side; hardcoded credentials or API keys; `verify=false` / disabled TLS checks; webhook handlers without signature verification; catch-and-ignore around §6 high-risk or export code.

## Incident rule
Suspected compromise or leaked secret → freeze the affected surface, rotate credentials, log `ESCALATE` immediately with what is known. Never quietly patch a breach — the audit trail and the human must know.
