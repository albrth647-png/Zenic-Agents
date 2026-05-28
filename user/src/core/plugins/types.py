from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PluginState(str, Enum):
    UNLOADED = "unloaded"
    LOADED = "loaded"
    ACTIVE = "active"
    ERROR = "error"
    DISABLED = "disabled"


class PluginCapability(str, Enum):
    EXECUTOR = "executor"
    AGENT = "agent"
    MIDDLEWARE = "middleware"
    HOOK = "hook"
    PROVIDER = "provider"


@dataclass
class PluginManifest:
    id: str
    name: str
    version: str
    description: str = ""
    author: str = ""
    capabilities: set[PluginCapability] = field(default_factory=set)
    dependencies: list[str] = field(default_factory=list)
    min_core_version: str = "0.1.0"
    entry_point: str = ""
    config_schema: dict[str, Any] = field(default_factory=dict)


@dataclass
class PluginInstance:
    manifest: PluginManifest
    state: PluginState = PluginState.UNLOADED
    loaded_at: str | None = None
    error_message: str | None = None
    config: dict[str, Any] = field(default_factory=dict)
