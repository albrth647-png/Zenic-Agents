"""
Zenic-Agents — Hardware Fingerprint Flow (Phase 10)

Flow for end users to view their device's hardware fingerprint
and hardware binding status. Useful for troubleshooting
license activation issues and providing support info.

Design Patterns:
  - Template Method: extends BaseFlow lifecycle
  - Value Object: HardwareResult as immutable result
  - Facade: delegates to hw_binding module
"""

from __future__ import annotations

import hashlib
import logging
import os
import platform
from dataclasses import dataclass, field
from typing import Any

from .base import BaseFlow, FlowContext

logger = logging.getLogger(__name__)


# ── Hardware Result ──────────────────────────────────────────


@dataclass
class HardwareResult:
    """Hardware fingerprint and system information.

    Attributes:
        fingerprint: The BLAKE3/SHA-256 hardware fingerprint hash.
        machine_id: The /etc/machine-id value (if available).
        cpu_model: CPU model name.
        total_memory_mb: Total system RAM in MB.
        disk_serial: Primary disk serial number.
        os_info: Operating system information.
        arch: System architecture.
        is_android: Whether running on Android/Termux.
        is_termux: Whether running inside Termux.
        components_used: List of components used in fingerprint.
        match_score: Soft-match score against stored license (0-100).
    """

    fingerprint: str = ""
    machine_id: str = ""
    cpu_model: str = ""
    total_memory_mb: int = 0
    disk_serial: str = ""
    os_info: str = ""
    arch: str = ""
    is_android: bool = False
    is_termux: bool = False
    components_used: list[str] = field(default_factory=list)
    match_score: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "fingerprint": self.fingerprint,
            "machine_id": self.machine_id[:8] + "..." if self.machine_id else "",
            "cpu_model": self.cpu_model,
            "total_memory_mb": self.total_memory_mb,
            "disk_serial": self.disk_serial[:8] + "..." if self.disk_serial else "",
            "os_info": self.os_info,
            "arch": self.arch,
            "is_android": self.is_android,
            "is_termux": self.is_termux,
            "components_used": self.components_used,
            "match_score": self.match_score,
        }


# ── Hardware Flow ────────────────────────────────────────────


