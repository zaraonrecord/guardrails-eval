import json
import os

import pytest

import conditions
from score import norm

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_conditions_present():
    assert {"baseline", "baseline_long", "free_skills", "guardrails"} <= set(conditions.CONDITIONS)


def test_baseline_long_starts_with_the_baseline():
    assert conditions.CONDITIONS["baseline_long"]().startswith(conditions.CONDITIONS["baseline"]())


@pytest.mark.skipif(not os.path.isdir(conditions.GUARDRAILS), reason="Guardrails Skills folder not available")
def test_baseline_long_is_within_10_percent_of_guardrails_length():
    a = len(conditions.CONDITIONS["baseline_long"]())
    b = len(conditions.CONDITIONS["guardrails"]())
    assert 0.9 <= a / b <= 1.1, (a, b)


def test_checklist_avoids_planted_phrases():
    """The control must not be taught the test: no three-word run from any planted span."""
    text = norm(conditions.CONDITIONS["baseline_long"]())
    grams = {tuple(text[i:i + 3]) for i in range(len(text) - 2)}
    hits = []
    for name in ("cases.json", "cases-v2.json"):
        for case in json.load(open(os.path.join(HERE, "data", name))):
            for p in case["planted"]:
                if p["span"]:
                    t = norm(p["span"])
                    hits += [(case["id"], g) for g in {tuple(t[i:i + 3]) for i in range(len(t) - 2)} if g in grams]
    assert not hits, hits


def test_checklist_names_no_brand():
    text = conditions.CONDITIONS["baseline_long"]().lower()
    assert "pebblebrook" not in text and "tea" not in norm(text)
