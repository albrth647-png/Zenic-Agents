#!/bin/bash
# ============================================================
#  MCP Server Status Check - Zenic-Agents
# ============================================================

LOG_DIR="/home/z/my-project/mcp-logs"

echo "============================================================"
echo "  Estado de Servidores MCP - Zenic-Agents"
echo "============================================================"
echo ""

if [ ! -d "$LOG_DIR" ]; then
  echo "  No se han iniciado servidores MCP aún."
  echo "  Ejecuta: bash /home/z/my-project/mcp-config/start-mcp.sh"
  exit 0
fi

running=0
stopped=0

for pidfile in "$LOG_DIR"/*.pid; do
  if [ -f "$pidfile" ]; then
    pid=$(cat "$pidfile")
    name=$(basename "$pidfile" .pid)
    if kill -0 "$pid" 2>/dev/null; then
      echo "  [RUNNING] $name (PID: $pid)"
      running=$((running + 1))
    else
      echo "  [STOPPED] $name (PID: $pid - no activo)"
      stopped=$((stopped + 1))
    fi
  fi
done

echo ""
echo "  Total: $running corriendo, $stopped detenidos"
echo "============================================================"
