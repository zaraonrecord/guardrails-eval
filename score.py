"""Score runs: did each setup catch the planted problems, how often did it cry wolf, and were its
publish calls right?

    python3 score.py v1-full             # one run: summary per setup
    python3 score.py v1-full --json      # also writes runs/v1-full/score.json
    python3 score.py v1-full --flags     # also lists every unmatched flag, for checking by hand
    python3 score.py summary             # all four runs in one table, paired tests, writes results/
    python3 score.py summary v1-full v2-full   # just these runs

Matching rules (deterministic, all in this file and covered by tests/):

1. A planted problem with a span is caught when a flagged quote matches it. Quote and span are
   split into lowercase word tokens (norm). The quote matches when
   a) its tokens contain the span's tokens as a whole-word run (the quote covers the span), or
   b) the quote is long enough (at least 2 content words, or at least 40% of the span's tokens with
      at least one content word) AND either its tokens appear as a whole-word run inside the span,
      or at least 60% of the span's distinct tokens appear in the quote.
   So "tea" or "ad" can no longer catch a long span, and "ad" no longer matches inside "made".
2. A missing label (span None) is caught only when a flag has type missing_disclosure AND points at
   the label: its quote is the draft's opening words (the first 3 tokens, or the whole quote if
   shorter, match the start of the draft), or it mentions ad, gifted, affiliate, sponsored, paid,
   commission or disclosure. Any other missing_disclosure flag does not count.
3. One flag may catch two planted problems on the same words (a fake testimonial that is also a
   health claim). Other flags that also match a problem already caught are counted separately as
   "duplicate flags on a planted problem", not as extra flags and not silently dropped.
4. Every other flag is an "extra flag", ruled by hand in data/adjudication.json as valid (a real
   problem the test set missed), false_alarm, borderline, or duplicate (it points at a planted problem
   another flag caught but is too short to match). Hand-ruled duplicates are added to the duplicate
   count in the summary.

Repeats: runs/<version>/<setup>/<case>.json is repeat 1, <case>.r2.json repeat 2, and so on.
Per planted problem we keep the catch rate across repeats. Headline counts use the majority
(caught in more than half the repeats that ran; a tie counts as missed). The mean catch rate is
reported alongside. Publish calls work the same way per draft. With one repeat both are the same as
the raw count. Paired tests (exact McNemar) use the majority outcome per problem or per draft.
"""
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = os.path.join(HERE, "runs")
DEFAULT_VERSIONS = ["v1-full", "v1-min", "v2-full", "v2-min"]
ORDER = ["baseline", "baseline_long", "free_skills", "guardrails"]
LABELS = {"baseline": "Plain Claude", "baseline_long": "Plain Claude + generic checklist",
          "free_skills": "Free Skills", "guardrails": "Guardrails pack"}

MIN_CONTENT_WORDS = 2
MIN_SHARE = 0.4
SHARED_WORDS = 0.6
OPENING_TOKENS = 3

STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "so", "of", "to", "in", "on", "at", "for", "with", "by", "from",
    "as", "is", "are", "was", "were", "be", "been", "it", "it's", "its", "this", "that", "these", "those",
    "i", "i'm", "i've", "me", "my", "we", "we're", "we've", "our", "you", "you're", "you'll", "your",
    "they", "their", "he", "she", "his", "her", "just", "very", "s",
}
DISCLOSURE_WORDS = {"ad", "ads", "paid", "gifted", "gift", "pr", "label", "labelled", "labeled"}
DISCLOSURE_PREFIXES = ("advert", "affiliat", "disclos", "sponsor", "commission", "partnership")


def norm(s):
    s = (s or "").lower().replace("’", "'").replace("“", '"').replace("”", '"')
    return re.sub(r"[^a-z0-9%£' ]+", " ", s).split()


def content_words(tokens):
    return [t for t in tokens if t not in STOPWORDS]


def contains_run(tokens, sub):
    """True when sub appears in tokens as a contiguous whole-word run."""
    n, m = len(tokens), len(sub)
    if m == 0 or m > n:
        return False
    return any(tokens[i:i + m] == sub for i in range(n - m + 1))


