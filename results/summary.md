Runs: v1-full, v1-min, v2-full, v2-min. Repeats seen: baseline 1, free_skills 1, guardrails 1.

**Planted problems caught**

| | v1-full | v1-min | v2-full | v2-min | **Total** |
|---|---|---|---|---|---|
| Plain Claude | 29/29 | 29/29 | 21/22 | 20/22 | **99/102** |
| Free Skills | 29/29 | 28/29 | 20/22 | 21/22 | **98/102** |
| Guardrails pack | 29/29 | 29/29 | 22/22 | 22/22 | **102/102** |

**Publish calls and false alarms** (all runs pooled; every draft and repeat counted)

| | Publish call right | Clean drafts blocked | Clean drafts with any flag | Duplicate flags on a planted problem | Extra flags: valid / false alarm / borderline / unruled | Cost per 50 drafts | Seconds per draft |
|---|---|---|---|---|---|---|---|
| Plain Claude | 183/192 (95%) | 6/96 (6%) | 6/96 (6%) | 7 | 13 / 1 / 1 / 0 | $0.46 | 10 |
| Free Skills | 173/192 (90%) | 15/96 (16%) | 15/96 (16%) | 12 | 16 / 16 / 10 / 0 | $0.64 | 12 |
| Guardrails pack | 181/192 (94%) | 11/96 (11%) | 11/96 (11%) | 6 | 16 / 8 / 5 / 0 | $0.68 | 13 |

**Paired comparisons** (exact McNemar, two-sided; A only = items A got right and B didn't)

| A vs B | Problems: pairs, A only, B only, p | Publish calls: pairs, A only, B only, p |
|---|---|---|
| Plain Claude vs Free Skills | 102, 3, 2, p = 1.00 | 192, 12, 2, p = 0.01 |
| Plain Claude vs Guardrails pack | 102, 0, 3, p = 0.25 | 192, 6, 4, p = 0.75 |
| Free Skills vs Guardrails pack | 102, 0, 4, p = 0.12 | 192, 3, 11, p = 0.06 |

**Scoring rule change** (new whole-word rules versus the original string rules)

- Plain Claude: 99 caught under the old rules, 99 under the new (0 changed)
- Free Skills: 98 caught under the old rules, 98 under the new (0 changed)
- Guardrails pack: 102 caught under the old rules, 102 under the new (0 changed)

