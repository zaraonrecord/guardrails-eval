# Do marketing guardrail Skills actually catch anything Claude wouldn't?

An eval of three ways to check marketing copy with Claude before it's published: plain Claude, a set of free guardrail Skills, and the Guardrails for Marketing Teams pack. Built and run in November 2026 on Claude Sonnet 5.5.

**Short answer:** plain Claude already catches almost all of the obvious and most of the subtle problems on its own (99 of 102). The Guardrails pack was the only setup to catch every planted problem (102 of 102), and it costs about 50% more per draft. The free Skills caught slightly fewer than plain Claude and raised the most false alarms. Most of the value isn't in catching blatant mistakes any more; it's in the last few subtle ones, and in doing it the same way every time.

## What was tested

**The drafts.** A fictional UK tea brand, Pebblebrook Tea Co., with a written brand policy (claims it can prove, words it never uses, how it labels ads). 24 clean drafts across landing pages, emails, search ads, product pages, creator posts and an affiliate review, using only claims the policy allows. Then variants with problems planted at exact, known positions:
- **Round 1, obvious (29 problems):** "The UK's best loose leaf tea", "Loved by 50,000 tea drinkers", "boosts your immunity", "carbon neutral", "only 40 tins are left", "In today's fast-paced world", a creator post with its "Ad" label removed.
- **Round 2, subtle (22 problems):** the review count quietly changed from 1,200 to 2,000; "noticeably smoother than supermarket tea bags"; "help you wind down and sleep better"; "packed with antioxidants"; "planet-friendly packaging"; "while stocks last"; "#ad" buried in the middle of seven hashtags; an affiliate link disclosed only in a footnote; "Brewed with care. Packed with love. Delivered with a smile."; "Was £12, now £8" with no price history.

**The setups**, each given the same task and the same policy:
1. **Plain Claude:** "You are a careful marketing editor. Check marketing copy before it is published."
2. **Free Skills:** Claims Guard, Slop Guard and Honest Review Rules from the free, CC BY marketing Skills.
3. **Guardrails pack:** the publish gate plus its claims, regulated claims, disclosure and house style checks.

**Two policy levels.** Every round ran twice: once with the full brand policy (which spells out banned phrases), and once with a bare one (who the brand is and the claims it can prove, nothing more). Most real teams have something closer to the bare one.

**How it ran.** Each draft went to Claude headless with no tools, no settings and no memory (`claude -p`), and the reply had to end with a JSON list of problems, quoting the draft's exact words, plus a publish or don't-publish decision. 576 runs in all.

**How it was scored.** A planted problem counts as caught when a flagged quote overlaps it. All 265 quote matches were exact containment, not partial overlap, which I checked separately. A missing label counts as caught when any flag is a missing disclosure. Every flag that didn't match a planted problem was ruled by hand as **valid** (a real problem my test set had missed), a **false alarm**, or **borderline**, with a reason for each, in `data/adjudication.json`.

## Results

**Planted problems caught**

| | Round 1, full policy | Round 1, bare | Round 2 (subtle), full | Round 2 (subtle), bare | **Total** |
|---|---|---|---|---|---|
| Plain Claude | 29/29 | 29/29 | 21/22 | 20/22 | **99/102** |
| Free Skills | 29/29 | 28/29 | 20/22 | 21/22 | **98/102** |
| Guardrails pack | 29/29 | 29/29 | 22/22 | 22/22 | **102/102** |

**Everything else they flagged, ruled by hand** (all four runs added together)

| | Real problems my test set missed | False alarms | Borderline |
|---|---|---|---|
| Plain Claude | 13 | 1 | 1 |
| Free Skills | 16 | 16 | 10 |
| Guardrails pack | 16 | 8 | 5 |

**Cost and speed** (Claude Sonnet 5.5, per 50 drafts): plain Claude about $0.45 and 10 seconds a draft; free Skills about $0.64 and 12 seconds; Guardrails about $0.68 and 13 seconds.

## What it means

- **The obvious stuff is solved.** With or without a policy, every setup caught every blatant problem in round 1. If your worry is "Claude will let 'clinically proven' through", it mostly won't.
- **The subtle misses are style and placement.** Plain Claude's three misses: the tidy "Brewed with care. Packed with love. Delivered with a smile." triplet (twice) and an affiliate link disclosed only in a footnote. The free Skills missed the triplet too, plus a fake "was £12, now £8" price.
- **Guardrails closed those gaps, at a cost.** It caught all 102 and found as many hidden real problems as anyone, but raised 8 false alarms to plain Claude's 1, and costs about 50% more per draft.
- **The free Skills over-flag.** They raised twice Guardrails' false alarms, mostly by questioning claims the policy allows and by asking for disclosure where it was already given. That's the first thing to fix in them.
- **The written policy mattered less than I expected.** Results with the full and bare policy were within a point or two of each other. Claude's own judgement about UK advertising norms carried most of it.

## What I'd change next

1. **Repeat each run three times.** Every draft ran once per setup, so differences of one or two problems could be noise.
2. **Make round 3 harder still,** with problems that need context, such as a claim that's true for one product but not another, or a disclosure that's present but not prominent enough on mobile.
3. **Cut the free Skills' false alarms** by teaching them to check the policy's approved claims before flagging, then rerun.
4. **Test another model.** Everything here is Claude Sonnet 5.5; a smaller model might show bigger gaps between the setups.

## Limits, honestly

- I wrote the drafts, the planted problems and the rulings, and I also wrote the Skills being tested. The rulings and their reasons are all in the repo so you can disagree with them.
- One fictional brand, UK English, one model, one run per draft.
- Asking for a JSON list of problems changes how the model answers a little. All three setups had the same instruction.

## Run it yourself

```
python3 data/build_cases.py && python3 data/build_cases_v2.py
POLICY=minimal python3 run.py v1-min                          # round 1, bare policy
CASES=cases-v2.json POLICY=full python3 run.py v2-full        # round 2, full policy
python3 score.py v2-full --flags                              # results and every unmatched flag
```
Needs the Claude CLI signed in. The Guardrails pack's Skill text isn't included here (it's a paid product); set `PAID_SKILLS` to its folder, or run the other two setups only. The free Skills are at github.com/zaraonrecord/claude-marketing-skills.
