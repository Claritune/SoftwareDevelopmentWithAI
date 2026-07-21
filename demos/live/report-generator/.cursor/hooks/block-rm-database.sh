#!/usr/bin/env bash
# beforeShellExecution: block deletion of database.db
set -euo pipefail

input=$(cat)
command=$(echo "$input" | jq -r '.command // empty')

if [[ "$command" =~ database\.db ]]; then
  if [[ "$command" =~ (^|[[:space:];|&])rm([[:space:]]|$|-) ]] \
    || [[ "$command" =~ (^|[[:space:];|&])/(usr/)?bin/rm([[:space:]]|$|-) ]] \
    || [[ "$command" =~ unlink[[:space:]] ]] \
    || [[ "$command" =~ trash[[:space:]] ]]; then
    jq -n \
      --arg user_message "Deleting database.db is blocked. Sample data would be lost. Reseed with /seed-database instead." \
      --arg agent_message "database.db deletion is blocked by project policy. Do not retry. Tell the user to reseed via /seed-database if they want fresh data." \
      '{
        permission: "deny",
        user_message: $user_message,
        agent_message: $agent_message
      }'
    exit 0
  fi
fi

echo '{ "permission": "allow" }'
exit 0
