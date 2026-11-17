"""Run each condition over every case with the Claude CLI (headless, no tools, no settings).

    python3 run.py v1                         # all conditions, results in runs/v1/<condition>/<case>.json
    python3 run.py v1 baseline                # one condition
    REPEATS=3 python3 run.py v1 baseline      # repeats 1 to 3: <case>.json, <case>.r2.json, <case>.r3.json
    python3 run.py adopt v1 [conditions]      # stamp the current hash on old records that have none (see below)

Settings come from the environment: CASES (default cases.json), POLICY (full or minimal),
EVAL_MODEL (default sonnet), REPEATS (default 1), EVAL_WORKERS (default 4), EVAL_TIMEOUT (seconds, default 300).

Caching. Every record stores a hash of the system prompt, the task prompt, the model and the policy.
A record is reused only when its hash matches what would be sent now. If a record exists with a
different hash, or none, the run stops before calling the model, so old and new prompts never mix.
REPLACE_STALE=1 moves those records to runs/<version>/_stale/ and runs them again.

`adopt` is for records made before hashes existed. It stamps the current hash on them and marks
them "hash_adopted". Only use it when you know the prompts, Skills, policy and cases have not changed
since those records were made.

Each run also writes runs/<version>/manifest.json (cases file, policy, model, prompt hashes), which
score.py reads, so both always agree on which cases a run used.
Skill files are read from paths given in conditions.py (FREE_SKILLS, GUARDRAILS_SKILLS), not copied into this repo.
"""
import concurrent.futures as cf
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

from conditions import CONDITIONS, policy_name, system_prompt

HERE = os.path.dirname(os.path.abspath(__file__))
CLAUDE = os.path.expanduser("~/.local/bin/claude")

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


def settings():
    return {"cases_file": os.environ.get("CASES", "cases.json"), "policy": policy_name(),
            "model": os.environ.get("EVAL_MODEL", "sonnet")}


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def task_prompt(case):
    return TASK.format(channel=case["channel"], text=case["text"])


def prompt_hash(system, task, model, policy):
    """The cache key: everything that decides what the model is asked."""
    return sha(json.dumps({"system": system, "task": task, "model": model, "policy": policy}, sort_keys=True))


def record_path(version, cond, case_id, repeat):
    name = f"{case_id}.json" if repeat == 1 else f"{case_id}.r{repeat}.json"
    return os.path.join(HERE, "runs", version, cond, name)


def cache_status(path, h):
    """'missing', 'cached' (hash matches) or 'stale' (exists with another hash, or none)."""
    if not os.path.exists(path):
        return "missing"
    try:
        rec = json.load(open(path))
    except (OSError, json.JSONDecodeError):
        return "stale"
    return "cached" if rec.get("hash") == h else "stale"


