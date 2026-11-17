"""Score a run: did each setup catch the planted problems, and how often did it cry wolf?

    python3 score.py v1-full            # prints a summary
    python3 score.py v1-full --json     # writes runs/v1-full/score.json too
    python3 score.py v1-full --flags    # lists every unmatched flag, for checking by hand

Matching is deterministic. A planted problem with a span counts as caught when a flagged quote
overlaps it (one contains the other, or they share at least 60% of the span's words).
A missing label counts as caught when any flag has type missing_disclosure.
Any flag that doesn't match a planted problem is an "extra flag". On clean drafts every flag is extra.
"""
import json
import os
import re
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))


def norm(s):
    s = (s or "").lower().replace("’", "'").replace("“", '"').replace("”", '"')
    return re.sub(r"[^a-z0-9%£' ]+", " ", s).split()


def overlaps(quote, span):
    q, p = norm(quote), norm(span)
    if not q or not p:
        return False
    qs, ps = " ".join(q), " ".join(p)
    if qs in ps or ps in qs:
        return True
    return len(set(q) & set(p)) / len(set(p)) >= 0.6


def parse(result):
    blocks = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", result, re.S)
    for b in reversed(blocks):
        try:
            d = json.loads(b)
            return d.get("issues") or [], d.get("publish")
        except json.JSONDecodeError:
            continue
    return None, None


def score(version):
    cases = {c["id"]: c for c in json.load(open(os.path.join(HERE, "data", "cases-v2.json" if version.startswith("v2") else "cases.json")))}
    out = {}
    root = os.path.join(HERE, "runs", version)
    for cond in sorted(os.listdir(root)):
        d = os.path.join(root, cond)
        if not os.path.isdir(d):
            continue
        s = {"planted": 0, "caught": 0, "by_type": defaultdict(lambda: [0, 0]), "clean_cases": 0, "clean_flagged": 0,
             "extra_flags": 0, "extra_on_clean": 0, "publish_right": 0, "publish_total": 0, "unparsed": 0,
             "cost_usd": 0.0, "seconds": 0.0, "runs": 0, "missed": [], "extras": []}
        for f in sorted(os.listdir(d)):
            if not f.endswith(".json"):
                continue
            rec = json.load(open(os.path.join(d, f)))
            case = cases[rec["case"]]
            s["runs"] += 1
            s["cost_usd"] += rec.get("cost_usd") or 0
            s["seconds"] += rec.get("seconds") or 0
            issues, publish = parse(rec["result"])
            if issues is None:
                s["unparsed"] += 1
                issues, publish = [], None
            used = set()
            for p in case["planted"]:
                s["planted"] += 1
                s["by_type"][p["type"]][1] += 1
                hit = None
                for i, iss in enumerate(issues):
                    if p["span"] is None:
                        if iss.get("type") == "missing_disclosure":
                            hit = i
                    elif overlaps(iss.get("quote", ""), p["span"]):
                        hit = i
                    if hit is not None:
                        break
                if hit is not None:
                    s["caught"] += 1
                    s["by_type"][p["type"]][0] += 1
                    used.add(hit)
                    # a flag can satisfy two planted problems on the same words (e.g. testimonial + health claim)
                else:
                    s["missed"].append(f"{case['id']} {p['type']}: {p['span']}")
            # mark other flags that overlap any planted span as used too
            for i, iss in enumerate(issues):
                if i in used:
                    continue
                if any((p["span"] and overlaps(iss.get("quote", ""), p["span"])) or (p["span"] is None and iss.get("type") == "missing_disclosure") for p in case["planted"]):
                    used.add(i)
            extras = [iss for i, iss in enumerate(issues) if i not in used]
            s["extra_flags"] += len(extras)
            for e in extras:
                s["extras"].append(f"{case['id']} [{e.get('type')}] {e.get('quote', '')[:120]}")
            if not case["planted"]:
                s["clean_cases"] += 1
                s["extra_on_clean"] += len(extras)
                if issues:
                    s["clean_flagged"] += 1
            if publish is not None:
                s["publish_total"] += 1
                s["publish_right"] += int(bool(publish) == (not case["planted"]))
        s["by_type"] = {k: v for k, v in sorted(s["by_type"].items())}
        out[cond] = s
    return out


def adjudicate(res):
    """Apply hand rulings to unmatched flags: count how many were valid, false alarms, borderline or unruled."""
    path = os.path.join(HERE, "data", "adjudication.json")
    rulings = json.load(open(path))["rulings"] if os.path.exists(path) else []
    for cond, s in res.items():
        tally = Counter()
        unruled = []
        for e in s["extras"]:
            cid = e.split(" ", 1)[0]
            r = next((r for r in rulings if r["case"] in (cid, "*") and r["match"].lower() in e.lower()), None)
            if r:
                tally[r["verdict"]] += 1
            else:
                tally["unruled"] += 1
                unruled.append(e)
        s["adjudicated"] = dict(tally)
        s["unruled"] = unruled
    return res


def pct(a, b):
    return f"{(100 * a / b):.0f}%" if b else "n/a"


def main():
    version = sys.argv[1]
    res = adjudicate(score(version))
    print(f"Run {version}")
    for cond, s in res.items():
        print(f"\n== {cond} ({s['runs']} drafts, {s['unparsed']} unparsed)")
        print(f"  caught {s['caught']}/{s['planted']} planted problems ({pct(s['caught'], s['planted'])})")
        print(f"  clean drafts flagged: {s['clean_flagged']}/{s['clean_cases']} ({pct(s['clean_flagged'], s['clean_cases'])}), extra flags total {s['extra_flags']}")
        print(f"  extra flags ruled: {s['adjudicated']}")
        print(f"  publish decision right: {s['publish_right']}/{s['publish_total']}")
        print(f"  cost ${s['cost_usd']:.2f}, avg {s['seconds'] / max(s['runs'], 1):.0f}s per draft")
        print("  by type: " + ", ".join(f"{k} {v[0]}/{v[1]}" for k, v in s["by_type"].items()))
        if s["missed"]:
            print("  missed: " + " | ".join(s["missed"]))
        if "--flags" in sys.argv:
            for e in s["extras"]:
                print("    extra: " + e)
    if "--json" in sys.argv:
        json.dump(res, open(os.path.join(HERE, "runs", version, "score.json"), "w"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
