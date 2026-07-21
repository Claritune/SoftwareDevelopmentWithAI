#!/usr/bin/env bash
# beforeMCPExecution: block destructive SQLite MCP writes unless reseed is allowed.
set -euo pipefail

input=$(cat)

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

is_sqlite_mcp() {
  echo "$input" | jq -e '
    (
      (.command // "") | test("mcp-server-sqlite|mcp/sqlite"; "i")
    ) or (
      (.url // "") | test("sqlite"; "i")
    ) or (
      (.tool_name // "") | test("^(read_query|write_query|query|create_table|list_tables|describe_table)$")
    )
  ' >/dev/null 2>&1
}

extract_sql() {
  echo "$input" | jq -r '
    def params:
      if (.tool_input | type) == "string" then
        (.tool_input | try fromjson catch {})
      elif (.tool_input | type) == "object" then
        .tool_input
      else
        {}
      end;

    params | .query // .sql // empty
  '
}

if ! is_sqlite_mcp; then
  allow
  exit 0
fi

reseed_allowed=false
if [[ -f .cursor/allow-destructive-sql ]]; then
  reseed_allowed=true
fi
if echo "$input" | jq -e 'tostring | test("reseed|reset"; "i")' >/dev/null 2>&1; then
  reseed_allowed=true
fi

tool_name=$(echo "$input" | jq -r '.tool_name // empty')
read_only_tools='^(read_query|list_tables|describe_table|db_info|get_table_schema)$'
if [[ "$tool_name" =~ $read_only_tools ]]; then
  allow
  exit 0
fi

sql=$(extract_sql)

if [[ -z "$sql" ]]; then
  allow
  exit 0
fi

normalized=$(echo "$sql" | tr '[:lower:]' '[:upper:]' | tr -s '[:space:]' ' ')

if [[ "$reseed_allowed" == "true" ]]; then
  allow
  exit 0
fi

if [[ "$normalized" =~ (^|[^A-Z])(DROP|DELETE|UPDATE|ALTER|TRUNCATE)([^A-Z]|$) ]]; then
  deny \
    "Destructive SQL (DROP/DELETE/UPDATE/ALTER) is blocked on the SQLite MCP server. To reset data, say \"reseed\" or create .cursor/allow-destructive-sql temporarily." \
    "Destructive SQL is blocked by project hook. Use INSERT/CREATE/SELECT for seeding, or ask the user to confirm a reseed before retrying DROP/DELETE/UPDATE."
  exit 0
fi

allow
exit 0