def call_claude(cmd, prompt, timeout):
    """Up to three tries. Returns (parsed CLI output or None, error text)."""
    err = ""
    for attempt in range(3):
        try:
            r = subprocess.run(cmd, input=prompt, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            err = f"timed out after {timeout}s"
        else:
            try:
                return json.loads(r.stdout), ""
            except json.JSONDecodeError:
                err = (r.stderr or r.stdout)[:200]
        time.sleep(5 * (attempt + 1))
    return None, err


def run_one(version, cond, case, repeat, system, cfg):
    path = record_path(version, cond, case["id"], repeat)
    prompt = task_prompt(case)
    h = prompt_hash(system, prompt, cfg["model"], cfg["policy"])
    status = cache_status(path, h)
    if status == "cached":
        return path, "cached"
    if status == "stale":
        return path, "stale: exists with a different prompt hash"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    cmd = [CLAUDE, "-p", "--model", cfg["model"], "--system-prompt", system, "--tools", "",
           "--strict-mcp-config", "--setting-sources", "", "--no-session-persistence", "--output-format", "json"]
    t0 = time.time()
    d, err = call_claude(cmd, prompt, int(os.environ.get("EVAL_TIMEOUT", "300")))
    if d is None:
        return path, "failed: " + err
    rec = {"case": case["id"], "condition": cond, "repeat": repeat, "model": cfg["model"], "policy": cfg["policy"],
           "cases_file": cfg["cases_file"], "hash": h, "result": d.get("result", ""),
           "cost_usd": d.get("total_cost_usd"), "seconds": round(time.time() - t0, 1),
           "models": list((d.get("modelUsage") or {}).keys())}
    tmp = path + ".tmp"
    json.dump(rec, open(tmp, "w"), indent=1, ensure_ascii=False)
    os.replace(tmp, path)
    return path, "ok"


def write_manifest(version, cfg, conds, systems, check_only=False):
    """Record what this run used. Refuses to mix cases, policy or model within one version."""
    path = os.path.join(HERE, "runs", version, "manifest.json")
    m = json.load(open(path)) if os.path.exists(path) else {}
    for k in ("cases_file", "policy", "model"):
        if m.get(k) not in (None, cfg[k]):
            sys.exit(f"runs/{version} was made with {k}={m[k]}, not {cfg[k]}. Use a new version name.")
    if check_only:
        return
    m.update(cfg)
    m["task_template_sha256"] = sha(TASK)
    m.setdefault("conditions", {})
    for c in conds:
        m["conditions"][c] = {"system_prompt_sha256": sha(systems[c]), "system_prompt_chars": len(systems[c])}
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(m, open(path, "w"), indent=1, sort_keys=True)
    open(path, "a").write("\n")


def plan(version, conds, cases, repeats, systems, cfg):
    jobs, stale = [], []
    for c in conds:
        for case in cases:
            for r in range(1, repeats + 1):
                path = record_path(version, c, case["id"], r)
                h = prompt_hash(systems[c], task_prompt(case), cfg["model"], cfg["policy"])
                st = cache_status(path, h)
                if st == "stale":
                    stale.append(path)
                jobs.append((c, case, r, st))
    return jobs, stale


def move_stale(version, paths):
    for p in paths:
        rel = os.path.relpath(p, os.path.join(HERE, "runs", version))
        dest = os.path.join(HERE, "runs", version, "_stale", rel)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.move(p, dest)


def adopt(version, conds, cases, systems, cfg):
    n = 0
    for c in conds:
        d = os.path.join(HERE, "runs", version, c)
        if not os.path.isdir(d):
            continue
        for case in cases:
            for r in range(1, 100):
                path = record_path(version, c, case["id"], r)
                if not os.path.exists(path):
                    break
                rec = json.load(open(path))
                if rec.get("hash"):
                    continue
                if rec.get("model") != cfg["model"]:
                    sys.exit(f"{path} was made with model {rec.get('model')}, not {cfg['model']}")
                rec.update({"hash": prompt_hash(systems[c], task_prompt(case), cfg["model"], cfg["policy"]),
                            "hash_adopted": True, "repeat": r, "policy": cfg["policy"], "cases_file": cfg["cases_file"]})
                json.dump(rec, open(path, "w"), indent=1, ensure_ascii=False)
                n += 1
    print(f"adopted {n} records in runs/{version}")


def main(argv):
    if not argv:
        print(__doc__)
        return 1
    adopting = argv[0] == "adopt"
    if adopting:
        argv = argv[1:]
    version = argv[0]
    conds = argv[1:] or list(CONDITIONS)
    unknown = [c for c in conds if c not in CONDITIONS]
    if unknown:
        sys.exit(f"unknown condition(s): {unknown}")
    cfg = settings()
    repeats = int(os.environ.get("REPEATS", "1"))
    cases = json.load(open(os.path.join(HERE, "data", cfg["cases_file"])))
    systems = {c: system_prompt(c) for c in conds}
    write_manifest(version, cfg, conds, systems, check_only=True)
    if adopting:
        write_manifest(version, cfg, conds, systems)
        adopt(version, conds, cases, systems, cfg)
        return 0

    jobs, stale = plan(version, conds, cases, repeats, systems, cfg)
    if stale:
        if os.environ.get("REPLACE_STALE") != "1":
            print(f"{len(stale)} existing records were made with a different prompt, Skill text, policy or model "
                  f"(or before hashes existed), for example {os.path.relpath(stale[0], HERE)}.")
            print("Refusing to mix them with new results. Set REPLACE_STALE=1 to move them to "
                  f"runs/{version}/_stale/ and rerun, or use a new version name.")
            return 2
        move_stale(version, stale)
        print(f"moved {len(stale)} stale records to runs/{version}/_stale/")
        jobs = [(c, case, r, "missing" if st == "stale" else st) for c, case, r, st in jobs]
    write_manifest(version, cfg, conds, systems)

    todo = [(c, case, r) for c, case, r, st in jobs if st != "cached"]
    print(f"{len(jobs)} records wanted, {len(jobs) - len(todo)} cached, {len(todo)} to run", flush=True)
    done, failed = 0, 0
    with cf.ThreadPoolExecutor(max_workers=int(os.environ.get("EVAL_WORKERS", "4"))) as ex:
        futs = {ex.submit(run_one, version, c, case, r, systems[c], cfg): (c, case["id"], r) for c, case, r in todo}
        for f in cf.as_completed(futs):
            done += 1
            try:
                _, status = f.result()
            except Exception as e:  # one bad job must not kill the run
                status = f"failed: {e!r}"
            if status not in ("ok", "cached"):
                failed += 1
                print(futs[f], status, flush=True)
            if done % 25 == 0:
                print(f"{done}/{len(todo)}", flush=True)
    print(f"done: {len(todo)} run, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
