#!/usr/bin/env bash
# Append every tool-call harness event to logs/tool-calls.log (JSONL).
set -euo pipefail

input=$(cat)
log_dir="logs"
log_file="$log_dir/tool-calls.log"

mkdir -p "$log_dir"
timestamp=$(date -u '+%Y-%m-%dT%H:%M:%SZ')

echo "$input" | jq -c --arg logged_at "$timestamp" '. + {logged_at: $logged_at}' >> "$log_file"

exit 0
