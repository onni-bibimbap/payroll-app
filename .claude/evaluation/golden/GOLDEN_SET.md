# GOLDEN SET — calibration & regression references

Pre-judged items used to (a) calibrate the llm-judge against human rulings and (b) catch regressions on domain-critical outputs. Rules live in `../EVALUATION_PROTOCOL.md`; this file holds the registry and logs. **All golden data is synthetic — never a real person's records.**

## Item structure
Each item is a folder `G-###/` containing:
- `brief.md` — the requirement/ACs and context exactly as a judge briefing would carry them
- `artifact/` — the input under judgment (code, samples, or output)
- `ruling.md` — the recorded human ruling (overall + per-criterion where it matters) and rationale

## Seeding plan
1. Convert past human `DECISION` entries (waivers, escalation rulings) from the orchestration log into golden items — they are ground truth by definition.
2. Build DM goldens from the project PRD's worked scenarios with synthetic data.
3. Add every FAST-vs-STRONG or judge-vs-human disagreement discovered in spot-checks as a new golden item.
Target: 10–20 items covering every rubric before trusting FAST-tier SHIPs on routine work.

## Registry
| G-ID | Rubric | Target type | Human ruling | Source | Added |
|---|---|---|---|---|---|
| — | — | — | — | — | — |

## Calibration log (append per run — target agreement ≥ 90%)
| Date | Tier | Judge model | Rubric versions | Items | Agreement % | Action |
|---|---|---|---|---|---|---|
| — | — | — | — | — | — | — |
