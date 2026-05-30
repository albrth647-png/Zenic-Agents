"""
Email Channel Provider — Constants and configuration mappings.
"""

# Valid send modes
VALID_MODES = frozenset({"smtp", "graph_api", "auto"})

# Priority → importance mapping (ChannelPriority → email importance)
PRIORITY_TO_IMPORTANCE: dict[str, str] = {
    "low": "low",
    "normal": "normal",
    "high": "high",
    "urgent": "high",
    "emergency": "high",
}
