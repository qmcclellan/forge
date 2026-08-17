#!/usr/bin/env bash
# mutation_ks0006.sh -- committed, reproducible mutation-testing harness for
# KS-0006's Forge -> Coder converter (forge/coder_target.py).
#
# Applies each mutation to a real copy of the module, runs the full KS-0006
# test suite against it, and asserts the suite FAILS (the mutant is killed).
# Every mutation is reverted before the next one runs, and the module is
# byte-identical to its starting state when this script exits, pass or fail.
#
# Usage: ./tests/mutation_ks0006.sh   (run from the repository root)
# Exit 0 = every mutation was killed and the module was left unchanged.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${HERE}"

MODULE="forge/coder_target.py"
BACKUP="$(mktemp)"
cp "${MODULE}" "${BACKUP}"

restore() { cp "${BACKUP}" "${MODULE}"; }
trap 'restore; rm -f "${BACKUP}"' EXIT

killed=0
survived=0

run_tests_quiet() {
  python3 -m pytest tests/test_ks0006_coder_target.py -q >/tmp/.ks0006_mutation_out 2>&1
}

assert_mutant_killed() {
  local name="$1"
  if run_tests_quiet; then
    echo "SURVIVED  ${name} -- the test suite did NOT fail against this mutant"
    survived=$((survived + 1))
  else
    echo "KILLED    ${name}"
    killed=$((killed + 1))
  fi
  restore
}

echo "=== baseline: suite must pass before any mutation ==="
if ! run_tests_quiet; then
  echo "ABORT: baseline suite does not pass on the unmutated module -- cannot trust mutation results"
  cat /tmp/.ks0006_mutation_out
  exit 2
fi
echo "baseline OK"
echo

echo "=== M1: bypass the runtime/image mapping (always emit a fixed image) ==="
python3 - "${MODULE}" <<'PY'
import sys
p = sys.argv[1]
s = open(p).read()
s = s.replace(
    "    return DEVCONTAINER_IMAGE_TEMPLATE.format(version=m.group(1))",
    '    return "mcr.microsoft.com/devcontainers/javascript-node:1-99-bullseye"  # MUTATION M1',
)
open(p, "w").write(s)
PY
assert_mutant_killed "M1: runtime/image mapping bypassed"

echo "=== M2: change the documented Node version resolution (always target Node 22, the live StarkGrid default, instead of the source's declared runtime) ==="
python3 - "${MODULE}" <<'PY'
import sys
p = sys.argv[1]
s = open(p).read()
s = s.replace(
    "    return DEVCONTAINER_IMAGE_TEMPLATE.format(version=m.group(1))",
    '    return DEVCONTAINER_IMAGE_TEMPLATE.format(version="22")  # MUTATION M2',
)
open(p, "w").write(s)
PY
assert_mutant_killed "M2: Node version resolution changed to the live-default 22"

echo "=== M3: remove unsupported-input rejection (accept any language) ==="
python3 - "${MODULE}" <<'PY'
import sys
p = sys.argv[1]
s = open(p).read()
s = s.replace(
    '''    if manifest["language"] != REQUIRED_LANGUAGE:
        raise UnsupportedForgeSource(
            f"unsupported language {manifest['language']!r} -- this converter only supports "
            f"{REQUIRED_LANGUAGE!r}-language, frontend-tagged templates (the node-dashboard profile)"
        )''',
    "    pass  # MUTATION M3: language check removed",
)
assert "pass  # MUTATION M3" in s, "replacement did not match -- mutation not applied"
open(p, "w").write(s)
PY
assert_mutant_killed "M3: unsupported-language rejection removed"

echo
echo "=== result ==="
echo "${killed} killed, ${survived} survived"

echo "=== final: module restored, suite green again ==="
if ! run_tests_quiet; then
  echo "FAIL: suite does not pass after final restore -- module was not cleanly reverted"
  diff "${BACKUP}" "${MODULE}" && echo "(no diff -- investigate test environment instead)"
  exit 1
fi
echo "restored OK, suite green"

rm -f /tmp/.ks0006_mutation_out
[ "${survived}" -eq 0 ]
