#!/usr/bin/env bash
# Stop hook: verify Python functions have no default argument values (semgrep).
set -euo pipefail

input=$(cat)
status=$(echo "$input" | jq -r '.status // empty')

if [[ "$status" != "completed" ]]; then
  echo '{}'
  exit 0
fi

rule_config=".cursor/semgrep/no-default-args.yaml"
if [[ ! -f "$rule_config" ]]; then
  echo "no-default-args hook: rule config not found at $rule_config" >&2
  echo '{}'
  exit 0
fi

run_semgrep() {
  if command -v uv >/dev/null 2>&1 && [[ -f pyproject.toml ]]; then
    uv run semgrep "$@" 2>/dev/null && return 0
  fi
  if command -v semgrep >/dev/null 2>&1; then
    semgrep "$@"
    return $?
  fi
  return 127
}

if ! run_semgrep --version >/dev/null 2>&1; then
  echo "no-default-args hook: semgrep not installed; install with 'pip install semgrep' or add to dev deps" >&2
  echo '{}'
  exit 0
fi

scan_output=$(run_semgrep --config "$rule_config" app/ tests/ --json --quiet || true)

findings=$(echo "$scan_output" | jq -r '.results // [] | length')
if [[ "$findings" -eq 0 ]]; then
  echo '{}'
  exit 0
fi

summary=$(echo "$scan_output" | jq -r '
  .results[]
  | "- \(.path):\(.start.line) in \(.extra.metavars.func.value // "function") — \(.extra.message)"
' | head -20)

remaining=""
if [[ "$findings" -gt 20 ]]; then
  remaining=$'\n(and '"$((findings - 20))"$' more)'
fi

followup="Semgrep found ${findings} function parameter(s) with default values. This project disallows default argument values — remove them or refactor (e.g. make parameters required, use overloads, or inject dependencies without defaults).

Findings:
${summary}${remaining}"

jq -n --arg msg "$followup" '{followup_message: $msg}'
