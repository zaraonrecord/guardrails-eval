Runs: v1-full, v1-min, v2-full, v2-min. Repeats seen: baseline 3, baseline_long 3, free_skills 3, guardrails 3.
Counts are majority across repeats (caught in more than half); mean catch rate in brackets.

**Planted problems caught**

| | v1-full | v1-min | v2-full | v2-min | **Total** |
|---|---|---|---|---|---|
| Plain Claude | 29/29 (29.0) | 28/29 (28.0) | 21/22 (20.7) | 20/22 (20.0) | **98/102** (97.7) |
| Plain Claude + generic checklist | 29/29 (29.0) | 28/29 (28.0) | 22/22 (21.7) | 22/22 (22.0) | **101/102** (100.7) |
| Free Skills | 29/29 (29.0) | 29/29 (28.7) | 20/22 (20.7) | 22/22 (21.7) | **100/102** (100.0) |
| Guardrails pack | 29/29 (29.0) | 29/29 (29.0) | 22/22 (22.0) | 22/22 (21.7) | **102/102** (101.7) |

**Publish calls and false alarms** (all runs pooled; every draft and repeat counted)

| | Publish call right | Clean drafts blocked | Clean drafts with any flag | Duplicate flags on a planted problem | Extra flags: valid / false alarm / borderline / unruled | Cost per 50 drafts | Seconds per draft |
|---|---|---|---|---|---|---|---|
| Plain Claude | 539/576 (94%) | 24/288 (8%) | 23/288 (8%) | 17 | 43 / 8 / 0 / 0 | $0.41 | 10 |
| Plain Claude + generic checklist | 542/576 (94%) | 30/288 (10%) | 30/288 (10%) | 13 | 51 / 12 / 0 / 0 | $0.43 | 10 |
| Free Skills | 530/576 (92%) | 40/288 (14%) | 40/288 (14%) | 42 | 39 / 44 / 28 / 0 | $0.60 | 13 |
| Guardrails pack | 550/576 (95%) | 25/288 (9%) | 24/288 (8%) | 22 | 38 / 17 / 10 / 0 | $0.63 | 13 |

**Paired comparisons** (exact McNemar, two-sided; A only = items A got right and B didn't)

| A vs B | Problems: pairs, A only, B only, p | Publish calls: pairs, A only, B only, p |
|---|---|---|
| Plain Claude vs Plain Claude + generic checklist | 102, 1, 4, p = 0.38 | 192, 4, 4, p = 1.00 |
| Plain Claude vs Free Skills | 102, 1, 3, p = 0.62 | 192, 8, 3, p = 0.23 |
| Plain Claude vs Guardrails pack | 102, 0, 4, p = 0.12 | 192, 2, 6, p = 0.29 |
| Plain Claude + generic checklist vs Free Skills | 102, 2, 1, p = 1.00 | 192, 8, 3, p = 0.23 |
| Plain Claude + generic checklist vs Guardrails pack | 102, 0, 1, p = 1.00 | 192, 2, 6, p = 0.29 |
| Free Skills vs Guardrails pack | 102, 0, 2, p = 0.50 | 192, 0, 9, p = 0.004 |

**Scoring rule change** (new whole-word rules versus the original string rules)

- Plain Claude: 293 caught under the old rules, 293 under the new (0 changed)
- Plain Claude + generic checklist: 302 caught under the old rules, 302 under the new (0 changed)
- Free Skills: 300 caught under the old rules, 300 under the new (0 changed)
- Guardrails pack: 305 caught under the old rules, 305 under the new (0 changed)

