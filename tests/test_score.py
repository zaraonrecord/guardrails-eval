import json

import pytest

import score
from score import (
    contains_run,
    majority,
    mcnemar_exact,
    norm,
    overlaps,
    overlaps_v1,
    paired,
    parse,
    points_at_missing_label,
    repeat_of,
    score_records,
)


def test_norm_lowercases_and_strips_punctuation():
    assert norm("The UK's BEST tea!") == ["the", "uk's", "best", "tea"]
    assert norm("“Best” ’tea’ #ad") == ["best", "'tea'", "ad"]
    assert norm("Was £12, now £8 (30%)") == ["was", "£12", "now", "£8", "30%"]
    assert norm(None) == [] and norm("") == []


def test_contains_run_is_whole_word():
    assert contains_run(["made", "with", "love"], ["with", "love"])
    assert not contains_run(["made", "with", "love"], ["love", "with"])
    assert not contains_run(["ad"], ["ad", "x"])
    assert not contains_run(["a"], [])


@pytest.mark.parametrize("quote", ["tea", "ad", "Tea.", "the"])
def test_single_word_cannot_catch_long_span(quote):
    span = "The UK's best loose leaf tea, made by hand"
    assert not overlaps(quote, span)


def test_old_rule_had_the_tea_and_ad_bug():
    # the original rule compared joined strings, so these counted as catches
    assert overlaps_v1("tea", "The UK's best loose leaf tea")
    assert overlaps_v1("ad", "Loved by tea drinkers, made by hand")
    assert not overlaps("ad", "Loved by tea drinkers, made by hand")


def test_quote_covering_span_matches():
    assert overlaps("Honestly, the UK's best loose leaf tea, packed in Bristol", "The UK's best loose leaf tea")


def test_quote_inside_span_needs_enough_words():
    span = "Brewed with care. Packed with love. Delivered with a smile."
    assert overlaps("Packed with love. Delivered with a smile.", span)
    assert not overlaps("love", span)
    # short spans: one distinctive word covering 40%+ is enough
    assert overlaps("The finest", "The finest organic loose leaf")
    assert not overlaps("guaranteed", "Good tea, guaranteed. Risk-free.")


def test_shared_words_rule_on_tokens():
    # reordered quote with 60%+ of the span's words
    assert overlaps("immunity boosts your", "boosts your immunity through winter")
    assert not overlaps("winter tea for you", "boosts your immunity through winter")


def test_empty_inputs():
    assert not overlaps("", "anything")
    assert not overlaps("anything", "")


def test_parse_takes_last_valid_block():
    text = 'First ```json\n{"issues": [{"quote": "a"}], "publish": false}\n```\nthen ```json\n{"issues": [], "publish": true}\n```'
    assert parse(text) == ([], True)


def test_parse_skips_malformed_last_block():
    text = '```json\n{"issues": [{"quote": "x", "type": "other"}], "publish": false}\n```\n```json\n{"issues": [oops}\n```'
    issues, publish = parse(text)
    assert issues == [{"quote": "x", "type": "other"}] and publish is False


def test_parse_no_block_or_garbage():
    assert parse("no json here") == (None, None)
    assert parse("```json\n{not json}\n```") == (None, None)
    assert parse(None) == (None, None)


def test_parse_drops_bad_shapes():
    issues, publish = parse('```json\n{"issues": ["str", {"quote": "q"}], "publish": "yes"}\n```')
    assert issues == [{"quote": "q"}] and publish is None


DRAFT = "My afternoon reset is a pot of Assam and ten minutes away from my phone. #tea #ad #selfcare"


@pytest.mark.parametrize("quote", [
    "My afternoon reset is a pot of Assam",
    "My afternoon reset",
    "#ad",
    "no Ad label at the start",
    "affiliate link not disclosed",
    "Gifted",
    "I may earn a small commission",
    "sponsored content",
])
def test_missing_label_counts_when_it_points_at_the_label(quote):
    assert points_at_missing_label({"type": "missing_disclosure", "quote": quote}, DRAFT)


@pytest.mark.parametrize("issue", [
    {"type": "missing_disclosure", "quote": "ten minutes away from my phone"},
    {"type": "missing_disclosure", "quote": ""},
    {"type": "missing_disclosure"},
    {"type": "other", "quote": "My afternoon reset"},
    {"type": "health_claim", "quote": "#ad"},
    {"type": "missing_disclosure", "quote": "made with love"},  # no "ad" token inside "made"
])
def test_missing_label_does_not_count_otherwise(issue):
    assert not points_at_missing_label(issue, DRAFT)


