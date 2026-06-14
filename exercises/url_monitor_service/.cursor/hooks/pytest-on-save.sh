#!/usr/bin/env bash
# Run pytest after the agent edits Python source or test files.
set -euo pipefail

input=$(cat)
file_path=$(echo "$input" | jq -r '.file_path // empty')

if [[ -z "$file_path" ]] || [[ ! "$file_path" =~ \.py$ ]]; then
  exit 0
fi

case "$file_path" in
  src/*|tests/*|app/*) ;;
  *) exit 0 ;;
esac

if [[ ! -f pyproject.toml ]] || [[ ! -d tests ]]; then
  exit 0
fi

if ! command -v uv >/dev/null 2>&1; then
  exit 0
fi

uv run pytest tests/ -q
