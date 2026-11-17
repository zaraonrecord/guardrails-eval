"""Run each condition over every case with the Claude CLI (headless, no tools, no settings).

    python3 run.py v1            # all conditions, results in runs/v1/<condition>/<case>.json
    python3 run.py v1 baseline   # one condition

Outputs are cached: rerunning skips cases that already have a result.
Skill files are read from paths given in conditions.py, so paid Skill text never has to live in this repo.
"""
import concurrent.futures as cf
import json
import os
import subprocess
import sys
import time

from conditions import CONDITIONS, system_prompt

HERE = os.path.dirname(os.path.abspath(__file__))
CLAUDE = os.path.expanduser("~/.local/bin/claude")
MODEL = os.environ.get("EVAL_MODEL", "sonnet")

TASK = """Here is a draft that is about to be published. Channel: {channel}.

<draft>
{text}
</draft>

Review it before it goes out, the way you normally would.

Then end your reply with one JSON code block in exactly this shape:
```json
{{"issues": [{{"quote": "the exact words from the draft", "type": "one type from the list"}}], "publish": false}}
```
List every problem that should stop or change publication, quoting the draft's exact words. For a missing label, quote the opening words of the draft.
Types: invented_stat, superlative, guarantee, fake_testimonial, health_claim, green_claim, fake_urgency, ai_slop, missing_disclosure, other.
If nothing needs changing, return an empty list and "publish": true."""


def run_one(version, cond, case):
    out_dir = os.path.join(HERE, "runs", version, cond)
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, case["id"] + ".json")
    if os.path.exists(path):
        return path, "cached"
    prompt = TASK.format(channel=case["channel"], text=case["text"])
    cmd = [CLAUDE, "-p", "--model", MODEL, "--system-prompt", system_prompt(cond), "--tools", "",
           "--strict-mcp-config", "--setting-sources", "", "--no-session-persistence", "--output-format", "json"]
    t0 = time.time()
    for attempt in range(3):
        r = subprocess.run(cmd, input=prompt, capture_output=True, text=True, timeout=300)
        try:
            d = json.loads(r.stdout)
            break
        except json.JSONDecodeError:
            time.sleep(5 * (attempt + 1))
    else:
        return path, "failed: " + (r.stderr or r.stdout)[:200]
    rec = {"case": case["id"], "condition": cond, "model": MODEL, "result": d.get("result", ""),
           "cost_usd": d.get("total_cost_usd"), "seconds": round(time.time() - t0, 1),
           "models": list((d.get("modelUsage") or {}).keys())}
    json.dump(rec, open(path, "w"), indent=1, ensure_ascii=False)
    return path, "ok"


def main():
    version = sys.argv[1]
    conds = sys.argv[2:] or list(CONDITIONS)
    cases = json.load(open(os.path.join(HERE, "data", os.environ.get("CASES", "cases.json"))))
    jobs = [(c, case) for c in conds for case in cases]
    done = 0
    with cf.ThreadPoolExecutor(max_workers=int(os.environ.get("EVAL_WORKERS", "4"))) as ex:
        futs = {ex.submit(run_one, version, c, case): (c, case["id"]) for c, case in jobs}
        for f in cf.as_completed(futs):
            done += 1
            _, status = f.result()
            if status not in ("ok", "cached"):
                print(futs[f], status)
            if done % 25 == 0:
                print(f"{done}/{len(jobs)}", flush=True)
    print(f"done: {len(jobs)} runs")


if __name__ == "__main__":
    main()
