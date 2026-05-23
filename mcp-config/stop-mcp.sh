#!/bin/bash
# ============================================================
#  MCP Server Stop Script - Zenic-Agents
# ============================================================

LOG_DIR="/home/z/my-project/mcp-logs"

echo "Deteniendo servidores MCP..."

if [ -d "$LOG_DIR" ]; then
  for pidfile in "$LOG_DIR"/*.pid; do
    if [ -f "$pidfile" ]; then
      pid=$(cat "$pidfile")
      name=$(basename "$pidfile" .pid)
      if kill -0 "$pid" 2>/dev/null; then
        kill "$pid"
        echo "  [$name] Detenido (PID: $pid)"
      else
        echo "  [$name] Ya no estaba corriendo (PID: $pid)"
      fi
      rm -f "$pidfile"
    fi
  done
fi

echo "Todos los servidores MCP han sido detenidos."
