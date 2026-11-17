#!/usr/bin/env bash
# The full rerun: four runs (round 1 and 2, full and bare policy) x four setups x 3 repeats,
# then rescore everything and regenerate results/summary.md.
#
#   ./rerun.sh 2>&1 | tee rerun.log
#
# Records are reused only when their prompt hash matches, so it is safe to stop and start again.
# Records made before hashes existed:
#   round 2 (v2-*) is adopted: every input (prompts, Skills, policies, cases, run.py) is older than those records.
#   round 1 (v1-*) is rerun, because run.py was edited after round 1 ran, so its prompt can't be proved
#   identical. The old records move to runs/v1-*/_stale/. Set ADOPT_V1=1 to adopt them instead.
#
# Needs the Claude CLI signed in, and GUARDRAILS_SKILLS pointing at the unzipped Guardrails skills
# folder if it isn't at the default path in conditions.py.
set -uo pipefail
cd "$(dirname "$0")"

CONDS="baseline baseline_long free_skills guardrails"
export REPEATS="${REPEATS:-3}"
export REPLACE_STALE=1

run_version() {  # version cases policy
  local v="$1"
  export CASES="$2" POLICY="$3"
  echo "== $v (cases $CASES, policy $POLICY, $REPEATS repeats)"
  if [[ "$v" == v2-* || "${ADOPT_V1:-0}" == "1" ]]; then
    python3 run.py adopt "$v" baseline free_skills guardrails
  fi
  # second pass retries anything that failed (finished records are cached)
  python3 run.py "$v" $CONDS || python3 run.py "$v" $CONDS || echo "!! $v still has failures, rerun this script later"
}

run_version v1-full cases.json full
run_version v1-min cases.json minimal
run_version v2-full cases-v2.json full
run_version v2-min cases-v2.json minimal

for v in v1-full v1-min v2-full v2-min; do
  python3 score.py "$v" --json > /dev/null
done
python3 score.py summary
echo "Summary written to results/summary.md. Rule any unruled flags in data/adjudication.json, then run: python3 score.py summary"
