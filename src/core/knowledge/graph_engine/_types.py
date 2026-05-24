"""Types and constants for graph_engine."""

from __future__ import annotations
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

DB_DIR = Path.home() / ".zenic_agents" / "db"

DB_PATH = DB_DIR / "knowledge_graph.sqlite"
__all__ = ["DB_DIR", "DB_PATH", "logger"]