class HardwareFlow(BaseFlow):
    """Hardware fingerprint display flow for end users.

    Collects system information, computes the hardware fingerprint,
    and checks it against any existing license binding.

    Steps:
      1. Collect system information (CPU, RAM, disk, OS)
      2. Compute hardware fingerprint
      3. Check match against stored license
      4. Render formatted report
    """

    name = "hardware"
    description = "Display your hardware fingerprint and system info"
    version = "1.0.0"

    def on_validate(self, ctx: FlowContext) -> None:
        """No user input required for hardware check."""
        pass

    def on_execute(self, ctx: FlowContext) -> None:
        """Collect hardware information and compute fingerprint."""
        result = HardwareResult(
            os_info=platform.system(),
            arch=platform.machine(),
            is_android="ANDROID_ARGUMENT" in os.environ,
            is_termux="TERMUX_VERSION" in os.environ,
        )

        # Machine ID
        components_used: list[str] = []
        for path in ["/etc/machine-id", "/var/lib/dbus/machine-id"]:
            try:
                with open(path) as f:
                    result.machine_id = f.read().strip()
                    components_used.append("machine-id")
                    break
            except (FileNotFoundError, PermissionError):
                continue

        # CPU
        try:
            with open("/proc/cpuinfo") as f:
                for line in f:
                    if line.startswith("model name"):
                        result.cpu_model = line.split(":")[1].strip()
                        components_used.append("cpu")
                        break
        except (FileNotFoundError, PermissionError):
            result.cpu_model = platform.processor() or "Unknown"

        # Memory
        try:
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        kb = int(line.split(":")[1].strip().split()[0])
                        result.total_memory_mb = kb // 1024
                        components_used.append("memory")
                        break
        except (FileNotFoundError, PermissionError, ValueError):
            pass

        # Disk serial
        try:
            import subprocess

            proc = subprocess.run(
                ["lsblk", "-ndo", "SERIAL"],  # noqa: S607
                capture_output=True,
                text=True,
                timeout=3,
            )
            if proc.returncode == 0:
                serials = [s.strip() for s in proc.stdout.split("\n") if s.strip()]
                if serials:
                    result.disk_serial = serials[0]
                    components_used.append("disk_serial")
        except (FileNotFoundError, Exception):
            pass

        # Compute fingerprint via license module
        try:
            from src.core.license.license_parts.hw_binding import (
                check_hardware_match,
                get_hardware_fingerprint,
            )
            from src.core.license.types import HardwareBindingStrength

            result.fingerprint = get_hardware_fingerprint()

            # Check match against stored license
            try:
                from src.core.license import get_license_manager

                manager = get_license_manager()
                license_info = manager.get_current_license()
                if license_info and license_info.hardware_id:
                    current = get_hardware_fingerprint()
                    if check_hardware_match(license_info.hardware_id, current, HardwareBindingStrength.SOFT):
                        result.match_score = 100
                    elif check_hardware_match(license_info.hardware_id, current, HardwareBindingStrength.STRICT):
                        result.match_score = 80
                    else:
                        result.match_score = 30
            except Exception:
                pass

        except ImportError:
            # Fallback: compute fingerprint manually
            components: list[str] = []
            if result.machine_id:
                components.append(result.machine_id[:32])
            if result.cpu_model:
                components.append(result.cpu_model[:32])
            if result.total_memory_mb:
                components.append(str(result.total_memory_mb))
            combined = "|".join(components) if components else "default-hw"
            result.fingerprint = hashlib.sha256(combined.encode()).hexdigest()[:32]

        result.components_used = components_used
        ctx.set_artifact("hardware", result.to_dict())
        ctx.set_artifact("fingerprint", result.fingerprint)

    def on_render(self, ctx: FlowContext) -> str:
        """Render a formatted hardware information report."""
        hw = ctx.get_artifact("hardware", {})

        lines = [
            "[bold]Hardware Fingerprint Report[/]",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "",
            f"  Fingerprint:  [bold cyan]{hw.get('fingerprint', 'N/A')}[/]",
            "",
            "[bold]System Information[/]",
            f"  OS:           {hw.get('os_info', 'Unknown')} {hw.get('arch', '')}",
            f"  CPU:          {hw.get('cpu_model', 'Unknown')}",
            f"  Memory:       {hw.get('total_memory_mb', 0)} MB",
            f"  Disk Serial:  {hw.get('disk_serial', 'N/A')[:8]}{'...' if hw.get('disk_serial') else ''}",
        ]

        # Android/Termux detection
        if hw.get("is_android") or hw.get("is_termux"):
            lines.append("")
            lines.append("[bold green]Android/Termux Environment Detected[/]")
            if hw.get("is_termux"):
                lines.append("  Termux:       [green]Yes[/]")
            if hw.get("is_android"):
                lines.append("  Android:      [green]Yes[/]")

        # Components used
        components = hw.get("components_used", [])
        if components:
            lines.append("")
            lines.append("[dim]Fingerprint components:[/]")
            for comp in components:
                lines.append(f"  [green]+[/] {comp}")

        # Match score
        match_score = hw.get("match_score", 0)
        if match_score > 0:
            lines.append("")
            if match_score >= 80:
                lines.append(f"  License Match: [bold green]{match_score}%[/] (hardware matches)")
            elif match_score >= 50:
                lines.append(f"  License Match: [bold yellow]{match_score}%[/] (partial match)")
            else:
                lines.append(f"  License Match: [bold red]{match_score}%[/] (hardware changed!)")

        lines.append("")
        lines.append("[dim]This fingerprint is unique to your device and used for license binding.[/]")
        lines.append("[dim]If you change hardware, your license may need reactivation.[/]")

        return "\n".join(lines)
