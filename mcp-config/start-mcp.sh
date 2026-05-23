#!/bin/bash
# ============================================================
#  MCP Server Launcher - Zenic-Agents
#  Inicia todos los servidores MCP configurados
# ============================================================

set -e

MCP_BASE="/home/z/my-project/mcp-servers"
CONFIG_DIR="/home/z/my-project/mcp-config"
LOG_DIR="/home/z/my-project/mcp-logs"

mkdir -p "$LOG_DIR"

echo "============================================================"
echo "  Iniciando Servidores MCP - Zenic-Agents"
echo "============================================================"
echo ""

# Function to start an MCP server in background
start_server() {
  local name=$1
  local command=$2
  shift 2
  local args=("$@")

  echo -n "  [$name] Iniciando... "
  if $command "${args[@]}" > "$LOG_DIR/${name}.log" 2>&1 &
  then
    local pid=$!
    echo "OK (PID: $pid)"
    echo "$pid" > "$LOG_DIR/${name}.pid"
  else
    echo "FALLO"
  fi
}

echo "Servidores oficiales:"
echo "-------------------------------------------"

start_server "filesystem" npx -y @modelcontextprotocol/server-filesystem /home/z/my-project &
start_server "memory" npx -y @modelcontextprotocol/server-memory &
start_server "sequential-thinking" npx -y @modelcontextprotocol/server-sequential-thinking &
start_server "everything" npx -y @modelcontextprotocol/server-everything &

wait
echo ""

echo "Servidores de base de datos:"
echo "-------------------------------------------"

start_server "sqlite" npx -y mcp-server-sqlite-npx &
start_server "postgres" npx -y @modelcontextprotocol/server-postgres &

wait
echo ""

echo "Servidores de desarrollo:"
echo "-------------------------------------------"

start_server "github" npx -y @modelcontextprotocol/server-github &
start_server "eslint" npx -y @eslint/mcp &
start_server "fetch" npx -y @mokei/mcp-fetch &
start_server "context7" npx -y @upstash/context7-mcp &

wait
echo ""

echo "Servidores de testing y debugging:"
echo "-------------------------------------------"

start_server "playwright" npx -y @playwright/mcp &
start_server "chrome-devtools" npx -y chrome-devtools-mcp &
start_server "sentry" npx -y @sentry/mcp-server &

wait
echo ""

echo "Servidores avanzados:"
echo "-------------------------------------------"

start_server "tree-sitter" npx -y @nendo/tree-sitter-mcp &
start_server "dependency-graph" npx -y @syke1/mcp-server &

wait
echo ""

echo "Servidor personalizado:"
echo "-------------------------------------------"

start_server "semantic-analyzer" node /home/z/my-project/mcp-servers/custom-semantic/index.mjs &

wait
echo ""

echo "============================================================"
echo "  Todos los servidores MCP han sido iniciados"
echo "  Logs: $LOG_DIR/"
echo "  Para detener: $0 --stop"
echo "============================================================"