def overlaps(quote, span):
    q, p = norm(quote), norm(span)
    if not q or not p:
        return False
    if contains_run(q, p):
        return True
    n_content = len(content_words(q))
    long_enough = n_content >= MIN_CONTENT_WORDS or (n_content >= 1 and len(q) / len(p) >= MIN_SHARE)
    if not long_enough:
        return False
    if contains_run(p, q):
        return True
    return len(set(q) & set(p)) / len(set(p)) >= SHARED_WORDS


def overlaps_v1(quote, span):
    """The original rule, kept only to report how many catches the new rule changes."""
    q, p = norm(quote), norm(span)
    if not q or not p:
        return False
    qs, ps = " ".join(q), " ".join(p)
    if qs in ps or ps in qs:
        return True
    return len(set(q) & set(p)) / len(set(p)) >= 0.6


def points_at_missing_label(issue, draft):
    if issue.get("type") != "missing_disclosure":
        return False
    q = norm(issue.get("quote", ""))
    if not q:
        return False
    if any(t in DISCLOSURE_WORDS or t.startswith(DISCLOSURE_PREFIXES) for t in q):
        return True
    d = norm(draft)
    k = min(len(q), OPENING_TOKENS)
    return q[:k] == d[:k]


def matches(issue, planted, draft, old=False):
    if planted["span"] is None:
        if old:
            return issue.get("type") == "missing_disclosure"
        return points_at_missing_label(issue, draft)
    return (overlaps_v1 if old else overlaps)(issue.get("quote", ""), planted["span"])


def parse(result):
    """The last fenced JSON block that parses wins. Returns (issues, publish) or (None, None)."""
    blocks = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", result or "", re.S)
    for b in reversed(blocks):
        try:
            d = json.loads(b)
        except json.JSONDecodeError:
            continue
        if not isinstance(d, dict):
            continue
        issues = d.get("issues") or []
        if not isinstance(issues, list):
            issues = []
        issues = [i for i in issues if isinstance(i, dict)]
        publish = d.get("publish")
        return issues, publish if isinstance(publish, bool) else None
    return None, None


def repeat_of(filename):
    """b01.json -> ('b01', 1); b01.r2.json -> ('b01', 2). Anything else -> None."""
    m = re.fullmatch(r"(.+?)(?:\.r(\d+))?\.json", filename)
    if not m:
        return None
    return m.group(1), int(m.group(2) or 1)


def manifest(version):
    path = os.path.join(RUNS, version, "manifest.json")
    return json.load(open(path)) if os.path.exists(path) else None


def cases_file(version):
    m = manifest(version)
    if m and m.get("cases_file"):
        return m["cases_file"]
    # runs made before manifests existed: the old naming rule
    return "cases-v2.json" if version.startswith("v2") else "cases.json"


def load_cases(version):
    return {c["id"]: c for c in json.load(open(os.path.join(HERE, "data", cases_file(version))))}


def score_records(version, cond, cases, records):
    """records: list of (repeat, record dict). Returns the per-setup tallies for one run."""
    s = {"planted": 0, "caught": 0, "caught_old": 0, "clean_runs": 0, "clean_flagged": 0, "clean_blocked": 0,
         "clean_decided": 0, "extra_flags": 0, "extra_on_clean": 0, "dup_flags": 0, "publish_right": 0,
         "publish_total": 0, "unparsed": 0, "cost_usd": 0.0, "seconds": 0.0, "runs": 0,
         "by_type": defaultdict(lambda: [0, 0]), "missed": [], "extras": [], "dups": [], "rule_changes": [],
         "problems": {}, "decisions": {}, "repeats": set()}
    for rep, rec in records:
        case = cases[rec["case"]]
        s["runs"] += 1
        s["repeats"].add(rep)
        s["cost_usd"] += rec.get("cost_usd") or 0
        s["seconds"] += rec.get("seconds") or 0
        issues, publish = parse(rec.get("result", ""))
        if issues is None:
            s["unparsed"] += 1
            issues, publish = [], None
        tag = case["id"] if rep == 1 else f"{case['id']}.r{rep}"
        used = set()
        for idx, p in enumerate(case["planted"]):
            s["planted"] += 1
            s["by_type"][p["type"]][1] += 1
            hit = next((i for i, iss in enumerate(issues) if matches(iss, p, case["text"])), None)
            hit_old = any(matches(iss, p, case["text"], old=True) for iss in issues)
            s["caught_old"] += int(hit_old)
            if (hit is not None) != hit_old:
                s["rule_changes"].append(f"{version} {cond} {tag} {p['type']}: "
                                         + ("now caught" if hit is not None else "no longer caught"))
            key = f"{version}/{case['id']}/{idx}"
            pr = s["problems"].setdefault(key, {"type": p["type"], "span": p["span"], "hits": []})
            pr["hits"].append(hit is not None)
            if hit is not None:
                s["caught"] += 1
                s["by_type"][p["type"]][0] += 1
                used.add(hit)
            else:
                s["missed"].append(f"{tag} {p['type']}: {p['span']}")
        for i, iss in enumerate(issues):
            if i in used:
                continue
            line = f"{tag} [{iss.get('type')}] {str(iss.get('quote', ''))[:120]}"
            if any(matches(iss, p, case["text"]) for p in case["planted"]):
                s["dup_flags"] += 1
                s["dups"].append(line)
            else:
                s["extra_flags"] += 1
                s["extras"].append(line)
                if not case["planted"]:
                    s["extra_on_clean"] += 1
        clean = not case["planted"]
        dec = s["decisions"].setdefault(f"{version}/{case['id']}", {"clean": clean, "right": []})
        dec["right"].append(None if publish is None else (publish == clean))
        if clean:
            s["clean_runs"] += 1
            s["clean_flagged"] += int(bool(issues))
            if publish is not None:
                s["clean_decided"] += 1
                s["clean_blocked"] += int(publish is False)
        if publish is not None:
            s["publish_total"] += 1
            s["publish_right"] += int(publish == clean)
    s["by_type"] = {k: v for k, v in sorted(s["by_type"].items())}
    s["repeats"] = sorted(s["repeats"])
    return s


