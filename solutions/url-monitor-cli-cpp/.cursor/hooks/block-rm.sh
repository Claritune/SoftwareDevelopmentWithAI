#!/bin/bash
input=$(cat)
command=$(echo "$input" | jq -r '.command // empty')

# Match rm as a standalone command, including common absolute paths.
if [[ "$command" =~ (^|[[:space:];|&])rm([[:space:]]|$|-) ]] \
  || [[ "$command" =~ (^|[[:space:];|&])/(usr/)?bin/rm([[:space:]]|$|-) ]]; then
  echo '{
    "permission": "deny",
    "user_message": "The rm command is blocked. Please delete the file(s) yourself in Finder or your terminal.",
    "agent_message": "rm is not allowed by project policy. Do not retry deletion. Tell the user which path(s) to delete manually."
  }'
  exit 0
fi

echo '{ "permission": "allow" }'
exit 0
