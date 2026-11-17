import json

import run


def test_prompt_hash_is_stable_and_sensitive():
    h = run.prompt_hash("sys", "task", "sonnet", "full")
    assert h == run.prompt_hash("sys", "task", "sonnet", "full")
    assert h != run.prompt_hash("sys2", "task", "sonnet", "full")
    assert h != run.prompt_hash("sys", "task2", "sonnet", "full")
    assert h != run.prompt_hash("sys", "task", "opus", "full")
    assert h != run.prompt_hash("sys", "task", "sonnet", "minimal")


def test_record_path_naming(monkeypatch, tmp_path):
    monkeypatch.setattr(run, "HERE", str(tmp_path))
    assert run.record_path("v", "c", "b01", 1).endswith("runs/v/c/b01.json")
    assert run.record_path("v", "c", "b01", 2).endswith("runs/v/c/b01.r2.json")


def test_cache_status(tmp_path):
    p = tmp_path / "b01.json"
    assert run.cache_status(str(p), "h1") == "missing"
    p.write_text(json.dumps({"hash": "h1"}))
    assert run.cache_status(str(p), "h1") == "cached"
    assert run.cache_status(str(p), "h2") == "stale"
    p.write_text(json.dumps({"result": "legacy record, no hash"}))
    assert run.cache_status(str(p), "h1") == "stale"
    p.write_text("{broken")
    assert run.cache_status(str(p), "h1") == "stale"


def test_task_prompt_unchanged_shape():
    t = run.task_prompt({"channel": "email", "text": "Hello"})
    assert "Channel: email." in t and "<draft>\nHello\n</draft>" in t and '"publish": false}' in t


def test_timeout_is_caught(monkeypatch):
    def boom(*a, **k):
        raise run.subprocess.TimeoutExpired(cmd="claude", timeout=1)

    monkeypatch.setattr(run.subprocess, "run", boom)
    monkeypatch.setattr(run.time, "sleep", lambda s: None)
    d, err = run.call_claude(["claude"], "p", 1)
    assert d is None and "timed out" in err


def test_plan_flags_stale_and_cached(monkeypatch, tmp_path):
    monkeypatch.setattr(run, "HERE", str(tmp_path))
    cfg = {"model": "sonnet", "policy": "full", "cases_file": "x.json"}
    case = {"id": "b01", "channel": "email", "text": "Hi"}
    systems = {"baseline": "sys"}
    h = run.prompt_hash("sys", run.task_prompt(case), "sonnet", "full")
    d = tmp_path / "runs" / "v" / "baseline"
    d.mkdir(parents=True)
    (d / "b01.json").write_text(json.dumps({"hash": h}))
    (d / "b01.r2.json").write_text(json.dumps({"hash": "old"}))
    jobs, stale = run.plan("v", ["baseline"], [case], 3, systems, cfg)
    assert [j[3] for j in jobs] == ["cached", "stale", "missing"]
    assert stale == [str(d / "b01.r2.json")]
    run.move_stale("v", stale)
    assert (tmp_path / "runs" / "v" / "_stale" / "baseline" / "b01.r2.json").exists()