def test_repeat_of():
    assert repeat_of("b01.json") == ("b01", 1)
    assert repeat_of("b01.r3.json") == ("b01", 3)
    assert repeat_of("manifest.txt") is None


def test_majority_and_ties():
    assert majority([True])
    assert not majority([False])
    assert majority([True, True, False])
    assert not majority([True, False])  # tie counts as missed
    assert not majority([])
    assert majority([True, None])


def test_mcnemar_exact():
    assert mcnemar_exact(0, 0) == 1.0
    assert mcnemar_exact(0, 3) == pytest.approx(0.25)
    assert mcnemar_exact(3, 0) == pytest.approx(0.25)
    assert mcnemar_exact(0, 4) == pytest.approx(0.125)
    # 12 vs 2: 2 * (1 + 14 + 91) / 2**14
    assert mcnemar_exact(12, 2) == pytest.approx(2 * 106 / 16384)
    assert mcnemar_exact(5, 5) == 1.0


def test_paired_counts_discordant_pairs_on_shared_keys():
    a = {"x": True, "y": True, "z": False, "only_a": True}
    b = {"x": True, "y": False, "z": True}
    assert paired(a, b) == (3, 1, 1, 1.0)


def _rec(case, issues, publish):
    body = json.dumps({"issues": issues, "publish": publish})
    return {"case": case, "result": f"Review.\n```json\n{body}\n```", "cost_usd": 0.01, "seconds": 10}


CASES = {
    "c1": {"id": "c1", "text": "Good tea, packed by hand.", "planted": []},
    "c2": {"id": "c2", "text": "The UK's best loose leaf tea, packed by hand.",
           "planted": [{"type": "superlative", "span": "The UK's best loose leaf tea"}]},
    "c3": {"id": "c3", "text": "My afternoon reset is a pot of tea.", "planted": [{"type": "missing_disclosure", "span": None}]},
}


def test_score_records_synthetic():
    records = [
        (1, _rec("c1", [{"quote": "Good tea", "type": "other"}], False)),           # false block on a clean draft
        (1, _rec("c2", [{"quote": "tea", "type": "superlative"},                   # too short: extra under new rule
                        {"quote": "The UK's best loose leaf tea", "type": "superlative"},
                        {"quote": "UK's best loose leaf", "type": "superlative"}], False)),  # duplicate
        (1, _rec("c3", [{"quote": "a pot of tea", "type": "missing_disclosure"}], False)),  # not pointing at label
    ]
    s = score_records("t", "cond", CASES, records)
    assert s["planted"] == 2 and s["caught"] == 1
    assert s["caught_old"] == 2  # old rule counted any missing_disclosure flag
    assert len(s["rule_changes"]) == 1 and "no longer caught" in s["rule_changes"][0]
    assert s["dup_flags"] == 1
    assert s["extra_flags"] == 3  # "Good tea", "tea", "a pot of tea"
    assert s["extra_on_clean"] == 1
    assert s["clean_runs"] == 1 and s["clean_flagged"] == 1 and s["clean_blocked"] == 1
    assert s["publish_right"] == 2 and s["publish_total"] == 3
    assert s["problems"]["t/c2/0"]["hits"] == [True]
    assert s["problems"]["t/c3/0"]["hits"] == [False]


def test_score_records_with_repeats():
    good = _rec("c2", [{"quote": "The UK's best loose leaf tea", "type": "superlative"}], False)
    miss = _rec("c2", [], True)
    s = score_records("t", "cond", CASES, [(1, good), (2, miss), (3, good)])
    hits = s["problems"]["t/c2/0"]["hits"]
    assert hits == [True, False, True] and majority(hits)
    assert s["decisions"]["t/c2"]["right"] == [True, False, True]
    assert s["repeats"] == [1, 2, 3]


def test_unparsed_reply_counts_as_no_flags():
    s = score_records("t", "cond", CASES, [(1, {"case": "c2", "result": "no json"})])
    assert s["unparsed"] == 1 and s["caught"] == 0 and s["publish_total"] == 0


def test_cases_file_prefers_manifest(tmp_path, monkeypatch):
    monkeypatch.setattr(score, "RUNS", str(tmp_path))
    (tmp_path / "v2-x").mkdir()
    assert score.cases_file("v2-x") == "cases-v2.json"  # fallback
    (tmp_path / "v2-x" / "manifest.json").write_text(json.dumps({"cases_file": "cases.json"}))
    assert score.cases_file("v2-x") == "cases.json"
