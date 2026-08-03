#!/usr/bin/env bash
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

QDRANT_CONTAINER="qdrant"
QDRANT_VOLUME="qdrant_data"
QDRANT_PORT=6333
OLLAMA_LLM_MODEL="llama3.1:8b"
OLLAMA_EMBED_MODEL="bge-m3"
MEM0_MCP_PKG="git+https://github.com/elvismdev/mem0-mcp-selfhosted.git@v0.3.2"

info()  { printf "${BLUE}[INFO]${NC}  %s\n" "$*"; }
ok()    { printf "${GREEN}[OK]${NC}    %s\n" "$*"; }
warn()  { printf "${YELLOW}[WARN]${NC}  %s\n" "$*"; }
fail()  { printf "${RED}[FAIL]${NC}  %s\n" "$*"; exit 1; }

cleanup() {
    info "Stopping Qdrant container..."
    docker stop "$QDRANT_CONTAINER" 2>/dev/null && ok "Container stopped" || warn "Container was not running"
    docker rm "$QDRANT_CONTAINER" 2>/dev/null && ok "Container removed" || warn "Container did not exist"

    info "Removing Qdrant volume..."
    docker volume rm "$QDRANT_VOLUME" 2>/dev/null && ok "Volume removed" || warn "Volume did not exist"

    ok "Cleanup complete"
    exit 0
}

if [[ "${1:-}" == "--cleanup" ]]; then
    cleanup
fi

# ─── Prerequisites ────────────────────────────────────────────────────

info "Checking prerequisites..."

command -v docker >/dev/null 2>&1 || fail "Docker is not installed. Install it from https://docker.com"
command -v ollama >/dev/null 2>&1 || fail "Ollama is not installed. Install it from https://ollama.com"
command -v uvx    >/dev/null 2>&1 || fail "uvx is not installed. Install it with: pip install uv"

# Check Docker daemon is running
if ! docker info >/dev/null 2>&1; then
    fail "Docker daemon is not running. Start Docker Desktop or run 'dockerd'"
fi
ok "Docker is running"

# Check Ollama is running — start it if not
if ! curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; then
    warn "Ollama is not running. Starting it in the background..."
    ollama serve >/dev/null 2>&1 &
    OLLAMA_PID=$!
    for i in {1..15}; do
        if curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; then
            break
        fi
        sleep 1
    done
    if ! curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; then
        fail "Could not start Ollama after 15 seconds"
    fi
    ok "Ollama started (PID $OLLAMA_PID)"
else
    ok "Ollama is running"
fi

# ─── Step 1: Qdrant ──────────────────────────────────────────────────

info "Step 1: Starting Qdrant..."

if docker ps --format '{{.Names}}' | grep -q "^${QDRANT_CONTAINER}$"; then
    ok "Qdrant container already running"
elif docker ps -a --format '{{.Names}}' | grep -q "^${QDRANT_CONTAINER}$"; then
    info "Qdrant container exists but is stopped — starting it..."
    docker start "$QDRANT_CONTAINER"
    ok "Qdrant container started"
else
    docker run -d --name "$QDRANT_CONTAINER" \
        -p ${QDRANT_PORT}:6333 -p 6334:6334 \
        -v ${QDRANT_VOLUME}:/qdrant/storage \
        qdrant/qdrant >/dev/null
    ok "Qdrant container created and started"
fi

# Wait for Qdrant to be healthy
info "Waiting for Qdrant to be ready..."
for i in {1..30}; do
    if curl -sf "http://localhost:${QDRANT_PORT}/healthz" >/dev/null 2>&1; then
        break
    fi
    sleep 1
done

if curl -sf "http://localhost:${QDRANT_PORT}/healthz" >/dev/null 2>&1; then
    ok "Qdrant is healthy at http://localhost:${QDRANT_PORT}"
else
    fail "Qdrant did not become healthy after 30 seconds"
fi

# ─── Step 2: Ollama Models ───────────────────────────────────────────

info "Step 2: Pulling Ollama models..."

pull_model() {
    local model="$1"
    if ollama list 2>/dev/null | grep -q "^${model}"; then
        ok "Model ${model} already available"
    else
        info "Pulling ${model} (this may take a while on first run)..."
        ollama pull "$model"
        ok "Model ${model} pulled"
    fi
}

pull_model "$OLLAMA_LLM_MODEL"
pull_model "$OLLAMA_EMBED_MODEL"

# ─── Step 3: Warm uvx cache ─────────────────────────────────────────

info "Step 3: Warming uvx cache for mem0-mcp-selfhosted..."

MCP_PIN="mcp[cli]>=1.23.0,<2"

info "Pre-warming uvx cache (pinning mcp<2 to avoid FastMCP breakage)..."
timeout 15 uvx --from "$MEM0_MCP_PKG" --with "$MCP_PIN" mem0-mcp-selfhosted 2>&1 || true
ok "uvx cache warmed"

# ─── Step 4: Verify mcp.json ────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MCP_JSON="${SCRIPT_DIR}/.cursor/mcp.json"

info "Step 4: Checking .cursor/mcp.json..."

if [[ -f "$MCP_JSON" ]]; then
    ok "MCP config exists at ${MCP_JSON}"
    if grep -q "mem0" "$MCP_JSON"; then
        ok "mem0 server is configured"
    else
        warn "mcp.json exists but does not contain mem0 config"
    fi
else
    warn "No .cursor/mcp.json found — see DEMO.md for the configuration"
fi

# ─── Done ────────────────────────────────────────────────────────────

echo ""
printf "${GREEN}════════════════════════════════════════════════════════${NC}\n"
printf "${GREEN}  Setup complete! Next steps:${NC}\n"
printf "${GREEN}════════════════════════════════════════════════════════${NC}\n"
echo ""
echo "  1. Restart Cursor (close and reopen completely)"
echo "  2. Go to Settings → Tools & MCP → enable mem0"
echo "  3. Open a chat (Cmd+L) and follow the demo script in DEMO.md"
echo ""
echo "  Useful commands during the demo:"
echo "    ollama ps              — show loaded models"
echo "    docker stats qdrant    — show container resource usage"
echo ""
echo "  To tear down:  ./setup.sh --cleanup"
echo ""
