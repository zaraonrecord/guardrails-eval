"""The setups being compared. Each gets the same brand policy and the same task.

baseline_long is a control: plain Claude plus a generic, brand-agnostic review checklist
(data/generic-review-checklist.md) about as long as the Guardrails Skill text. If the Skills only
help because they make the prompt longer and more detailed, this setup should do as well.
The checklist was written from general advertising-review common sense, without reading the Guardrails
Skills, and avoids the exact phrases planted in the test cases (tests/test_conditions.py checks).
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
FREE = os.path.expanduser(os.environ.get("FREE_SKILLS", "~/Projects/claude-marketing-skills/skills"))
# The Guardrails pack is a free download (marketingprompthub.com/guardrails/). Point GUARDRAILS_SKILLS at its
# unzipped skills folder. PAID_SKILLS is the old name, still read as a fallback.
GUARDRAILS = os.path.expanduser(os.environ.get("GUARDRAILS_SKILLS") or os.environ.get("PAID_SKILLS")
                                or "~/Projects/marketing-prompt-hub/content/guardrails/skills")


def _skill(root, name):
    return open(os.path.join(root, name, "SKILL.md"), encoding="utf-8").read()


def _checklist():
    return open(os.path.join(HERE, "data", "generic-review-checklist.md"), encoding="utf-8").read()


BASELINE = "You are a careful marketing editor. Check marketing copy before it is published."


def policy_name():
    # POLICY=full (default) or minimal: how much the team has written down
    return "minimal" if os.environ.get("POLICY") == "minimal" else "full"


def _policy():
    name = "brand-policy-minimal.md" if policy_name() == "minimal" else "brand-policy.md"
    return open(os.path.join(HERE, "data", name), encoding="utf-8").read()


CONDITIONS = {
    # Plain Claude, told what the job is, with the brand policy. The baseline.
    "baseline": lambda: BASELINE,
    # Control: the same one-liner plus a generic checklist of about the same length as the Guardrails text.
    "baseline_long": lambda: BASELINE + "\n\n" + _checklist(),
    # The free, public guardrail Skills (CC BY 4.0).
    "free_skills": lambda: "\n\n---\n\n".join(_skill(FREE, n) for n in ("claims-guard", "slop-guard", "honest-review-rules")),
    # The Guardrails pack: the publish gate and the checks it runs.
    "guardrails": lambda: "\n\n---\n\n".join(
        _skill(GUARDRAILS, n)
        for n in ("publish-gate", "claims-evidence-log", "regulated-claims-check", "disclosure-check", "house-style-guard")
    ),
}


def system_prompt(cond):
    body = CONDITIONS[cond]()
    return (body + "\n\n---\n\nThe brand policy for this brand (it is also the claims allowlist):\n\n" + _policy()
            + "\n\nYou have no tools in this session. Do every check yourself, in your reply.")
