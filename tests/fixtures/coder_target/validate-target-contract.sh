#!/usr/bin/env bash
# validate-target-contract.sh — structural validator for
# docs/contracts/coder-terraform-target-contract-v1.md.
#
# Checks a target directory's main.tf against the contract's "Required shape"
# section. STRUCTURAL, not semantic: text-pattern presence/shape checks, never
# a Terraform parse or a `terraform validate`/`plan` call. Terraform is not
# installed on the hosts this runs from, by the authoring task's own
# instruction, and this script never invokes it or expects it present.
#
# A known, stated limitation (matches the contract's own "Unsupported
# surface"): block extraction below counts braces character-by-character and
# does not special-case heredoc bodies (`startup_script = <<-EOT ... EOT`).
# An unbalanced literal brace inside a heredoc could misattribute where a
# block ends. None of the four templates this contract is bounded by, nor the
# committed example, exercises that case; a real Terraform parser would be
# needed to remove the limitation entirely, which is exactly the dependency
# this validator is built to avoid.
#
# Usage:
#   ./validate-target-contract.sh <target-dir>
#
# Exit code 0 = all checks passed; non-zero = at least one failed, or usage error.
set -uo pipefail

TARGET_DIR="${1:?usage: validate-target-contract.sh <target-dir>}"
MAIN_TF="${TARGET_DIR}/main.tf"

pass=0
fail=0
check() { # <description> <command...>
  local desc="$1"; shift
  if "$@" >/dev/null 2>&1; then
    echo "PASS  ${desc}"; pass=$((pass+1))
  else
    echo "FAIL  ${desc}"; fail=$((fail+1))
  fi
}

if [ ! -f "${MAIN_TF}" ]; then
  echo "ERROR: ${MAIN_TF} not found. This script neither creates nor infers a target." >&2
  exit 2
fi

# Extracts ONE top-level block starting at the first line matching $2 (an
# extended regex), through the line where brace depth returns to zero,
# inclusive. Depth starts at 0 and is tracked character-by-character, so a
# single-line empty block (`data "x" "y" {}`) is captured correctly, as is a
# multi-line block. Prints nothing if the start pattern is never found.
extract_block() {
  local file="$1" start_pat="$2"
  awk -v start="${start_pat}" '
    BEGIN { capturing = 0; depth = 0 }
    !capturing && $0 ~ start { capturing = 1 }
    capturing {
      print
      line = $0
      for (i = 1; i <= length(line); i++) {
        c = substr(line, i, 1)
        if (c == "{") depth++
        else if (c == "}") depth--
      }
      if (capturing && depth == 0) { exit }
    }
  ' "${file}"
}

# All of the following take block/file CONTENT as a real argv value ($1),
# never interpolated into a constructed shell command string -- content that
# legitimately contains `$`, `{`, `}` (every Terraform interpolation does)
# must never be re-parsed by a second shell. This bit an earlier draft: a
# `bash -c "... \"${BLOCK}\" ..."` construction let the block's own
# `${data.coder_workspace.me...}` text be re-evaluated as a bad variable
# substitution by the inner shell, which failed silently under `check`'s
# `2>/dev/null` and reported every content-bearing check as FAIL regardless
# of the real content. Passing content as `"$1"` to a plain function avoids a
# second parse entirely.
nonempty()       { [ -n "$1" ]; }
block_matches()  { printf '%s\n' "$1" | grep -Eq "$2"; }   # <content> <regex>
count_pos()      { [ "$(( $1 + $2 ))" -eq 1 ]; }            # exactly-one-of-two

# --- 1. Providers ------------------------------------------------------------
REQUIRED_PROVIDERS_BLOCK="$(extract_block "${MAIN_TF}" 'required_providers[[:space:]]*{' | tr '\n' ' ' | tr -s ' ')"
check 'required_providers declares coder = { source = "coder/coder" }' \
  block_matches "${REQUIRED_PROVIDERS_BLOCK}" 'coder[[:space:]]*=[[:space:]]*{[[:space:]]*source[[:space:]]*=[[:space:]]*"coder/coder"'
check 'required_providers declares docker = { source = "kreuzwerker/docker" }' \
  block_matches "${REQUIRED_PROVIDERS_BLOCK}" 'docker[[:space:]]*=[[:space:]]*{[[:space:]]*source[[:space:]]*=[[:space:]]*"kreuzwerker/docker"'
