#!/bin/bash
input=$(cat)
path=$(echo "$input" | jq -r '.tool_input.path // empty')

if [[ -n "$path" ]]; then
  user_message="The Delete tool is blocked. Please delete ${path} yourself in Finder or your terminal."
  agent_message="Delete is not allowed by project policy. Do not retry deletion. Tell the user to delete ${path} manually."
else
  user_message="The Delete tool is blocked. Please delete the file(s) yourself in Finder or your terminal."
  agent_message="Delete is not allowed by project policy. Do not retry deletion. Tell the user which path(s) to delete manually."
fi

jq -n \
  --arg user_message "$user_message" \
  --arg agent_message "$agent_message" \
  '{
    permission: "deny",
    user_message: $user_message,
    agent_message: $agent_message
  }'