def load_records(version, cond):
    d = os.path.join(RUNS, version, cond)
    out = []
    for f in sorted(os.listdir(d)):
        r = repeat_of(f)
        if r is None:
            continue
        out.append((r[1], json.load(open(os.path.join(d, f)))))
    return out


def conditions_in(version):
    root = os.path.join(RUNS, version)
    names = [c for c in os.listdir(root) if os.path.isdir(os.path.join(root, c)) and not c.startswith(("_", "."))]
    return sorted(names, key=lambda c: (ORDER.index(c) if c in ORDER else len(ORDER), c))


def score(version):
    cases = load_cases(version)
    return {cond: score_records(version, cond, cases, load_records(version, cond)) for cond in conditions_in(version)}


def adjudicate(res):
    """Apply hand rulings to extra flags: valid, false_alarm, borderline, or unruled."""
    path = os.path.join(HERE, "data", "adjudication.json")
    rulings = json.load(open(path))["rulings"] if os.path.exists(path) else []
    for s in res.values():
        tally = Counter()
        unruled = []
        for e in s["extras"]:
            cid = e.split(" ", 1)[0].split(".r", 1)[0]
            r = next((r for r in rulings if r["case"] in (cid, "*") and r["match"].lower() in e.lower()), None)
            if r:
                tally[r["verdict"]] += 1
            else:
                tally["unruled"] += 1
                unruled.append(e)
        s["adjudicated"] = dict(tally)
        s["unruled"] = unruled
    return res


# ---- aggregation across repeats and runs -------------------------------------------------------

def majority(values):
    """True when more than half of the non-None values are True. Ties and no data count as False."""
    vals = [v for v in values if v is not None]
    return bool(vals) and sum(vals) * 2 > len(vals)


def mean(values):
    vals = [v for v in values if v is not None]
    return sum(vals) / len(vals) if vals else 0.0