check 'top-level provider "docker" {} block present' \
  grep -Eq '^provider[[:space:]]+"docker"' "${MAIN_TF}"

# --- 2. Data sources -----------------------------------------------------------
check 'data "coder_workspace" "me" present' \
  grep -Eq '^data[[:space:]]+"coder_workspace"[[:space:]]+"me"' "${MAIN_TF}"
check 'data "coder_workspace_owner" "me" present' \
  grep -Eq '^data[[:space:]]+"coder_workspace_owner"[[:space:]]+"me"' "${MAIN_TF}"

# --- 3. Resources --------------------------------------------------------------
AGENT_BLOCK="$(extract_block "${MAIN_TF}" '^resource[[:space:]]+"coder_agent"[[:space:]]+"main"[[:space:]]*{')"
check 'resource "coder_agent" "main" present' \
  nonempty "${AGENT_BLOCK}"
check 'coder_agent.main declares os' \
  block_matches "${AGENT_BLOCK}" '^[[:space:]]*os[[:space:]]*='
check 'coder_agent.main declares arch' \
  block_matches "${AGENT_BLOCK}" '^[[:space:]]*arch[[:space:]]*='

VOLUME_BLOCK="$(extract_block "${MAIN_TF}" '^resource[[:space:]]+"docker_volume"[[:space:]]+"home_volume"[[:space:]]*{')"
check 'resource "docker_volume" "home_volume" present' \
  nonempty "${VOLUME_BLOCK}"
check 'docker_volume.home_volume declares name' \
  block_matches "${VOLUME_BLOCK}" '^[[:space:]]*name[[:space:]]*='

CONTAINER_BLOCK="$(extract_block "${MAIN_TF}" '^resource[[:space:]]+"docker_container"[[:space:]]+"workspace"[[:space:]]*{')"
check 'resource "docker_container" "workspace" present' \
  nonempty "${CONTAINER_BLOCK}"
check 'docker_container.workspace references coder_agent.main (.token, .init_script or .id)' \
  block_matches "${CONTAINER_BLOCK}" 'coder_agent\.main\.(token|init_script|id)'

# --- 4. Variable convention (conditional) --------------------------------------
VAR_NAMES="$(grep -Eo '^variable[[:space:]]+"[^"]+"' "${MAIN_TF}" | sed -E 's/^variable[[:space:]]+"([^"]+)"/\1/')"
if [ -z "${VAR_NAMES}" ]; then
  echo "NOTE  no variable blocks declared -- convention check not applicable (contract section 4 permits zero variables)"
else
  while IFS= read -r vname; do
    [ -n "${vname}" ] || continue
    VBLOCK="$(extract_block "${MAIN_TF}" "^variable[[:space:]]+\"${vname}\"[[:space:]]*{")"
    check "variable \"${vname}\" declares default" \
      block_matches "${VBLOCK}" '^[[:space:]]*default[[:space:]]*='
    check "variable \"${vname}\" declares description" \
      block_matches "${VBLOCK}" '^[[:space:]]*description[[:space:]]*='
    check "variable \"${vname}\" declares type" \
      block_matches "${VBLOCK}" '^[[:space:]]*type[[:space:]]*='
  done <<< "${VAR_NAMES}"
fi

# --- 5. Provenance (exactly one required) --------------------------------------
HAS_SOURCE_METADATA=0; [ -f "${TARGET_DIR}/SOURCE_METADATA.md" ] && HAS_SOURCE_METADATA=1
HAS_FORGE_SOURCE=0; [ -f "${TARGET_DIR}/FORGE_SOURCE.md" ] && HAS_FORGE_SOURCE=1
check 'exactly one provenance record present (SOURCE_METADATA.md xor FORGE_SOURCE.md)' \
  count_pos "${HAS_SOURCE_METADATA}" "${HAS_FORGE_SOURCE}"

# --- 6. No inline secrets --------------------------------------------------------
# Reuses ops/coder/images/starkgrid-coder-base/validate.sh's exact host-side
# source-scan pattern, for consistency rather than a second detector.
secret_scan_clean() { ! grep -Eq 'BEGIN [A-Z ]*PRIVATE KEY|gh[pousr]_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|password[[:space:]]*=' "$1"; }
check 'no inline secret material in main.tf' \
  secret_scan_clean "${MAIN_TF}"

echo "== ${pass} passed, ${fail} failed (${TARGET_DIR}) =="
[ "${fail}" -eq 0 ]
