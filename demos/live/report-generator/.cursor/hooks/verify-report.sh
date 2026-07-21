#!/usr/bin/env bash
# stop hook + manual verifier: run report_generator.py and check required HTML sections.
set -euo pipefail

REQUIRED_SECTIONS=(
  report-header
  kpi-cards
  mrr-trend
  revenue-by-plan
  churn-analysis
  top-customers
  engagement-summary
)

log_dir=".cursor/hooks/logs"
mkdir -p "$log_dir"
log_file="$log_dir/report-verify.log"

log() {
  printf '%s %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*" >> "$log_file"
}

validate_report() {
  local output_file=${1:-report.html}
  local missing=()

  if [[ ! -f "$output_file" ]]; then
    echo "missing output file: $output_file"
    return 1
  fi

  if [[ ! -s "$output_file" ]]; then
    echo "output file is empty: $output_file"
    return 1
  fi

  for section_id in "${REQUIRED_SECTIONS[@]}"; do
    if ! grep -q "id=\"${section_id}\"" "$output_file"; then
      missing+=("$section_id")
    fi
  done

  if ((${#missing[@]} > 0)); then
    echo "missing sections: ${missing[*]}"
    return 1
  fi

  echo "ok"
  return 0
}

run_generator() {
  local output_file=${1:-report.html}

  if [[ ! -f report_generator.py ]]; then
    log "report_generator.py not found; skipping generation"
    return 2
  fi

  if python3 report_generator.py --output "$output_file" >> "$log_file" 2>&1; then
    log "report_generator.py succeeded -> $output_file"
    return 0
  fi

  log "report_generator.py failed; see $log_file"
  return 1
}

build_followup() {
  local message=$1
  jq -n --arg msg "$message" '{followup_message: $msg}'
}

manual_mode=false
output_file="report.html"

if [[ "${1:-}" == "--manual" ]]; then
  manual_mode=true
  output_file="${2:-report.html}"
fi

if [[ "$manual_mode" == "true" ]]; then
  log "manual verification started"
  gen_status=0
  run_generator "$output_file" || gen_status=$?

  if [[ "$gen_status" -eq 2 ]]; then
    echo "report_generator.py not found"
    exit 1
  elif [[ "$gen_status" -ne 0 ]]; then
    echo "report_generator.py failed; see $log_file"
    exit 1
  fi

  result=$(validate_report "$output_file" || true)
  if [[ "$result" == "ok" ]]; then
    echo "Report verification passed: $output_file"
    log "manual verification passed"
    exit 0
  fi

  echo "Report verification failed: $result"
  log "manual verification failed: $result"
  exit 1
fi

input=$(cat)
status=$(echo "$input" | jq -r '.status // empty')

if [[ "$status" != "completed" ]]; then
  echo '{}'
  exit 0
fi

log "stop hook verification started"

if [[ ! -f report_generator.py ]]; then
  log "report_generator.py not found; no follow-up"
  echo '{}'
  exit 0
fi

if ! run_generator "$output_file"; then
  build_followup "Report verification failed: report_generator.py exited with an error. Check .cursor/hooks/logs/report-verify.log and fix before finishing."
  exit 0
fi

result=$(validate_report "$output_file" || true)
if [[ "$result" == "ok" ]]; then
  log "stop hook verification passed"
  echo '{}'
  exit 0
fi

build_followup "Report verification failed: ${result}. Required section IDs: ${REQUIRED_SECTIONS[*]}. Fix report_generator.py and re-run /verify-report."
exit 0