def mcnemar_exact(b, c):
    """Two-sided exact McNemar p-value from the discordant counts b and c."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def paired(a_items, b_items):
    """a_items, b_items: {key: bool}. Returns (n_pairs, b = a only, c = b only, p)."""
    keys = sorted(set(a_items) & set(b_items))
    b = sum(1 for k in keys if a_items[k] and not b_items[k])
    c = sum(1 for k in keys if b_items[k] and not a_items[k])
    return len(keys), b, c, mcnemar_exact(b, c)


def pct(a, b):
    return f"{(100 * a / b):.0f}%" if b else "n/a"


def fmt_p(p):
    return "1.00" if p >= 0.995 else f"{p:.2f}" if p >= 0.01 else f"{p:.3f}"


def combine(versions):
    """Score and adjudicate each run, then pool everything per setup."""
    per_run = {v: adjudicate(score(v)) for v in versions}
    conds = []
    for v in versions:
        for c in per_run[v]:
            if c not in conds:
                conds.append(c)
    conds.sort(key=lambda c: (ORDER.index(c) if c in ORDER else len(ORDER), c))
    pooled = {}
    for c in conds:
        t = Counter()
        problems, decisions, adj, changes = {}, {}, Counter(), []
        repeats = set()
        for v in versions:
            s = per_run[v].get(c)
            if not s:
                continue
            for k in ("runs", "planted", "caught", "caught_old", "clean_runs", "clean_flagged", "clean_blocked",
                      "clean_decided", "extra_flags", "dup_flags", "publish_right", "publish_total", "unparsed"):
                t[k] += s[k]
            t["cost_usd"] += s["cost_usd"]
            t["seconds"] += s["seconds"]
            problems.update(s["problems"])
            decisions.update(s["decisions"])
            adj.update(s["adjudicated"])
            changes += s["rule_changes"]
            repeats.update(s["repeats"])
        pooled[c] = {"t": t, "problems": problems, "decisions": decisions, "adjudicated": adj,
                     "rule_changes": changes, "repeats": sorted(repeats)}
    return per_run, conds, pooled


def summary(versions, write=True):
    per_run, conds, pooled = combine(versions)
    L = []
    multi = any(len(p["repeats"]) > 1 for p in pooled.values())
    L.append(f"Runs: {', '.join(versions)}. Repeats seen: "
             + ", ".join(f"{c} {max(p['repeats']) if p['repeats'] else 0}" for c, p in pooled.items()) + ".")
    if multi:
        L.append("Counts are majority across repeats (caught in more than half); mean catch rate in brackets.")
    L.append("")

    L.append("**Planted problems caught**")
    L.append("")
    L.append("| | " + " | ".join(versions) + " | **Total** |")
    L.append("|---|" + "---|" * (len(versions) + 1))
    for c in conds:
        cells, tot_maj, tot_n, tot_mean = [], 0, 0, 0.0
        for v in versions:
            s = per_run[v].get(c)
            if not s:
                cells.append("not run")
                continue
            maj = sum(majority(p["hits"]) for p in s["problems"].values())
            n = len(s["problems"])
            mn = sum(mean(p["hits"]) for p in s["problems"].values())
            cells.append(f"{maj}/{n}" + (f" ({mn:.1f})" if multi else ""))
            tot_maj, tot_n, tot_mean = tot_maj + maj, tot_n + n, tot_mean + mn
        L.append(f"| {LABELS.get(c, c)} | " + " | ".join(cells)
                 + f" | **{tot_maj}/{tot_n}**" + (f" ({tot_mean:.1f})" if multi else "") + " |")
    L.append("")

    L.append("**Publish calls and false alarms** (all runs pooled; every draft and repeat counted)")
    L.append("")
    L.append("| | Publish call right | Clean drafts blocked | Clean drafts with any flag "
             "| Duplicate flags on a planted problem | Extra flags: valid / false alarm / borderline / unruled "
             "| Cost per 50 drafts | Seconds per draft |")
    L.append("|---|---|---|---|---|---|---|---|")
    for c in conds:
        t, a = pooled[c]["t"], pooled[c]["adjudicated"]
        L.append(f"| {LABELS.get(c, c)} | {t['publish_right']}/{t['publish_total']} ({pct(t['publish_right'], t['publish_total'])})"
                 f" | {t['clean_blocked']}/{t['clean_decided']} ({pct(t['clean_blocked'], t['clean_decided'])})"
                 f" | {t['clean_flagged']}/{t['clean_runs']} ({pct(t['clean_flagged'], t['clean_runs'])})"
                 f" | {t['dup_flags'] + a.get('duplicate', 0)}"
                 f" | {a.get('valid', 0)} / {a.get('false_alarm', 0)} / {a.get('borderline', 0)} / {a.get('unruled', 0)}"
                 f" | ${50 * t['cost_usd'] / max(t['runs'], 1):.2f} | {t['seconds'] / max(t['runs'], 1):.0f} |")
    L.append("")

    L.append("**Paired comparisons** (exact McNemar, two-sided; A only = items A got right and B didn't)")
    L.append("")
    L.append("| A vs B | Problems: pairs, A only, B only, p | Publish calls: pairs, A only, B only, p |")
    L.append("|---|---|---|")
    tests = []
    for i, a in enumerate(conds):
        for b in conds[i + 1:]:
            pa = {k: majority(v["hits"]) for k, v in pooled[a]["problems"].items()}
            pb = {k: majority(v["hits"]) for k, v in pooled[b]["problems"].items()}
            da = {k: majority(v["right"]) for k, v in pooled[a]["decisions"].items()}
            db = {k: majority(v["right"]) for k, v in pooled[b]["decisions"].items()}
            n1, b1, c1, p1 = paired(pa, pb)
            n2, b2, c2, p2 = paired(da, db)
            tests.append({"a": a, "b": b, "problems": [n1, b1, c1, p1], "publish": [n2, b2, c2, p2]})
            L.append(f"| {LABELS.get(a, a)} vs {LABELS.get(b, b)} | {n1}, {b1}, {c1}, p = {fmt_p(p1)}"
                     f" | {n2}, {b2}, {c2}, p = {fmt_p(p2)} |")
    L.append("")

    L.append("**Scoring rule change** (new whole-word rules versus the original string rules)")
    L.append("")
    for c in conds:
        t = pooled[c]["t"]
        ch = pooled[c]["rule_changes"]
        L.append(f"- {LABELS.get(c, c)}: {t['caught_old']} caught under the old rules, {t['caught']} under the new"
                 f" ({len(ch)} changed)" + (": " + "; ".join(x.split(' ', 2)[2] for x in ch) if ch else ""))
    L.append("")
    text = "\n".join(L)
    if write:
        os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
        open(os.path.join(HERE, "results", "summary.md"), "w").write(text + "\n")
        out = {"versions": versions, "tests": tests,
               "conditions": {c: {"totals": dict(pooled[c]["t"]), "adjudicated": dict(pooled[c]["adjudicated"]),
                                  "repeats": pooled[c]["repeats"], "rule_changes": pooled[c]["rule_changes"]}
                              for c in conds}}
        json.dump(out, open(os.path.join(HERE, "results", "summary.json"), "w"), indent=1, ensure_ascii=False)
    return text, per_run, pooled, tests


def report(version, flags=False):
    res = adjudicate(score(version))
    print(f"Run {version} (cases: {cases_file(version)})")
    for cond, s in res.items():
        print(f"\n== {cond} ({s['runs']} drafts, repeats {s['repeats']}, {s['unparsed']} unparsed)")
        maj = sum(majority(p["hits"]) for p in s["problems"].values())
        print(f"  caught {maj}/{len(s['problems'])} planted problems by majority; "
              f"{s['caught']}/{s['planted']} across all repeats ({pct(s['caught'], s['planted'])})")
        print(f"  publish call right: {s['publish_right']}/{s['publish_total']}; clean drafts blocked "
              f"{s['clean_blocked']}/{s['clean_decided']}; clean drafts with any flag {s['clean_flagged']}/{s['clean_runs']}")
        print(f"  extra flags {s['extra_flags']} ruled {s['adjudicated']}; duplicate flags on a planted problem {s['dup_flags']}")
        print(f"  cost ${s['cost_usd']:.2f}, avg {s['seconds'] / max(s['runs'], 1):.0f}s per draft")
        print("  by type: " + ", ".join(f"{k} {v[0]}/{v[1]}" for k, v in s["by_type"].items()))
        if s["missed"]:
            print("  missed: " + " | ".join(s["missed"]))
        if s["rule_changes"]:
            print("  changed by the new matching rules: " + " | ".join(s["rule_changes"]))
        if flags:
            for e in s["extras"]:
                print("    extra: " + e)
            for e in s["dups"]:
                print("    duplicate: " + e)
    return res


def main(argv):
    if not argv:
        print(__doc__)
        return 1
    if argv[0] == "summary":
        versions = [a for a in argv[1:] if not a.startswith("--")] or DEFAULT_VERSIONS
        text, per_run, _, _ = summary(versions)
        print(text)
        unruled = [e for v in per_run.values() for s in v.values() for e in s["unruled"]]
        if unruled:
            print(f"{len(unruled)} extra flags have no hand ruling yet:")
            for e in unruled:
                print("  " + e)
        return 0
    version = argv[0]
    res = report(version, flags="--flags" in argv)
    if "--json" in argv:
        json.dump(res, open(os.path.join(RUNS, version, "score.json"), "w"), indent=1, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
