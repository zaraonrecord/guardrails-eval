"""The three setups being compared. Each gets the same brand policy and the same task."""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
FREE = os.path.expanduser(os.environ.get("FREE_SKILLS", "~/Projects/claude-marketing-skills/skills"))
PAID = os.path.expanduser(os.environ.get("PAID_SKILLS", "~/Projects/marketing-prompt-hub/content/guardrails/skills"))


def _skill(root, name):
    return open(os.path.join(root, name, "SKILL.md"), encoding="utf-8").read()


def _policy():
    # POLICY=full (default) or minimal: how much the team has written down
    name = "brand-policy-minimal.md" if os.environ.get("POLICY") == "minimal" else "brand-policy.md"
    return open(os.path.join(HERE, "data", name), encoding="utf-8").read()


CONDITIONS = {
    # Plain Claude, told what the job is, with the brand policy. The baseline.
    "baseline": lambda: "You are a careful marketing editor. Check marketing copy before it is published.",
    # The free, public guardrail Skills (CC BY 4.0).
    "free_skills": lambda: "\n\n---\n\n".join(_skill(FREE, n) for n in ("claims-guard", "slop-guard", "honest-review-rules")),
    # The Guardrails pack: the publish gate and the checks it runs.
    "guardrails": lambda: "\n\n---\n\n".join(_skill(PAID, n) for n in ("publish-gate", "claims-evidence-log", "regulated-claims-check", "disclosure-check", "house-style-guard")),
}


def system_prompt(cond):
    body = CONDITIONS[cond]()
    return (body + "\n\n---\n\nThe brand policy for this brand (it is also the claims allowlist):\n\n" + _policy()
            + "\n\nYou have no tools in this session. Do every check yourself, in your reply.")
