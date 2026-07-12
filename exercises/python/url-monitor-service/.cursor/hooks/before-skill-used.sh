#!/usr/bin/env bash
# Audit skill usage and enforce QRSPI phase prerequisites before a skill runs.
set -euo pipefail

input=$(cat)

skill_name=$(
  echo "$input" | jq -r '
    .skill_name // .name // .skill_id // empty
  '
)
skill_path=$(
  echo "$input" | jq -r '
    .skill_path // .file_path // .full_path // empty
  '
)
entrypoint=$(
  echo "$input" | jq -r '
    .entrypoint // .invocation_type // .source // empty
  '
)

log_dir=".cursor/hooks/logs"
mkdir -p "$log_dir"
timestamp=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
printf '%s skill=%s path=%s entrypoint=%s\n' \
  "$timestamp" "$skill_name" "$skill_path" "$entrypoint" \
  >> "$log_dir/skill-usage.log"

allow() {
  echo '{ "permission": "allow" }'
}

deny() {
  local user_message=$1
  local agent_message=$2
  jq -n \
    --arg user_message "$user_message" \
    --arg agent_message "$agent_message" \
    '{
      permission: "deny",
      user_message: $user_message,
      agent_message: $agent_message
    }'
}

if [[ -z "$skill_name" ]]; then
  allow
  exit 0
fi

find_qrspi_file() {
  local filename=$1
  find thoughts/qrspi -name "$filename" -type f 2>/dev/null | head -1
}

case "$skill_name" in
  implement)
    if [[ -z "$(find_qrspi_file plan.md)" ]]; then
      deny \
        "The /implement skill is blocked until plan.md exists under thoughts/qrspi/." \
        "Run /plan first and create plan.md before invoking /implement."
      exit 0
    fi
    ;;
  plan)
    if [[ -z "$(find_qrspi_file structure.md)" ]]; then
      deny \
        "The /plan skill is blocked until structure.md exists under thoughts/qrspi/." \
        "Run /structure first and create structure.md before invoking /plan."
      exit 0
    fi
    ;;
  structure)
    if [[ -z "$(find_qrspi_file design.md)" ]]; then
      deny \
        "The /structure skill is blocked until design.md exists under thoughts/qrspi/." \
        "Run /design first and create design.md before invoking /structure."
      exit 0
    fi
    ;;
esac

allow
exit 0
