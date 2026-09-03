# Rubric: io-contract (v1.0)
Mode default: single-artifact over a request/response sample set (happy path + errors + one replay + one cross-tenant probe) · Tier: FAST for schema shape; STRONG when the endpoint touches PROJECT_PROFILE §6 high-risk paths or §7 sensitive data · Evidence on FAIL: sample id + field, mandatory.

| ID | Criterion — PASS means |
|---|---|
| IO-1 | Requests and responses match the published schema: fields, types, required/optional, enums |
| IO-2 | Error responses use the standard error shape; no stack traces, SQL, or internal paths leaked |
| IO-3 | No §7 sensitive data (government IDs, financial details, or other RESTRICTED fields) in payloads, URLs, headers, or logs — references only |
| IO-4 | List endpoints paginate with enforced limits; no unbounded responses |
| IO-5 | §6 high-risk endpoints honor idempotency keys — the replay sample produces no double effect |
| IO-6 | Responses are scoped to the caller's role and tenant/entity — the cross-tenant probe sample returns deny, not data |
| IO-7 | Breaking contract changes are flagged and versioned, never silent |
| IO-8 | **Integrity:** samples are genuine tool output, not hand-written "expected" responses passed off as actual |
